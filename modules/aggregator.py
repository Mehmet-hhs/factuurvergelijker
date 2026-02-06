# aggregator.py
# v1.3: Multi-document aggregatie naar artikelniveau

"""
aggregator.py
=============

Verantwoordelijkheid:
    Aggregeert meerdere genormaliseerde documenten (pakbonnen, facturen)
    tot één geconsolideerd artikeloverzicht.

Architectuur:
    reader → validator → normalizer → **aggregator (N→1)** → comparator → reporter

Gebruik:
    >>> result = aggregeer_documenten(
    ...     df_list=[df_pakbon1, df_pakbon2, df_factuur],
    ...     document_namen=["pakbon_01.pdf", "pakbon_02.pdf", "factuur.pdf"],
    ...     document_rollen=["pakbon", "pakbon", "factuur"]
    ... )
    >>> result.df_aggregaat  # Geconsolideerde artikellijst
    >>> result.metadata      # Aantal docs, regels, etc.
    >>> result.warnings      # Informatieve meldingen (geen blokkeerders)

Aggregatie regels:
    - Artikelen met zelfde code + naam worden samengevoegd
    - aantal → SUM
    - totaal → SUM
    - prijs_per_stuk → weighted average (totaal / aantal)
    - artikelnaam → eerste originele waarde (niet genormaliseerd)
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Voeg parent directory toe voor config
sys.path.append(str(Path(__file__).parent.parent))
import config

# Hergebruik bestaande normalisatiefunctie
from modules.normalizer import maak_genormaliseerde_naam


@dataclass
class AggregatieResultaat:
    """
    Resultaat van multi-document aggregatie.

    Attributes
    ----------
    df_aggregaat : pd.DataFrame
        Geconsolideerde artikellijst met geaggregeerde waarden.
    metadata : Dict[str, Any]
        Metadata over aggregatie proces.
    warnings : List[str]
        Informatieve meldingen (geen blokkeerders).
    """
    df_aggregaat: pd.DataFrame
    metadata: Dict[str, Any]
    warnings: List[str]


def aggregeer_documenten(
    df_list: List[pd.DataFrame],
    document_namen: List[str],
    document_rollen: List[str]
) -> AggregatieResultaat:
    """
    Aggregeert meerdere genormaliseerde documenten naar één artikeloverzicht.

    Parameters
    ----------
    df_list : List[pd.DataFrame]
        Lijst van genormaliseerde DataFrames (output van normalizer.py).
    document_namen : List[str]
        Namen van de documenten (voor tracking).
    document_rollen : List[str]
        Rol van elk document ('pakbon', 'factuur', 'onbekend').

    Returns
    -------
    AggregatieResultaat
        Geaggregeerde data + metadata + warnings.

    Raises
    ------
    ValueError
        Als df_list leeg is of lijsten verschillende lengtes hebben.

    Voorbeelden
    -----------
    >>> df1 = pd.DataFrame({
    ...     'artikelcode': ['A123', 'B456'],
    ...     'artikelnaam': ['Widget', 'Gadget'],
    ...     'aantal': [10.0, 5.0],
    ...     'prijs_per_stuk': [5.0, 10.0],
    ...     'totaal': [50.0, 50.0],
    ...     'btw_percentage': [21.0, 21.0]
    ... })
    >>> df2 = pd.DataFrame({
    ...     'artikelcode': ['A123'],
    ...     'artikelnaam': ['Widget'],
    ...     'aantal': [5.0],
    ...     'prijs_per_stuk': [5.0],
    ...     'totaal': [25.0],
    ...     'btw_percentage': [21.0]
    ... })
    >>> result = aggregeer_documenten(
    ...     df_list=[df1, df2],
    ...     document_namen=["doc1.pdf", "doc2.pdf"],
    ...     document_rollen=["pakbon", "pakbon"]
    ... )
    >>> result.df_aggregaat.loc[result.df_aggregaat['artikelcode'] == 'A123', 'aantal'].values[0]
    15.0  # 10 + 5
    >>> result.df_aggregaat.loc[result.df_aggregaat['artikelcode'] == 'A123', 'totaal'].values[0]
    75.0  # 50 + 25
    """

    # Validatie input
    if not df_list:
        raise ValueError("df_list mag niet leeg zijn")

    if len(df_list) != len(document_namen) or len(df_list) != len(document_rollen):
        raise ValueError(
            f"Lengte mismatch: df_list={len(df_list)}, "
            f"document_namen={len(document_namen)}, "
            f"document_rollen={len(document_rollen)}"
        )

    # Edge case: 1 document = identity aggregatie
    if len(df_list) == 1:
        return _aggregeer_enkel_document(df_list[0], document_namen[0], document_rollen[0])

    # Initialiseer tracking
    warnings = []
    totaal_regels_input = 0
    lege_documenten = []

    # Filter en valideer documenten
    df_list_valid = []
    document_namen_valid = []
    document_rollen_valid = []

    for idx, (df, naam, rol) in enumerate(zip(df_list, document_namen, document_rollen)):
        if df is None or df.empty:
            warnings.append(f"Document '{naam}' is leeg en wordt overgeslagen")
            lege_documenten.append(idx)
            continue

        totaal_regels_input += len(df)
        df_list_valid.append(df)
        document_namen_valid.append(naam)
        document_rollen_valid.append(rol)

    # Check of er na filtering nog documenten over zijn
    if not df_list_valid:
        raise ValueError("Alle documenten zijn leeg - kan niet aggregeren")

    # Edge case: na filtering 1 document over
    if len(df_list_valid) == 1:
        result = _aggregeer_enkel_document(
            df_list_valid[0],
            document_namen_valid[0],
            document_rollen_valid[0]
        )
        # Voeg warnings over overgeslagen documenten toe
        result.warnings.extend(warnings)
        # Update metadata met volledige info
        result.metadata['aantal_documenten'] = len(df_list)
        result.metadata['lege_documenten'] = lege_documenten
        return result

    # Concateneer alle DataFrames
    df_combined = pd.concat(df_list_valid, ignore_index=True)

    # Filter regels met aantal = 0 of None
    df_filtered = df_combined[
        (df_combined[config.CANON_AANTAL].notna()) &
        (df_combined[config.CANON_AANTAL] > 0)
    ].copy()

    if len(df_combined) - len(df_filtered) > 0:
        warnings.append(
            f"{len(df_combined) - len(df_filtered)} regels met aantal=0 overgeslagen"
        )

    # Detecteer prijs inconsistenties VOOR aggregatie
    prijs_warnings = _detecteer_prijs_inconsistenties(df_filtered)
    warnings.extend(prijs_warnings)

    # Maak genormaliseerde artikelnaam kolom (voor grouping)
    df_filtered['_artikelnaam_normalized'] = df_filtered[config.CANON_ARTIKELNAAM].apply(
        maak_genormaliseerde_naam
    )

    # Group by: artikelcode + genormaliseerde artikelnaam
    # Gebruik .fillna("") voor artikelcode om None's te groeperen
    groupby_cols = ['_artikelcode_filled', '_artikelnaam_normalized']
    df_filtered['_artikelcode_filled'] = df_filtered[config.CANON_ARTIKELCODE].fillna("")

    # Aggregatie functies
    agg_dict = {
        config.CANON_AANTAL: 'sum',
        config.CANON_TOTAAL: 'sum',
        # Artikelnaam: eerste niet-None waarde (origineel, niet genormaliseerd)
        config.CANON_ARTIKELNAAM: lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else None,
        # BTW: most frequent (of None)
        config.CANON_BTW: lambda x: x.mode().iloc[0] if len(x.mode()) > 0 and pd.notna(x.mode().iloc[0]) else None,
        # Artikelcode: eerste niet-None waarde
        config.CANON_ARTIKELCODE: lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else None,
    }

    df_aggregaat = df_filtered.groupby(groupby_cols, as_index=False).agg(agg_dict)

    # Bereken weighted average prijs
    df_aggregaat[config.CANON_PRIJS] = (
        df_aggregaat[config.CANON_TOTAAL] / df_aggregaat[config.CANON_AANTAL]
    )

    # Drop helper kolommen
    df_aggregaat = df_aggregaat.drop(columns=['_artikelcode_filled', '_artikelnaam_normalized'], errors='ignore')

    # Zorg voor juiste kolomvolgorde
    df_aggregaat = df_aggregaat[config.CANONIEKE_KOLOMMEN]

    # Metadata
    metadata = {
        'aantal_documenten': len(df_list),
        'aantal_documenten_verwerkt': len(df_list_valid),
        'document_namen': document_namen_valid,
        'document_rollen': document_rollen_valid,
        'totaal_regels_input': totaal_regels_input,
        'totaal_regels_output': len(df_aggregaat),
        'lege_documenten': lege_documenten,
    }

    return AggregatieResultaat(
        df_aggregaat=df_aggregaat,
        metadata=metadata,
        warnings=warnings
    )


def _aggregeer_enkel_document(
    df: pd.DataFrame,
    document_naam: str,
    document_rol: str
) -> AggregatieResultaat:
    """
    Identity aggregatie voor 1 document (geen transformatie).

    Parameters
    ----------
    df : pd.DataFrame
        Genormaliseerd DataFrame.
    document_naam : str
        Naam van document.
    document_rol : str
        Rol van document.

    Returns
    -------
    AggregatieResultaat
        Document zonder wijziging + metadata.
    """

    # Filter regels met aantal = 0 of None
    df_filtered = df[
        (df[config.CANON_AANTAL].notna()) &
        (df[config.CANON_AANTAL] > 0)
    ].copy()

    warnings = []
    if len(df) - len(df_filtered) > 0:
        warnings.append(
            f"{len(df) - len(df_filtered)} regels met aantal=0 overgeslagen"
        )

    metadata = {
        'aantal_documenten': 1,
        'aantal_documenten_verwerkt': 1,
        'document_namen': [document_naam],
        'document_rollen': [document_rol],
        'totaal_regels_input': len(df),
        'totaal_regels_output': len(df_filtered),
        'lege_documenten': [],
    }

    return AggregatieResultaat(
        df_aggregaat=df_filtered,
        metadata=metadata,
        warnings=warnings
    )


def _detecteer_prijs_inconsistenties(df: pd.DataFrame) -> List[str]:
    """
    Detecteert prijsverschillen binnen hetzelfde artikel over documenten heen.

    Waarschuwing wordt gegeven als een artikel in meerdere documenten voorkomt
    met verschillende prijzen (meer dan €0.01 verschil).

    Parameters
    ----------
    df : pd.DataFrame
        Gecombineerd DataFrame (vóór aggregatie).

    Returns
    -------
    List[str]
        Lijst van warnings (informatief, geen blokkeerders).

    Voorbeelden
    -----------
    >>> df = pd.DataFrame({
    ...     'artikelcode': ['A123', 'A123'],
    ...     'artikelnaam': ['Widget', 'Widget'],
    ...     'aantal': [10.0, 5.0],
    ...     'prijs_per_stuk': [5.00, 5.50],  # Verschil!
    ...     'totaal': [50.0, 27.5],
    ...     'btw_percentage': [21.0, 21.0]
    ... })
    >>> warnings = _detecteer_prijs_inconsistenties(df)
    >>> len(warnings)
    1
    >>> 'A123' in warnings[0]
    True
    """

    warnings = []

    # Maak genormaliseerde artikelnaam kolom
    df_check = df.copy()
    df_check['_artikelnaam_normalized'] = df_check[config.CANON_ARTIKELNAAM].apply(
        maak_genormaliseerde_naam
    )
    df_check['_artikelcode_filled'] = df_check[config.CANON_ARTIKELCODE].fillna("")

    # Group by artikel
    groupby_cols = ['_artikelcode_filled', '_artikelnaam_normalized']

    for (code, naam_norm), group in df_check.groupby(groupby_cols):
        # Skip als maar 1 regel (geen inconsistentie mogelijk)
        if len(group) <= 1:
            continue

        # Check prijsverschil
        prijzen = group[config.CANON_PRIJS].dropna().unique()

        if len(prijzen) <= 1:
            continue  # Alle prijzen zijn gelijk (of None)

        # Check of verschil groter is dan tolerantie
        max_prijs = prijzen.max()
        min_prijs = prijzen.min()
        verschil = max_prijs - min_prijs

        if verschil > config.TOLERANTIE_PRIJS:
            # Haal originele artikelnaam op (niet genormaliseerd)
            originele_naam = group[config.CANON_ARTIKELNAAM].dropna().iloc[0]
            originele_code = group[config.CANON_ARTIKELCODE].dropna().iloc[0] if code != "" else "zonder code"

            prijzen_str = ', '.join([f"€{p:.2f}" for p in sorted(prijzen)])

            warnings.append(
                f"Artikel {originele_code} ({originele_naam}) heeft verschillende "
                f"prijzen tussen documenten ({prijzen_str}). Gemiddelde prijs gebruikt."
            )

    return warnings


# ============================================================================
# UTILITY FUNCTIES
# ============================================================================

def validate_aggregatie_resultaat(result: AggregatieResultaat) -> bool:
    """
    Valideert of aggregatie resultaat correct is gestructureerd.

    Parameters
    ----------
    result : AggregatieResultaat
        Resultaat om te valideren.

    Returns
    -------
    bool
        True als geldig, False anders.

    Voorbeelden
    -----------
    >>> result = AggregatieResultaat(
    ...     df_aggregaat=pd.DataFrame({'artikelnaam': ['Widget']}),
    ...     metadata={'aantal_documenten': 1},
    ...     warnings=[]
    ... )
    >>> validate_aggregatie_resultaat(result)
    True
    """

    # Check dataclass velden
    if not isinstance(result.df_aggregaat, pd.DataFrame):
        return False

    if not isinstance(result.metadata, dict):
        return False

    if not isinstance(result.warnings, list):
        return False

    # Check verplichte metadata velden
    verplichte_metadata = [
        'aantal_documenten',
        'document_namen',
        'document_rollen',
        'totaal_regels_input',
        'totaal_regels_output'
    ]

    for veld in verplichte_metadata:
        if veld not in result.metadata:
            return False

    # Check kolommen in df_aggregaat
    for kolom in config.CANONIEKE_KOLOMMEN:
        if kolom not in result.df_aggregaat.columns:
            return False

    return True
