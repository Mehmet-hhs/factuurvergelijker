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


def vergelijk_regel(systeem_row: pd.Series, factuur_row: pd.Series) -> Dict:
    """
    Vergelijkt één systeemregel met één factuurregel.
    
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
    alle_velden_vergelijkbaar = True
    
    # Vergelijk artikelnaam
    naam_afwijking = vergelijk_tekstveld(
        systeem_row[config.CANON_ARTIKELNAAM],
        factuur_row[config.CANON_ARTIKELNAAM],
        'artikelnaam'
    )
    if naam_afwijking:
        afwijkingen.append(naam_afwijking)
    
    # Vergelijk aantal
    aantal_sys = systeem_row[config.CANON_AANTAL]
    aantal_fac = factuur_row[config.CANON_AANTAL]
    
    if pd.notna(aantal_sys) and pd.notna(aantal_fac):
        aantal_afwijking = vergelijk_numeriek(
            aantal_sys,
            aantal_fac,
            config.TOLERANTIE_AANTAL,
            'aantal'
        )
        if aantal_afwijking:
            afwijkingen.append(aantal_afwijking)
    else:
        alle_velden_vergelijkbaar = False
    
    # Vergelijk prijs
    prijs_sys = systeem_row[config.CANON_PRIJS]
    prijs_fac = factuur_row[config.CANON_PRIJS]
    
    if pd.notna(prijs_sys) and pd.notna(prijs_fac):
        prijs_afwijking = vergelijk_numeriek(
            prijs_sys,
            prijs_fac,
            config.TOLERANTIE_PRIJS,
            'prijs per stuk',
            is_bedrag=True
        )
        if prijs_afwijking:
            afwijkingen.append(prijs_afwijking)
    else:
        alle_velden_vergelijkbaar = False
    
    # Vergelijk totaal
    totaal_sys = systeem_row[config.CANON_TOTAAL]
    totaal_fac = factuur_row[config.CANON_TOTAAL]
    
    if pd.notna(totaal_sys) and pd.notna(totaal_fac):
        totaal_afwijking = vergelijk_numeriek(
            totaal_sys,
            totaal_fac,
            config.TOLERANTIE_TOTAAL,
            'totaalbedrag',
            is_bedrag=True
        )
        if totaal_afwijking:
            afwijkingen.append(totaal_afwijking)
    else:
        alle_velden_vergelijkbaar = False
    
    # Vergelijk BTW (optioneel)
    btw_sys = systeem_row[config.CANON_BTW]
    btw_fac = factuur_row[config.CANON_BTW]
    
    if pd.notna(btw_sys) and pd.notna(btw_fac):
        btw_afwijking = vergelijk_numeriek(
            btw_sys,
            btw_fac,
            config.TOLERANTIE_BTW,
            'BTW-percentage',
            is_percentage=True
        )
        if btw_afwijking:
            afwijkingen.append(btw_afwijking)
    # BTW is optioneel, dus niet meenemen in 'alle_velden_vergelijkbaar'
    
    # Bepaal status
    if afwijkingen:
        status = config.STATUS_AFWIJKING
    elif not alle_velden_vergelijkbaar:
        status = config.STATUS_GEDEELTELIJK
    else:
        status = config.STATUS_OK
    
    # Bouw toelichting
    if afwijkingen:
        toelichting = '; '.join(afwijkingen)
    elif not alle_velden_vergelijkbaar:
        toelichting = 'Niet alle velden waren vergelijkbaar'
    else:
        toelichting = 'Alle velden komen overeen'
    
    # Bouw resultaat
    resultaat = {
        'status': status,
        'artikelcode': systeem_row[config.CANON_ARTIKELCODE] or factuur_row[config.CANON_ARTIKELCODE],
        'artikelnaam': systeem_row[config.CANON_ARTIKELNAAM] or factuur_row[config.CANON_ARTIKELNAAM],
        'aantal_systeem': systeem_row[config.CANON_AANTAL],
        'aantal_factuur': factuur_row[config.CANON_AANTAL],
        'prijs_systeem': systeem_row[config.CANON_PRIJS],
        'prijs_factuur': factuur_row[config.CANON_PRIJS],
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
    2. ONTBREEKT_OP_FACTUUR
    3. ONTBREEKT_IN_SYSTEEM
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
        # Geen status kolom? Return as-is (defensive)
        return df
    
    status_priority = {
        'AFWIJKING': 0,
        'ONTBREEKT_OP_FACTUUR': 1,
        'ONTBREEKT_IN_SYSTEEM': 2,
        'GEDEELTELIJK': 3,
        'OK': 4,
    }
    
    df_sorted = df.copy()
    df_sorted['_sort_priority'] = df_sorted['status'].map(status_priority)
    df_sorted = df_sorted.sort_values('_sort_priority', na_last=True)
    df_sorted = df_sorted.drop(columns=['_sort_priority'])
    df_sorted = df_sorted.reset_index(drop=True)
    
    return df_sorted


def compare(df_source_a: pd.DataFrame, df_source_b: pd.DataFrame, 
            config: dict = None) -> pd.DataFrame:
    """
    [... bestaande docstring ...]
    """
    
    # [... alle bestaande code ...]
    
    # Bouw results DataFrame
    results_df = pd.DataFrame(results)
    
    # ✨ NIEUW: Sorteer op status prioriteit
    results_df = _sort_by_status_priority(results_df)
    
    return results_df