# pdf_converter.py
# Converteert PDF-facturen naar DataFrames volgens leverancier-templates

"""
pdf_converter.py
================

Verantwoordelijkheid:
    PDF-bestanden van bekende leveranciers converteren naar DataFrames.
    Gebruikt template-based parsing voor betrouwbaarheid.

Functies:
    - detecteer_leverancier: Identificeer leverancier o.b.v. PDF-inhoud
    - converteer_pdf_naar_df: Parse PDF volgens template
    - valideer_pdf_extractie: Controleer volledigheid

Ondersteunde leveranciers:
    Gedefinieerd in config.PDF_LEVERANCIER_TEMPLATES
    Momenteel: 3 leveranciers (v1.2)

Output:
    DataFrame met canonieke kolommen (artikelcode, artikelnaam, aantal, prijs_per_stuk, totaal)

Foutafhandeling:
    - LeverancierOnbekendError: Geen template beschikbaar
    - PDFParseError: Extractie gefaald of onvolledig
    - PDFValidatieError: Data lijkt incorrect (te weinig regels, geen totaal)
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
import re
import sys

# PDF parsing libraries
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False

# Voeg parent directory toe voor imports
sys.path.append(str(Path(__file__).parent.parent))
import config


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class PDFConverterError(Exception):
    """Basis exception voor PDF conversie fouten."""
    pass


class LeverancierOnbekendError(PDFConverterError):
    """Leverancier heeft geen template of kan niet gedetecteerd worden."""
    pass


class PDFParseError(PDFConverterError):
    """PDF kon niet worden geparsed (corrupte PDF, scanned document, etc.)."""
    pass


class PDFValidatieError(PDFConverterError):
    """PDF is geparsed maar data lijkt onvolledig of incorrect."""
    pass


# ============================================================================
# HOOFDFUNCTIES
# ============================================================================

def detecteer_leverancier(pdf_pad: Path) -> Optional[str]:
    """
    Detecteert welke leverancier een PDF heeft aangemaakt.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF-bestand.

    Returns
    -------
    str of None
        Naam van leverancier (key uit PDF_LEVERANCIER_TEMPLATES),
        of None als onbekend.

    Voorbeelden
    -----------
    >>> detecteer_leverancier(Path("factuur_office_supplies.pdf"))
    "Office Supplies BV"
    >>> detecteer_leverancier(Path("onbekend.pdf"))
    None
    """

    if not PDFPLUMBER_AVAILABLE:
        raise PDFConverterError("pdfplumber library niet geïnstalleerd. Installeer met: pip install pdfplumber")

    # Lees eerste pagina tekst
    try:
        with pdfplumber.open(pdf_pad) as pdf:
            eerste_pagina = pdf.pages[0]
            tekst = eerste_pagina.extract_text()
    except Exception as e:
        raise PDFParseError(f"Kan PDF niet openen: {e}")

    # Check elke leverancier template
    for leverancier_naam, template in config.PDF_LEVERANCIER_TEMPLATES.items():
        identifier_regex = template.get('identifier_regex')
        if identifier_regex and re.search(identifier_regex, tekst, re.IGNORECASE):
            return leverancier_naam

    return None


def converteer_pdf_naar_df(
    pdf_pad: Path,
    leverancier: Optional[str] = None
) -> pd.DataFrame:
    """
    Converteert PDF naar DataFrame volgens leverancier-template.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF-bestand.
    leverancier : str, optional
        Naam leverancier. Als None, wordt auto-detectie gebruikt.

    Returns
    -------
    pd.DataFrame
        DataFrame met canonieke kolommen.

    Raises
    ------
    LeverancierOnbekendError
        Als leverancier niet wordt herkend of geen template heeft.
    PDFParseError
        Als PDF niet kan worden gelezen.
    PDFValidatieError
        Als extractie onvolledig is.

    Voorbeelden
    -----------
    >>> df = converteer_pdf_naar_df(Path("factuur.pdf"))
    >>> df.columns
    Index(['artikelcode', 'artikelnaam', 'aantal', 'prijs_per_stuk', 'totaal'])
    """

    # Auto-detectie als geen leverancier opgegeven
    if leverancier is None:
        leverancier = detecteer_leverancier(pdf_pad)
        if leverancier is None:
            raise LeverancierOnbekendError(
                f"Kan leverancier niet detecteren in PDF: {pdf_pad.name}"
            )

    # Haal template op
    if leverancier not in config.PDF_LEVERANCIER_TEMPLATES:
        raise LeverancierOnbekendError(
            f"Geen template beschikbaar voor leverancier: {leverancier}"
        )

    template = config.PDF_LEVERANCIER_TEMPLATES[leverancier]

    # Parse PDF volgens template
    parser_type = template.get('parser_type', 'pdfplumber')

    if parser_type == 'custom_text':
        # v1.2: Custom text-based parsing (Bosal, Fource, InternSysteem)
        df = _parse_met_custom_text_extraction(pdf_pad, template)
    elif parser_type == 'pdfplumber':
        # Legacy: table detection (niet gebruikt in v1.2)
        df = _parse_met_pdfplumber(pdf_pad, template)
    elif parser_type == 'tabula':
        # Legacy: table detection (niet gebruikt in v1.2)
        df = _parse_met_tabula(pdf_pad, template)
    else:
        raise PDFConverterError(f"Onbekend parser type: {parser_type}")

    # Valideer extractie
    valideer_pdf_extractie(df, template, leverancier)

    return df


def valideer_pdf_extractie(
    df: pd.DataFrame,
    template: Dict,
    leverancier: str
) -> None:
    """
    Valideert of PDF-extractie compleet en correct is.

    Parameters
    ----------
    df : pd.DataFrame
        Geëxtraheerde data.
    template : dict
        Template-configuratie.
    leverancier : str
        Naam leverancier.

    Raises
    ------
    PDFValidatieError
        Als data onvolledig of incorrect lijkt.

    Voorbeelden
    -----------
    >>> valideer_pdf_extractie(df, template, "Office Supplies BV")
    # Gooit error als < min_regels of verplichte velden ontbreken
    """

    validatie_config = template.get('validatie', {})

    # Check minimum aantal regels
    min_regels = validatie_config.get('min_regels', 1)
    if len(df) < min_regels:
        raise PDFValidatieError(
            f"Te weinig regels gevonden: {len(df)} (minimum: {min_regels}) "
            f"voor leverancier {leverancier}"
        )

    # Check verplichte kolommen
    vereiste_kolommen = ['artikelnaam', 'aantal', 'prijs_per_stuk']
    ontbrekende = [kol for kol in vereiste_kolommen if kol not in df.columns]
    if ontbrekende:
        raise PDFValidatieError(
            f"Verplichte kolommen ontbreken: {ontbrekende} "
            f"voor leverancier {leverancier}"
        )

    # Check of data niet leeg is
    if df['artikelnaam'].isna().all():
        raise PDFValidatieError(
            f"Geen artikelnamen gevonden in PDF voor leverancier {leverancier}"
        )


# ============================================================================
# HELPER FUNCTIES (PARSERS)
# ============================================================================

def _parse_met_pdfplumber(pdf_pad: Path, template: Dict) -> pd.DataFrame:
    """
    Parse PDF met pdfplumber library.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF.
    template : dict
        Template configuratie.

    Returns
    -------
    pd.DataFrame
        Geëxtraheerde tabel data.
    """

    if not PDFPLUMBER_AVAILABLE:
        raise PDFConverterError("pdfplumber niet geïnstalleerd")

    try:
        with pdfplumber.open(pdf_pad) as pdf:
            # Lees eerste pagina (kan uitgebreid worden naar meerdere pagina's)
            page = pdf.pages[0]

            # Gebruik bounding box als gespecificeerd
            tabel_area = template.get('tabel_area')
            if tabel_area:
                # Crop naar specifiek gebied
                page = page.within_bbox(tabel_area)

            # Extracteer tabel
            tables = page.extract_tables()

            if not tables:
                raise PDFParseError("Geen tabel gevonden in PDF")

            # Neem eerste tabel (kan uitgebreid worden)
            tabel = tables[0]

            # Converteer naar DataFrame
            df = pd.DataFrame(tabel[1:], columns=tabel[0])  # Eerste rij = headers

    except Exception as e:
        raise PDFParseError(f"Fout bij lezen PDF: {e}")

    # Map kolommen naar canonieke namen
    df = _map_kolommen_naar_canonical(df, template)

    return df


def _parse_met_tabula(pdf_pad: Path, template: Dict) -> pd.DataFrame:
    """
    Parse PDF met tabula-py library.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF.
    template : dict
        Template configuratie.

    Returns
    -------
    pd.DataFrame
        Geëxtraheerde tabel data.
    """

    if not TABULA_AVAILABLE:
        raise PDFConverterError("tabula-py niet geïnstalleerd")

    try:
        # Tabula leest automatisch tabellen
        tabel_area = template.get('tabel_area')

        if tabel_area:
            # Tabula gebruikt andere coördinaten syntax: [top, left, bottom, right]
            dfs = tabula.read_pdf(
                str(pdf_pad),
                area=tabel_area,
                pages=1,
                pandas_options={'header': 0}
            )
        else:
            dfs = tabula.read_pdf(
                str(pdf_pad),
                pages=1,
                pandas_options={'header': 0}
            )

        if not dfs:
            raise PDFParseError("Geen tabel gevonden in PDF")

        df = dfs[0]  # Eerste tabel

    except Exception as e:
        raise PDFParseError(f"Fout bij lezen PDF: {e}")

    # Map kolommen naar canonieke namen
    df = _map_kolommen_naar_canonical(df, template)

    return df


def _parse_met_custom_text_extraction(pdf_pad: Path, template: Dict) -> pd.DataFrame:
    """
    Parse PDF met custom text extraction (geen table detection).

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF.
    template : dict
        Template configuratie.

    Returns
    -------
    pd.DataFrame
        Geëxtraheerde tabel data.
    """
    # Extraheer alle tekst
    volledige_tekst = _extract_raw_text(pdf_pad)

    # Bepaal strategie
    parser_config = template.get('parser_config', {})
    strategy = parser_config.get('strategy')

    if strategy == 'single_line_pattern':
        # Bosal, InternSysteem
        return _parse_single_line_pattern(volledige_tekst, template)
    elif strategy == 'two_line_pattern':
        # Fource
        return _parse_two_line_pattern(volledige_tekst, template)
    else:
        raise PDFConverterError(f"Onbekende parsing strategy: {strategy}")


def _parse_single_line_pattern(tekst: str, template: Dict) -> pd.DataFrame:
    """
    Parse PDF waarbij alle velden op één regel staan.

    Gebruikt voor: Bosal, InternSysteem

    Parameters
    ----------
    tekst : str
        Ruwe PDF tekst.
    template : dict
        Template configuratie.

    Returns
    -------
    pd.DataFrame
        Geëxtraheerde regels als DataFrame.
    """
    parser_config = template.get('parser_config', {})
    header_pattern = parser_config.get('header_pattern')
    stop_pattern = parser_config.get('stop_pattern')
    line_pattern = parser_config.get('line_pattern')
    decimal_separator = parser_config.get('decimal_separator', '.')

    if not line_pattern:
        raise PDFConverterError("line_pattern niet gedefinieerd in template")

    # Split tekst in regels
    regels = tekst.split('\n')

    # Zoek start van tabel (na header)
    start_idx = 0
    if header_pattern:
        for idx, regel in enumerate(regels):
            if re.search(header_pattern, regel, re.IGNORECASE):
                start_idx = idx + 1
                break

    # Parse regels
    data_regels = []
    for regel in regels[start_idx:]:
        # Check stop condition
        if stop_pattern and re.search(stop_pattern, regel, re.IGNORECASE):
            break

        # Probeer regel te matchen
        match = re.match(line_pattern, regel.strip())
        if match:
            groups = match.groups()

            # Map naar kolommen volgens template
            kolom_mapping = template.get('kolom_mapping', {})
            row_data = {}

            for map_idx, canonical_naam in kolom_mapping.items():
                if map_idx < len(groups):
                    value = groups[map_idx]

                    # Clean numerieke velden
                    if canonical_naam in ['aantal', 'prijs_per_stuk', 'totaal']:
                        try:
                            value = _clean_numeric_value(value, decimal_separator)
                        except ValueError:
                            continue  # Skip rij met invalide data

                    row_data[canonical_naam] = value

            # Valideer rij
            if _validate_row_format(row_data, template):
                data_regels.append(row_data)

    if not data_regels:
        raise PDFParseError("Geen data regels gevonden in PDF")

    # Converteer naar DataFrame
    df = pd.DataFrame(data_regels)

    return df


def _parse_two_line_pattern(tekst: str, template: Dict) -> pd.DataFrame:
    """
    Parse PDF waarbij omschrijving op aparte regel staat.

    Gebruikt voor: Fource

    Parameters
    ----------
    tekst : str
        Ruwe PDF tekst.
    template : dict
        Template configuratie.

    Returns
    -------
    pd.DataFrame
        Geëxtraheerde regels als DataFrame.
    """
    parser_config = template.get('parser_config', {})
    header_pattern = parser_config.get('header_pattern')
    line_pattern = parser_config.get('line_pattern')
    decimal_separator = parser_config.get('decimal_separator', '.')

    if not line_pattern:
        raise PDFConverterError("line_pattern niet gedefinieerd in template")

    # Split tekst in regels
    regels = tekst.split('\n')

    # Zoek start van tabel
    start_idx = 0
    if header_pattern:
        for idx, regel in enumerate(regels):
            if re.search(header_pattern, regel, re.IGNORECASE):
                start_idx = idx + 1
                break

    # Parse regels (2-line pattern)
    data_regels = []
    idx = start_idx
    while idx < len(regels):
        regel = regels[idx].strip()

        # Probeer regel te matchen
        match = re.match(line_pattern, regel)
        if match:
            groups = match.groups()

            # Map naar kolommen
            kolom_mapping = template.get('kolom_mapping', {})
            row_data = {}

            for map_idx, canonical_naam in kolom_mapping.items():
                if map_idx < len(groups):
                    value = groups[map_idx]

                    # Clean numerieke velden
                    if canonical_naam in ['aantal', 'prijs_per_stuk', 'totaal']:
                        try:
                            value = _clean_numeric_value(value, decimal_separator)
                        except ValueError:
                            idx += 1
                            continue

                    row_data[canonical_naam] = value

            # Haal omschrijving van volgende regel
            if idx + 1 < len(regels):
                omschrijving = regels[idx + 1].strip()
                # Filter lege regels en regels die starten met cijfer (nieuwe data rij)
                if omschrijving and not re.match(r'^\d+\s', omschrijving):
                    row_data['artikelnaam'] = omschrijving
                    idx += 1  # Skip omschrijving regel

            # Valideer en voeg toe
            if _validate_row_format(row_data, template):
                data_regels.append(row_data)

        idx += 1

    if not data_regels:
        raise PDFParseError("Geen data regels gevonden in PDF")

    # Converteer naar DataFrame
    df = pd.DataFrame(data_regels)

    return df


def _map_kolommen_naar_canonical(df: pd.DataFrame, template: Dict) -> pd.DataFrame:
    """
    Map kolommen naar canonieke namen volgens template.

    Parameters
    ----------
    df : pd.DataFrame
        Ruwe DataFrame met leverancier-specifieke kolomnamen.
    template : dict
        Template met kolom_mapping.

    Returns
    -------
    pd.DataFrame
        DataFrame met canonieke kolomnamen.
    """

    kolom_mapping = template.get('kolom_mapping', {})

    if isinstance(list(kolom_mapping.keys())[0], int):
        # Mapping op basis van kolom-index
        nieuwe_kolommen = {}
        for idx, canonical_naam in kolom_mapping.items():
            if idx < len(df.columns):
                nieuwe_kolommen[df.columns[idx]] = canonical_naam

        df = df.rename(columns=nieuwe_kolommen)
    else:
        # Mapping op basis van kolomnaam
        df = df.rename(columns=kolom_mapping)

    # Selecteer alleen canonieke kolommen die bestaan
    beschikbare_canonical = [
        kol for kol in ['artikelcode', 'artikelnaam', 'aantal', 'prijs_per_stuk', 'totaal']
        if kol in df.columns
    ]

    df = df[beschikbare_canonical]

    # Clean data types
    if 'aantal' in df.columns:
        df['aantal'] = pd.to_numeric(df['aantal'], errors='coerce')

    if 'prijs_per_stuk' in df.columns:
        df['prijs_per_stuk'] = pd.to_numeric(df['prijs_per_stuk'], errors='coerce')

    if 'totaal' in df.columns:
        df['totaal'] = pd.to_numeric(df['totaal'], errors='coerce')

    return df


# ============================================================================
# HELPER FUNCTIES (v1.2 - custom text extraction)
# ============================================================================

def _extract_raw_text(pdf_pad: Path) -> str:
    """
    Extraheert ruwe tekst uit alle pagina's van een PDF.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF-bestand.

    Returns
    -------
    str
        Alle tekst uit PDF, pagina's gescheiden door newlines.

    Raises
    ------
    PDFParseError
        Als PDF niet kan worden gelezen.
    """
    if not PDFPLUMBER_AVAILABLE:
        raise PDFConverterError("pdfplumber niet geïnstalleerd")

    try:
        tekst_alle_paginas = []
        with pdfplumber.open(pdf_pad) as pdf:
            for pagina in pdf.pages:
                pagina_tekst = pagina.extract_text()
                if pagina_tekst:
                    tekst_alle_paginas.append(pagina_tekst)

        return "\n\n".join(tekst_alle_paginas)

    except Exception as e:
        raise PDFParseError(f"Kan PDF niet lezen: {e}")


def _clean_numeric_value(value: str, decimal_separator: str = ".") -> float:
    """
    Converteert string naar float, met ondersteuning voor verschillende decimaal scheidingstekens.

    Parameters
    ----------
    value : str
        Numerieke waarde als string (bijv. "36,09" of "36.09").
    decimal_separator : str
        Decimaal scheidingsteken in de input ("," of ".").

    Returns
    -------
    float
        Numerieke waarde.

    Raises
    ------
    ValueError
        Als conversie faalt.

    Voorbeelden
    -----------
    >>> _clean_numeric_value("36,09", ",")
    36.09
    >>> _clean_numeric_value("1.234,56", ",")
    1234.56
    """
    if not value or value.strip() == "":
        raise ValueError("Lege waarde")

    # Verwijder whitespace
    value = value.strip()

    # Als komma decimaal is, vervang deze door punt voor Python
    if decimal_separator == ",":
        # Verwijder duizendtallen punt (bijv. 1.234,56 -> 1234,56)
        value = value.replace(".", "")
        # Vervang komma door punt (1234,56 -> 1234.56)
        value = value.replace(",", ".")
    else:
        # Verwijder duizendtallen komma (bijv. 1,234.56 -> 1234.56)
        value = value.replace(",", "")

    try:
        return float(value)
    except ValueError as e:
        raise ValueError(f"Kan '{value}' niet converteren naar getal: {e}")


def _validate_row_format(row_data: Dict, template: Dict) -> bool:
    """
    Valideert of een geëxtraheerde rij voldoet aan het formaat van de template.

    Parameters
    ----------
    row_data : dict
        Dictionary met geëxtraheerde veldwaarden.
    template : dict
        Template configuratie.

    Returns
    -------
    bool
        True als rij valide is, False anders.
    """
    validatie = template.get('validatie', {})

    # Check artikelcode formaat (indien gespecificeerd)
    artikelcode_formaat = validatie.get('artikelcode_formaat')
    if artikelcode_formaat and 'artikelcode' in row_data:
        if not re.match(artikelcode_formaat, str(row_data['artikelcode'])):
            return False

    # Check verplichte velden
    vereiste_velden = ['artikelnaam', 'aantal', 'prijs_per_stuk']
    for veld in vereiste_velden:
        if veld not in row_data or row_data[veld] is None:
            return False

    return True


# ============================================================================
# UTILITY FUNCTIES
# ============================================================================

def lijst_ondersteunde_leveranciers() -> List[str]:
    """
    Geeft lijst van ondersteunde leveranciers.

    Returns
    -------
    list of str
        Namen van leveranciers met templates.

    Voorbeelden
    -----------
    >>> lijst_ondersteunde_leveranciers()
    ['Office Supplies BV', 'Kantoorartikelen NL', 'TechGear Wholesale']
    """
    return list(config.PDF_LEVERANCIER_TEMPLATES.keys())


def check_pdf_dependencies() -> Dict[str, bool]:
    """
    Check welke PDF libraries beschikbaar zijn.

    Returns
    -------
    dict
        {'pdfplumber': bool, 'tabula': bool}
    """
    return {
        'pdfplumber': PDFPLUMBER_AVAILABLE,
        'tabula': TABULA_AVAILABLE
    }
