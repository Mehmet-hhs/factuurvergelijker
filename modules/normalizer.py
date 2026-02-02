# normalizer.py
# Fase 3: Normalisatie naar canoniek datamodel

"""
normalizer.py
=============

Verantwoordelijkheid:
    Transformeren van ruwe CSV-data naar het canonieke datamodel.

Functies:
    - normaliseer_dataframe: Hoofd-functie voor normalisatie
    - map_kolommen: Hernoemt kolommen naar canonieke namen
    - voeg_ontbrekende_kolommen_toe: Vult missende velden aan met None
    - normaliseer_tekstvelden: Trim en lowercase waar nodig
    - converteer_datatypes: Zet kolommen om naar juiste types

Output:
    DataFrame met exacte structuur zoals gedefinieerd in Fase 2.
"""

import pandas as pd
import numpy as np
from typing import Dict
import sys
from pathlib import Path

# Voeg parent directory toe zodat config.py gevonden kan worden
sys.path.append(str(Path(__file__).parent.parent))
import config


def normaliseer_dataframe(df: pd.DataFrame, bron: str = "onbekend") -> pd.DataFrame:
    """
    Normaliseert een ruwe DataFrame naar het canonieke datamodel.
    
    Stappen:
    1. Kolommen mappen naar canonieke namen
    2. Ontbrekende kolommen toevoegen (waarde: None)
    3. Tekstvelden normaliseren (trim, lowercase voor matching)
    4. Datatypes converteren
    
    Parameters
    ----------
    df : pd.DataFrame
        Ruwe data uit CSV.
    bron : str
        Naam van de bron (voor logging/debugging).
    
    Returns
    -------
    pd.DataFrame
        Genormaliseerd DataFrame met canonieke kolomnamen en datatypes.
    
    Voorbeelden
    -----------
    >>> ruwe_data = pd.DataFrame({
    ...     'artikel': ['ART-001'],
    ...     'omschrijving': ['  Laptop Dell  '],
    ...     'qty': ['2'],
    ...     'price': ['599.00']
    ... })
    >>> genormaliseerd = normaliseer_dataframe(ruwe_data)
    >>> genormaliseerd.columns.tolist()
    ['artikelcode', 'artikelnaam', 'aantal', 'prijs_per_stuk', 'totaal', 'btw_percentage']
    """
    
    # Kopieer DataFrame om origineel niet te wijzigen
    df_norm = df.copy()
    
    # Stap 1: Map kolommen naar canonieke namen
    df_norm = map_kolommen(df_norm)
    
    # Stap 2: Voeg ontbrekende kolommen toe
    df_norm = voeg_ontbrekende_kolommen_toe(df_norm)
    
    # Stap 3: Normaliseer tekstvelden
    df_norm = normaliseer_tekstvelden(df_norm)
    
    # Stap 4: Converteer datatypes
    df_norm = converteer_datatypes(df_norm)
    
    # Stap 5: Zorg voor juiste kolomvolgorde
    df_norm = df_norm[config.CANONIEKE_KOLOMMEN]
    
    return df_norm


def map_kolommen(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hernoemt kolommen naar canonieke namen via mapping uit config.py.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame met originele kolomnamen.
    
    Returns
    -------
    pd.DataFrame
        DataFrame met hernoemde kolommen.
    """
    
    # Maak mapping dict: originele naam (lowercase) -> canonieke naam
    mapping = {}
    
    for kolom in df.columns:
        # Lowercase en stripped voor matching
        kolom_normalized = kolom.lower().strip()
        
        # Kijk of deze kolom in de mapping zit
        if kolom_normalized in config.LEVERANCIERS_MAPPING:
            canonieke_naam = config.LEVERANCIERS_MAPPING[kolom_normalized]
            mapping[kolom] = canonieke_naam
    
    # Hernoem kolommen
    df_renamed = df.rename(columns=mapping)
    
    return df_renamed


def voeg_ontbrekende_kolommen_toe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Voegt ontbrekende canonieke kolommen toe met waarde None.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame met mogelijk incomplete kolommen.
    
    Returns
    -------
    pd.DataFrame
        DataFrame met alle canonieke kolommen.
    """
    
    for canonieke_kolom in config.CANONIEKE_KOLOMMEN:
        if canonieke_kolom not in df.columns:
            df[canonieke_kolom] = None
    
    return df


def normaliseer_tekstvelden(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliseert tekstvelden voor consistente vergelijking.
    
    Acties:
    - Trim whitespace aan begin/einde
    - Verwijder dubbele spaties
    - Converteer lege strings naar None
    
    LET OP: Lowercase wordt NIET hier toegepast, maar alleen tijdens matching
            in comparator.py, zodat originele waarden bewaard blijven.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame met ruwe tekstvelden.
    
    Returns
    -------
    pd.DataFrame
        DataFrame met genormaliseerde tekstvelden.
    """
    
    tekst_kolommen = [config.CANON_ARTIKELCODE, config.CANON_ARTIKELNAAM]
    
    for kolom in tekst_kolommen:
        if kolom in df.columns:
            # Converteer naar string (voor None-veilige operaties)
            df[kolom] = df[kolom].astype(str)
            
            # Vervang 'None', 'nan', lege strings door echte None
            df[kolom] = df[kolom].replace(['None', 'nan', 'NaN', ''], None)
            
            # Trim whitespace en verwijder dubbele spaties (alleen voor niet-None waarden)
            df[kolom] = df[kolom].apply(
                lambda x: ' '.join(str(x).split()) if pd.notna(x) and x is not None else None
            )
    
    return df


def converteer_datatypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converteert kolommen naar de juiste datatypes.
    
    Numerieke kolommen → float
    Tekstvelden → blijven string (of None)
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame met mogelijk incorrecte datatypes.
    
    Returns
    -------
    pd.DataFrame
        DataFrame met correcte datatypes.
    """
    
    numerieke_kolommen = [
        config.CANON_AANTAL,
        config.CANON_PRIJS,
        config.CANON_TOTAAL,
        config.CANON_BTW
    ]
    
    for kolom in numerieke_kolommen:
        if kolom in df.columns:
            # Converteer naar float, ongeldige waarden worden NaN
            df[kolom] = pd.to_numeric(df[kolom], errors='coerce')
            
            # Vervang NaN door None (voor consistentie)
            df[kolom] = df[kolom].replace({np.nan: None})
    
    return df


def maak_genormaliseerde_naam(naam: str) -> str:
    """
    Hulpfunctie: normaliseert een artikelnaam voor matching.
    
    Gebruikt door comparator.py tijdens de fallback-matching op naam.
    
    Parameters
    ----------
    naam : str
        Originele artikelnaam.
    
    Returns
    -------
    str
        Genormaliseerde naam (lowercase, geen extra spaties).
    
    Voorbeelden
    -----------
    >>> maak_genormaliseerde_naam("  Laptop  DELL  ")
    'laptop dell'
    """
    
    if naam is None or pd.isna(naam):
        return ""
    
    # Lowercase, trim, verwijder dubbele spaties
    genormaliseerd = ' '.join(str(naam).lower().split())
    
    return genormaliseerd