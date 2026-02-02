# data_reader.py
# Fase 3: Inlezen van CSV-bestanden

"""
data_reader.py
==============

Verantwoordelijkheid:
    Veilig inlezen van CSV-bestanden en omzetten naar pandas DataFrame.

Functies:
    - lees_csv: Leest CSV-bestand en retourneert DataFrame

Foutafhandeling:
    - Lege bestanden → ValueError
    - Niet-CSV bestanden → ValueError
    - Lees/encoding problemen → IOError
"""

import pandas as pd
from pathlib import Path
from typing import Union
import sys

# Voeg parent directory toe zodat config.py gevonden kan worden
sys.path.append(str(Path(__file__).parent.parent))


def lees_csv(bestandspad: Union[str, Path]) -> pd.DataFrame:
    """
    Leest een CSV-bestand en retourneert een pandas DataFrame.
    
    Parameters
    ----------
    bestandspad : str of Path
        Pad naar het CSV-bestand dat ingelezen moet worden.
    
    Returns
    -------
    pd.DataFrame
        DataFrame met de inhoud van het CSV-bestand.
    
    Raises
    ------
    FileNotFoundError
        Als het bestand niet bestaat.
    ValueError
        Als het bestand leeg is of geen geldige CSV is.
    IOError
        Bij lees- of encoding-problemen.
    
    Voorbeelden
    -----------
    >>> df = lees_csv("export_januari.csv")
    >>> df.shape
    (247, 6)
    """
    
    # Converteer naar Path object voor consistente afhandeling
    pad = Path(bestandspad)
    
    # Controleer of bestand bestaat
    if not pad.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {pad}")
    
    # Controleer of bestand niet leeg is
    if pad.stat().st_size == 0:
        raise ValueError(f"Bestand is leeg: {pad}")
    
    # Probeer CSV in te lezen
    try:
        # Lees CSV met standaard instellingen
        # - Verwacht header in eerste regel
        # - Gebruikt comma als separator (standaard)
        # - Probeert automatisch encoding te detecteren
        df = pd.read_csv(
            pad,
            encoding='utf-8',  # Probeer eerst UTF-8
            sep=',',
            skipinitialspace=True,  # Verwijder spaties na separator
        )
        
    except UnicodeDecodeError:
        # Fallback naar latin-1 encoding (vaak gebruikt in Nederlandse systemen)
        try:
            df = pd.read_csv(
                pad,
                encoding='latin-1',
                sep=',',
                skipinitialspace=True,
            )
        except Exception as e:
            raise IOError(f"Kan bestand niet lezen met UTF-8 of Latin-1 encoding: {e}")
    
    except pd.errors.EmptyDataError:
        raise ValueError(f"CSV-bestand bevat geen data: {pad}")
    
    except pd.errors.ParserError as e:
        raise ValueError(f"Ongeldige CSV-structuur in {pad}: {e}")
    
    except Exception as e:
        raise IOError(f"Onverwachte fout bij lezen van {pad}: {e}")
    
    # Controleer of DataFrame rijen bevat
    if df.empty:
        raise ValueError(f"CSV-bestand bevat geen data-rijen: {pad}")
    
    # Controleer of DataFrame kolommen bevat
    if len(df.columns) == 0:
        raise ValueError(f"CSV-bestand bevat geen kolommen: {pad}")
    
    return df


def inspecteer_csv(bestandspad: Union[str, Path]) -> dict:
    """
    Geeft basisinformatie over een CSV-bestand zonder het volledig in te laden.
    
    Nuttig voor debugging en loggen.
    
    Parameters
    ----------
    bestandspad : str of Path
        Pad naar het CSV-bestand.
    
    Returns
    -------
    dict
        Dictionary met:
        - 'bestandsnaam': naam van het bestand
        - 'grootte_bytes': bestandsgrootte in bytes
        - 'aantal_rijen': aantal rijen (inclusief header)
        - 'kolommen': lijst met kolomnamen
    
    Voorbeelden
    -----------
    >>> info = inspecteer_csv("factuur.csv")
    >>> print(info['aantal_rijen'])
    248
    """
    
    pad = Path(bestandspad)
    
    if not pad.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {pad}")
    
    # Lees alleen eerste rij voor kolommen
    try:
        df_preview = pd.read_csv(pad, nrows=0, encoding='utf-8')
    except UnicodeDecodeError:
        df_preview = pd.read_csv(pad, nrows=0, encoding='latin-1')
    
    # Tel aantal regels (simpele benadering)
    with open(pad, 'r', encoding='utf-8', errors='ignore') as f:
        aantal_rijen = sum(1 for _ in f)
    
    return {
        'bestandsnaam': pad.name,
        'grootte_bytes': pad.stat().st_size,
        'aantal_rijen': aantal_rijen,  # Inclusief header
        'kolommen': df_preview.columns.tolist()
    }