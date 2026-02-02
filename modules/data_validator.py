# data_validator.py
# Fase 3: Validatie van kolommen en datatypes

"""
data_validator.py
=================

Verantwoordelijkheid:
    Valideren of een DataFrame voldoet aan de eisen van het canonieke datamodel.

Functies:
    - valideer_dataframe: Controleert kolommen en datatypes
    - controleer_verplichte_kolommen: Checkt aanwezigheid verplichte velden
    - controleer_datatypes: Controleert of conversie naar juiste types mogelijk is

Belangrijke noot:
    Deze module detecteert alleen problemen, voert GEEN correcties uit.
"""

import pandas as pd
from typing import Tuple, List
import sys
from pathlib import Path

# Voeg parent directory toe zodat config.py gevonden kan worden
sys.path.append(str(Path(__file__).parent.parent))
import config


def valideer_dataframe(df: pd.DataFrame, bron: str = "onbekend") -> Tuple[bool, List[str]]:
    """
    Valideert of een DataFrame voldoet aan het canonieke datamodel.
    
    Controleert:
    1. Aanwezigheid van verplichte kolommen
    2. Datatypes van numerieke kolommen (aantal, prijs, totaal, btw)
    
    Parameters
    ----------
    df : pd.DataFrame
        Het te valideren DataFrame.
    bron : str, optional
        Naam van de bron (bijv. "systeemexport" of "leveranciersfactuur")
        Gebruikt in foutmeldingen.
    
    Returns
    -------
    tuple
        (is_valid, foutmeldingen)
        - is_valid: bool - True als alles OK is
        - foutmeldingen: list[str] - Lijst met foutmeldingen (leeg als valid)
    
    Voorbeelden
    -----------
    >>> df = pd.DataFrame({'artikelnaam': ['Laptop'], 'aantal': [1]})
    >>> is_valid, fouten = valideer_dataframe(df)
    >>> is_valid
    False
    >>> fouten
    ['Verplichte kolom ontbreekt: prijs_per_stuk', 'Verplichte kolom ontbreekt: totaal']
    """
    
    foutmeldingen = []
    
    # Controleer 1: Verplichte kolommen
    kolom_fouten = controleer_verplichte_kolommen(df, bron)
    foutmeldingen.extend(kolom_fouten)
    
    # Controleer 2: Datatypes (alleen als kolommen bestaan)
    datatype_fouten = controleer_datatypes(df, bron)
    foutmeldingen.extend(datatype_fouten)
    
    # Controleer 3: DataFrame niet leeg
    if df.empty:
        foutmeldingen.append(f"[{bron}] DataFrame bevat geen rijen")
    
    is_valid = len(foutmeldingen) == 0
    
    return is_valid, foutmeldingen


def controleer_verplichte_kolommen(df: pd.DataFrame, bron: str = "onbekend") -> List[str]:
    """
    Controleert of alle verplichte kolommen aanwezig zijn.
    
    Parameters
    ----------
    df : pd.DataFrame
        Het te controleren DataFrame.
    bron : str
        Naam van de bron voor in foutmeldingen.
    
    Returns
    -------
    list[str]
        Lijst met foutmeldingen (leeg als alles OK).
    """
    
    fouten = []
    aanwezige_kolommen = set(df.columns)
    
    for verplichte_kolom in config.VERPLICHTE_VELDEN:
        if verplichte_kolom not in aanwezige_kolommen:
            fouten.append(
                f"[{bron}] Verplichte kolom ontbreekt: '{verplichte_kolom}'"
            )
    
    return fouten


def controleer_datatypes(df: pd.DataFrame, bron: str = "onbekend") -> List[str]:
    """
    Controleert of numerieke kolommen converteerbaar zijn naar float.
    
    Let op: Deze functie doet GEEN conversie, alleen detectie van problemen.
    
    Parameters
    ----------
    df : pd.DataFrame
        Het te controleren DataFrame.
    bron : str
        Naam van de bron voor in foutmeldingen.
    
    Returns
    -------
    list[str]
        Lijst met foutmeldingen (leeg als alles OK).
    """
    
    fouten = []
    
    # Definieer welke kolommen numeriek moeten zijn
    numerieke_kolommen = [
        config.CANON_AANTAL,
        config.CANON_PRIJS,
        config.CANON_TOTAAL,
        config.CANON_BTW
    ]
    
    for kolom in numerieke_kolommen:
        # Sla over als kolom niet bestaat (wordt door andere functie gemeld)
        if kolom not in df.columns:
            continue
        
        # Sla over als kolom volledig leeg is (is toegestaan voor optionele velden)
        if df[kolom].isna().all():
            continue
        
        # Probeer conversie naar float
        try:
            # Test conversie op niet-lege waarden
            niet_lege_waarden = df[kolom].dropna()
            if len(niet_lege_waarden) > 0:
                pd.to_numeric(niet_lege_waarden, errors='raise')
        
        except (ValueError, TypeError) as e:
            # Vind de eerste problematische waarde voor in foutmelding
            for idx, waarde in df[kolom].items():
                if pd.notna(waarde):
                    try:
                        float(waarde)
                    except (ValueError, TypeError):
                        fouten.append(
                            f"[{bron}] Kolom '{kolom}' bevat ongeldige numerieke waarde: "
                            f"'{waarde}' op rij {idx + 2}"  # +2 omdat: 0-indexed + header
                        )
                        break  # Eerste fout is genoeg
    
    # Controleer of tekstvelden geen volledig lege waarden zijn
    tekst_kolommen = [config.CANON_ARTIKELCODE, config.CANON_ARTIKELNAAM]
    
    for kolom in tekst_kolommen:
        if kolom not in df.columns:
            continue
        
        # Voor artikelnaam (verplicht): mag niet volledig leeg zijn
        if kolom == config.CANON_ARTIKELNAAM:
            if df[kolom].isna().all() or (df[kolom].astype(str).str.strip() == '').all():
                fouten.append(
                    f"[{bron}] Verplichte kolom '{kolom}' bevat alleen lege waarden"
                )
    
    return fouten


def valideer_canoniek_dataframe(df: pd.DataFrame, bron: str = "onbekend") -> Tuple[bool, List[str]]:
    """
    Strikte validatie voor een DataFrame dat al genormaliseerd zou moeten zijn.
    
    Controleert dat ALLE canonieke kolommen aanwezig zijn (ook optionele).
    
    Parameters
    ----------
    df : pd.DataFrame
        Het genormaliseerde DataFrame.
    bron : str
        Naam van de bron voor in foutmeldingen.
    
    Returns
    -------
    tuple
        (is_valid, foutmeldingen)
    """
    
    fouten = []
    aanwezige_kolommen = set(df.columns)
    verwachte_kolommen = set(config.CANONIEKE_KOLOMMEN)
    
    ontbrekende_kolommen = verwachte_kolommen - aanwezige_kolommen
    
    if ontbrekende_kolommen:
        fouten.append(
            f"[{bron}] Genormaliseerd DataFrame mist canonieke kolommen: "
            f"{', '.join(sorted(ontbrekende_kolommen))}"
        )
    
    # Roep ook standaard validatie aan
    standaard_valid, standaard_fouten = valideer_dataframe(df, bron)
    fouten.extend(standaard_fouten)
    
    is_valid = len(fouten) == 0
    
    return is_valid, fouten