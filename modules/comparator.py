# comparator.py
# Fase 3: Matching en vergelijkingslogica

"""
comparator.py
=============

Verantwoordelijkheid:
    Deterministisch matchen en vergelijken van systeemexport met leveranciersfactuur.

Hoofdfunctie:
    - vergelijk_facturen: Voert volledige vergelijking uit en retourneert resultaat-DataFrame

Workflow:
    1. Match regels (artikelcode → naam fallback)
    2. Vergelijk gematchte regels veld-voor-veld
    3. Bepaal status per regel
    4. Genereer mensleesbare toelichtingen
    5. Bouw resultaat-DataFrame

Output:
    DataFrame met vergelijkingsresultaten, klaar voor rapportage.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Optional
import sys
from pathlib import Path

# Voeg parent directory toe zodat config.py gevonden kan worden
sys.path.append(str(Path(__file__).parent.parent))
import config


def vergelijk_facturen(df_systeem: pd.DataFrame, df_factuur: pd.DataFrame) -> pd.DataFrame:
    """
    Hoofdfunctie: vergelijkt systeemexport met leveranciersfactuur.
    
    Parameters
    ----------
    df_systeem : pd.DataFrame
        Genormaliseerde systeemexport (canoniek model).
    df_factuur : pd.DataFrame
        Genormaliseerde leveranciersfactuur (canoniek model).
    
    Returns
    -------
    pd.DataFrame
        Resultaat met kolommen:
        - status
        - artikelcode
        - artikelnaam
        - aantal_systeem / aantal_factuur
        - prijs_systeem / prijs_factuur
        - totaal_systeem / totaal_factuur
        - btw_systeem / btw_factuur
        - afwijking_toelichting
    
    Voorbeelden
    -----------
    >>> df_sys = normaliseer_dataframe(lees_csv("export.csv"))
    >>> df_fac = normaliseer_dataframe(lees_csv("factuur.csv"))
    >>> resultaat = vergelijk_facturen(df_sys, df_fac)
    >>> resultaat['status'].value_counts()
    OK                       198
    AFWIJKING                 35
    ONTBREEKT OP FACTUUR      10
    dtype: int64
    """
    
    # Stap 1: Match regels
    matches = match_regels(df_systeem, df_factuur)
    
    # Stap 2: Bouw resultaten lijst
    resultaten = []
    
    # Verwerk gematchte regels
    for systeem_idx, factuur_idx in matches['gematchte_regels']:
        systeem_row = df_systeem.iloc[systeem_idx]
        factuur_row = df_factuur.iloc[factuur_idx]
        
        resultaat = vergelijk_regel(systeem_row, factuur_row)
        resultaten.append(resultaat)
    
    # Verwerk niet-gematchte systeemregels
    for systeem_idx in matches['systeem_zonder_match']:
        systeem_row = df_systeem.iloc[systeem_idx]
        
        resultaat = {
            'status': config.STATUS_ONTBREEKT_FACTUUR,
            'artikelcode': systeem_row[config.CANON_ARTIKELCODE],
            'artikelnaam': systeem_row[config.CANON_ARTIKELNAAM],
            'aantal_systeem': systeem_row[config.CANON_AANTAL],
            'aantal_factuur': None,
            'prijs_systeem': systeem_row[config.CANON_PRIJS],
            'prijs_factuur': None,
            'totaal_systeem': systeem_row[config.CANON_TOTAAL],
            'totaal_factuur': None,
            'btw_systeem': systeem_row[config.CANON_BTW],
            'btw_factuur': None,
            'afwijking_toelichting': 'Regel staat in systeem maar niet op factuur'
        }
        resultaten.append(resultaat)
    
    # Verwerk niet-gematchte factuurregels
    for factuur_idx in matches['factuur_zonder_match']:
        factuur_row = df_factuur.iloc[factuur_idx]
        
        resultaat = {
            'status': config.STATUS_ONTBREEKT_SYSTEEM,
            'artikelcode': factuur_row[config.CANON_ARTIKELCODE],
            'artikelnaam': factuur_row[config.CANON_ARTIKELNAAM],
            'aantal_systeem': None,
            'aantal_factuur': factuur_row[config.CANON_AANTAL],
            'prijs_systeem': None,
            'prijs_factuur': factuur_row[config.CANON_PRIJS],
            'totaal_systeem': None,
            'totaal_factuur': factuur_row[config.CANON_TOTAAL],
            'btw_systeem': None,
            'btw_factuur': factuur_row[config.CANON_BTW],
            'afwijking_toelichting': 'Regel staat op factuur maar niet in systeem'
        }
        resultaten.append(resultaat)
    
    # Converteer naar DataFrame
    df_resultaat = pd.DataFrame(resultaten)

    # Sorteer op status prioriteit (afwijkingen bovenaan)
    df_resultaat = _sort_by_status_priority(df_resultaat)

    return df_resultaat


def match_regels(df_systeem: pd.DataFrame, df_factuur: pd.DataFrame) -> Dict[str, List]:
    """
    Matcht regels tussen systeem en factuur.
    
    Strategie:
    1. Primair: match op artikelcode (indien beide niet None)
    2. Fallback: match op genormaliseerde artikelnaam
    3. Houd bij welke regels al gematcht zijn
    
    Parameters
    ----------
    df_systeem : pd.DataFrame
        Systeemexport.
    df_factuur : pd.DataFrame
        Leveranciersfactuur.
    
    Returns
    -------
    dict
        {
            'gematchte_regels': [(systeem_idx, factuur_idx), ...],
            'systeem_zonder_match': [idx, ...],
            'factuur_zonder_match': [idx, ...]
        }
    """
    
    gematchte_regels = []
    gematchte_factuur_indices = set()
    gematchte_systeem_indices = set()
    
    # STAP 1: Match op artikelcode
    for sys_idx, sys_row in df_systeem.iterrows():
        sys_code = sys_row[config.CANON_ARTIKELCODE]
        
        # Skip als geen artikelcode
        if pd.isna(sys_code) or sys_code is None:
            continue
        
        # Zoek match in factuur
        for fac_idx, fac_row in df_factuur.iterrows():
            # Skip als al gematcht
            if fac_idx in gematchte_factuur_indices:
                continue
            
            fac_code = fac_row[config.CANON_ARTIKELCODE]
            
            # Skip als geen artikelcode
            if pd.isna(fac_code) or fac_code is None:
                continue
            
            # Check match
            if str(sys_code).strip() == str(fac_code).strip():
                gematchte_regels.append((sys_idx, fac_idx))
                gematchte_factuur_indices.add(fac_idx)
                gematchte_systeem_indices.add(sys_idx)
                break  # Een systeemregel kan maar één match hebben
    
    # STAP 2: Fallback match op artikelnaam
    for sys_idx, sys_row in df_systeem.iterrows():
        # Skip als al gematcht
        if sys_idx in gematchte_systeem_indices:
            continue
        
        sys_naam = sys_row[config.CANON_ARTIKELNAAM]
        
        # Skip als geen naam
        if pd.isna(sys_naam) or sys_naam is None:
            continue
        
        # Normaliseer naam
        sys_naam_norm = normaliseer_naam(sys_naam)
        
        # Skip als lege naam na normalisatie
        if not sys_naam_norm:
            continue
        
        # Zoek match in factuur
        for fac_idx, fac_row in df_factuur.iterrows():
            # Skip als al gematcht
            if fac_idx in gematchte_factuur_indices:
                continue
            
            fac_naam = fac_row[config.CANON_ARTIKELNAAM]
            
            # Skip als geen naam
            if pd.isna(fac_naam) or fac_naam is None:
                continue
            
            # Normaliseer naam
            fac_naam_norm = normaliseer_naam(fac_naam)
            
            # Check match
            if sys_naam_norm == fac_naam_norm and fac_naam_norm != "":
                gematchte_regels.append((sys_idx, fac_idx))
                gematchte_factuur_indices.add(fac_idx)
                gematchte_systeem_indices.add(sys_idx)
                break  # Een systeemregel kan maar één match hebben
    
    # STAP 3: Bepaal welke regels niet gematcht zijn
    alle_systeem_indices = set(df_systeem.index)
    alle_factuur_indices = set(df_factuur.index)
    
    systeem_zonder_match = list(alle_systeem_indices - gematchte_systeem_indices)
    factuur_zonder_match = list(alle_factuur_indices - gematchte_factuur_indices)
    
    return {
        'gematchte_regels': gematchte_regels,
        'systeem_zonder_match': systeem_zonder_match,
        'factuur_zonder_match': factuur_zonder_match
    }


def normaliseer_naam(naam: str) -> str:
    """
    Normaliseert een artikelnaam voor matching.
    
    - Lowercase
    - Trim whitespace
    - Verwijder dubbele spaties
    
    Parameters
    ----------
    naam : str
        Originele naam.
    
    Returns
    -------
    str
        Genormaliseerde naam.
    """
    
    if naam is None or pd.isna(naam):
        return ""
    
    # Lowercase, trim, verwijder dubbele spaties
    genormaliseerd = ' '.join(str(naam).lower().split())
    
    return genormaliseerd


def bereken_effectieve_prijs(aantal: float, totaal: float, prijs_per_stuk: float = None) -> float:
    """
    Bepaalt de enige prijs die relevant is voor vergelijking:
    de uiteindelijke betaalde prijs per artikel.

    Deze functie is de ENIGE BRON VAN WAARHEID voor prijsbepaling.

    Logica:
    1. Als prijs_per_stuk expliciet bekend is → gebruik die
    2. Anders: bereken uit totaal / aantal (indien mogelijk)
    3. Anders: None (niet vergelijkbaar)

    Parameters
    ----------
    aantal : float
        Aantal artikelen.
    totaal : float
        Totaalbedrag voor deze regel.
    prijs_per_stuk : float, optional
        Expliciete prijs per stuk (indien aanwezig).

    Returns
    -------
    float or None
        Effectieve prijs per stuk, of None indien niet bepaalbaar.

    Voorbeelden
    -----------
    >>> bereken_effectieve_prijs(10, 100, prijs_per_stuk=10.0)
    10.0
    >>> bereken_effectieve_prijs(10, 100, prijs_per_stuk=None)
    10.0
    >>> bereken_effectieve_prijs(10, None, prijs_per_stuk=None)
    None
    """
    # Prioriteit 1: Expliciet opgegeven prijs per stuk
    if pd.notna(prijs_per_stuk) and prijs_per_stuk is not None:
        return float(prijs_per_stuk)

    # Prioriteit 2: Bereken uit totaal / aantal
    if pd.notna(aantal) and pd.notna(totaal) and aantal > 0:
        return float(totaal) / float(aantal)

    # Kan niet bepaald worden
    return None


def vergelijk_regel(systeem_row: pd.Series, factuur_row: pd.Series) -> Dict:
    """
    Vergelijkt één systeemregel met één factuurregel.

    NIEUWE BUSINESS REGEL (v1.3 - Business Logic Correctie):
    ========================================================
    Een artikel mag ALLEEN als "AFWIJKING" worden gemarkeerd als:
    1. Het aantal verschilt (buiten tolerantie), OF
    2. De uiteindelijke betaalde prijs per artikel verschilt (buiten tolerantie)

    NIETS ANDERS mag een afwijking veroorzaken.

    Velden zoals bruto_prijs, netto_prijs, korting, staffel, BTW, totaalbedrag
    zijn INFORMATIEF maar mogen NOOIT zelfstandig een afwijking triggeren.

    Dit voorkomt valse afwijkingen door verschillende prijsopbouwen tussen leveranciers.

    Parameters
    ----------
    systeem_row : pd.Series
        Regel uit systeemexport.
    factuur_row : pd.Series
        Regel uit leveranciersfactuur.

    Returns
    -------
    dict
        Resultaat met status, waarden en toelichting.
    """

    afwijkingen = []

    # =========================================================================
    # STAP 1: VERGELIJK AANTAL (ENIGE CRITERIUM 1)
    # =========================================================================
    aantal_sys = systeem_row[config.CANON_AANTAL]
    aantal_fac = factuur_row[config.CANON_AANTAL]
    aantal_vergelijkbaar = pd.notna(aantal_sys) and pd.notna(aantal_fac)

    if aantal_vergelijkbaar:
        aantal_afwijking = vergelijk_numeriek(
            aantal_sys,
            aantal_fac,
            config.TOLERANTIE_AANTAL,
            'aantal'
        )
        if aantal_afwijking:
            afwijkingen.append(aantal_afwijking)

    # =========================================================================
    # STAP 2: VERGELIJK EFFECTIEVE PRIJS (ENIGE CRITERIUM 2)
    # =========================================================================
    # Bepaal effectieve prijs per kant (uiteindelijke betaalde prijs)
    prijs_sys = bereken_effectieve_prijs(
        aantal_sys,
        systeem_row[config.CANON_TOTAAL],
        systeem_row[config.CANON_PRIJS]
    )
    prijs_fac = bereken_effectieve_prijs(
        aantal_fac,
        factuur_row[config.CANON_TOTAAL],
        factuur_row[config.CANON_PRIJS]
    )

    prijs_vergelijkbaar = (prijs_sys is not None) and (prijs_fac is not None)

    if prijs_vergelijkbaar:
        prijs_afwijking = vergelijk_numeriek(
            prijs_sys,
            prijs_fac,
            config.TOLERANTIE_PRIJS,
            'prijs per stuk',
            is_bedrag=True
        )
        if prijs_afwijking:
            afwijkingen.append(prijs_afwijking)

    # =========================================================================
    # STAP 3: BEPAAL STATUS (ALLEEN OP BASIS VAN AANTAL EN PRIJS)
    # =========================================================================
    if afwijkingen:
        status = config.STATUS_AFWIJKING
    elif not aantal_vergelijkbaar or not prijs_vergelijkbaar:
        # Indien aantal of prijs niet vergelijkbaar → gedeeltelijk
        status = config.STATUS_GEDEELTELIJK
    else:
        # Aantal en prijs kloppen → OK
        status = config.STATUS_OK

    # =========================================================================
    # STAP 4: BOUW TOELICHTING (SPECIFIEK EN VERKLAARBAAR)
    # =========================================================================
    if afwijkingen:
        # Specifieke afwijking: "Aantal wijkt af: ...", "Prijs per stuk wijkt af: ..."
        toelichting = '; '.join(afwijkingen)
    elif not aantal_vergelijkbaar:
        toelichting = 'Aantal kon niet worden vergeleken (ontbrekende data)'
    elif not prijs_vergelijkbaar:
        toelichting = 'Prijs per stuk kon niet worden bepaald (ontbrekende data)'
    else:
        # Alles OK
        toelichting = 'Aantal en prijs komen overeen'

    # =========================================================================
    # STAP 5: BOUW RESULTAAT
    # =========================================================================
    # Bepaal welke prijs we tonen (kan berekend zijn of origineel)
    prijs_systeem_display = prijs_sys if prijs_sys is not None else systeem_row[config.CANON_PRIJS]
    prijs_factuur_display = prijs_fac if prijs_fac is not None else factuur_row[config.CANON_PRIJS]

    resultaat = {
        'status': status,
        'artikelcode': systeem_row[config.CANON_ARTIKELCODE] or factuur_row[config.CANON_ARTIKELCODE],
        'artikelnaam': systeem_row[config.CANON_ARTIKELNAAM] or factuur_row[config.CANON_ARTIKELNAAM],
        'aantal_systeem': aantal_sys,
        'aantal_factuur': aantal_fac,
        'prijs_systeem': prijs_systeem_display,
        'prijs_factuur': prijs_factuur_display,
        'totaal_systeem': systeem_row[config.CANON_TOTAAL],
        'totaal_factuur': factuur_row[config.CANON_TOTAAL],
        'btw_systeem': systeem_row[config.CANON_BTW],
        'btw_factuur': factuur_row[config.CANON_BTW],
        'afwijking_toelichting': toelichting
    }

    return resultaat


def vergelijk_tekstveld(waarde_systeem: str, waarde_factuur: str, veldnaam: str) -> Optional[str]:
    """
    Vergelijkt twee tekstvelden.
    
    Parameters
    ----------
    waarde_systeem : str
        Waarde uit systeem.
    waarde_factuur : str
        Waarde uit factuur.
    veldnaam : str
        Naam van het veld (voor in toelichting).
    
    Returns
    -------
    str or None
        Afwijkingsmelding indien verschillend, anders None.
    """
    
    # Als beide leeg/None → geen afwijking
    if (pd.isna(waarde_systeem) or waarde_systeem is None) and \
       (pd.isna(waarde_factuur) or waarde_factuur is None):
        return None
    
    # Normaliseer voor vergelijking
    sys_norm = normaliseer_naam(waarde_systeem) if waarde_systeem else ""
    fac_norm = normaliseer_naam(waarde_factuur) if waarde_factuur else ""
    
    if sys_norm != fac_norm:
        return f"{veldnaam} verschilt (systeem: '{waarde_systeem}', factuur: '{waarde_factuur}')"
    
    return None


def vergelijk_numeriek(
    waarde_systeem: float,
    waarde_factuur: float,
    tolerantie: float,
    veldnaam: str,
    is_bedrag: bool = False,
    is_percentage: bool = False
) -> Optional[str]:
    """
    Vergelijkt twee numerieke waarden met tolerantie.
    
    Parameters
    ----------
    waarde_systeem : float
        Waarde uit systeem.
    waarde_factuur : float
        Waarde uit factuur.
    tolerantie : float
        Maximaal toegestaan verschil.
    veldnaam : str
        Naam van het veld (voor in toelichting).
    is_bedrag : bool
        True = format als bedrag (€X.XX).
    is_percentage : bool
        True = format als percentage (X%).
    
    Returns
    -------
    str or None
        Afwijkingsmelding indien buiten tolerantie, anders None.
    """
    
    verschil = abs(waarde_systeem - waarde_factuur)
    
    if verschil > tolerantie:
        if is_bedrag:
            return (
                f"{veldnaam} wijkt af "
                f"(verwacht €{waarde_systeem:.2f}, gekregen €{waarde_factuur:.2f}, "
                f"verschil: €{verschil:.2f})"
            )
        elif is_percentage:
            return (
                f"{veldnaam} wijkt af "
                f"(verwacht {waarde_systeem:.1f}%, gekregen {waarde_factuur:.1f}%)"
            )
        else:
            return (
                f"{veldnaam} verschilt "
                f"(verwacht {waarde_systeem}, gekregen {waarde_factuur})"
            )
    
    return None


def _sort_by_status_priority(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort comparison results by status priority.
    
    Priority order (most important first):
    1. AFWIJKING
    2. ONTBREEKT OP FACTUUR
    3. ONTBREEKT IN SYSTEEM  
    4. GEDEELTELIJK
    5. OK
    
    Args:
        df: DataFrame with comparison results containing 'status' column
        
    Returns:
        DataFrame sorted by status priority (original data unchanged)
    """
    if df.empty:
        return df
    
    if 'status' not in df.columns:
        return df
    
    # Gebruik de ECHTE status waarden uit config.py
    status_priority = {
        config.STATUS_AFWIJKING: 0,
        config.STATUS_ONTBREEKT_FACTUUR: 1,
        config.STATUS_ONTBREEKT_SYSTEEM: 2,
        config.STATUS_GEDEELTELIJK: 3,
        config.STATUS_OK: 4,
    }
    
    df_sorted = df.copy()
    df_sorted['_sort_priority'] = df_sorted['status'].map(status_priority)
    
    # ✅ CORRECTE PARAMETER: na_position='last' (niet na_last=True)
    df_sorted = df_sorted.sort_values('_sort_priority', na_position='last')
    
    df_sorted = df_sorted.drop(columns=['_sort_priority'])
    df_sorted = df_sorted.reset_index(drop=True)
    
    return df_sorted


  