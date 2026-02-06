# document_classifier.py
# v1.3: Document rol classificatie (pakbon/factuur/onbekend)

"""
document_classifier.py
=====================

Verantwoordelijkheid:
    Classificeert documenten op basis van rol en inhoud voor multi-document vergelijking.

Classificatie Types:
    1. Documentrol: pakbon / factuur / onbekend
    2. Totaalbedrag aanwezig: ja / nee

Waarom:
    - Multi-document vergelijking (N pakbonnen + M facturen)
    - Contextuele UX (pakbon zonder totaal is normaal, geen fout)
    - Geen angst-woorden ("onvolledig", "risico")

Gebruik:
    >>> result = classificeer_document(Path("pakbon_01.pdf"))
    >>> result.rol
    'pakbon'
    >>> result.heeft_totaalbedrag
    False
    >>> result.bericht_gebruiker
    'Pakbon herkend — totalen volgen via factuur'
"""

from dataclasses import dataclass
from typing import Optional, Literal
from pathlib import Path
import re

# Hergebruik bestaande PDF classificatie
try:
    from modules.pdf_classifier import (
        classificeer_pdf,
        PDFClassificatieResultaat,
    )
    PDF_CLASSIFIER_AVAILABLE = True
except ImportError:
    PDF_CLASSIFIER_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

import pandas as pd


@dataclass
class DocumentClassificatieResultaat:
    """
    Resultaat van document classificatie.

    Attributes
    ----------
    # Van PDF classificatie (indien PDF):
    type : str, optional
        Een van: 'template_herkend', 'text_geen_template', 'geen_artikelregels', 'gescand'
        None voor CSV/Excel.
    leverancier : str, optional
        Naam van herkende leverancier (alleen bij template_herkend).

    # Nieuwe rol-detectie:
    rol : str
        Een van: 'pakbon', 'factuur', 'onbekend'
    heeft_totaalbedrag : bool
        True als document totaalbedrag/BTW-sectie bevat.

    # Metadata:
    bestandstype : str
        'pdf', 'csv', of 'excel'
    tekst_lengte : int
        Aantal karakters tekst in document.
    bericht_gebruiker : str
        Menselijke melding voor in UI (geen angst-woorden).
    """

    # PDF classificatie (optioneel, None voor CSV/Excel)
    type: Optional[Literal['template_herkend', 'text_geen_template', 'geen_artikelregels', 'gescand']]
    leverancier: Optional[str]

    # Documentrol (nieuw in v1.3)
    rol: Literal['pakbon', 'factuur', 'onbekend']
    heeft_totaalbedrag: bool

    # Metadata
    bestandstype: Literal['pdf', 'csv', 'excel']
    tekst_lengte: int
    bericht_gebruiker: str


def classificeer_document(bestand_pad: Path) -> DocumentClassificatieResultaat:
    """
    Classificeert document op basis van type en rol.

    Detecteert:
    - Bestandstype (PDF/CSV/Excel)
    - Documentrol (pakbon/factuur/onbekend) via keyword matching
    - Totaalbedrag aanwezig (ja/nee)

    Parameters
    ----------
    bestand_pad : Path
        Pad naar document (PDF, CSV, of Excel).

    Returns
    -------
    DocumentClassificatieResultaat
        Classificatie met rol, type, en vriendelijke melding.

    Voorbeelden
    -----------
    >>> result = classificeer_document(Path("pakbon_01.pdf"))
    >>> result.rol
    'pakbon'
    >>> result.heeft_totaalbedrag
    False
    >>> result.bericht_gebruiker
    'Pakbon herkend (Bosal) — totalen volgen via factuur'

    >>> result = classificeer_document(Path("verzamelfactuur.pdf"))
    >>> result.rol
    'factuur'
    >>> result.heeft_totaalbedrag
    True
    """

    # Detecteer bestandstype
    extensie = bestand_pad.suffix.lower()

    if extensie == '.pdf':
        return _classificeer_pdf(bestand_pad)
    elif extensie in ['.csv', '.xlsx', '.xls']:
        return _classificeer_csv_excel(bestand_pad, extensie)
    else:
        # Onbekend bestandstype
        return DocumentClassificatieResultaat(
            type=None,
            leverancier=None,
            rol='onbekend',
            heeft_totaalbedrag=False,
            bestandstype='pdf',  # fallback
            tekst_lengte=0,
            bericht_gebruiker=f"Onbekend bestandstype: {extensie}"
        )


def _classificeer_pdf(pdf_pad: Path) -> DocumentClassificatieResultaat:
    """
    Classificeert PDF document.

    Gebruikt bestaande pdf_classifier.py + nieuwe rol-detectie.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF-bestand.

    Returns
    -------
    DocumentClassificatieResultaat
        Classificatie met PDF-specifieke info + rol.
    """

    if not PDF_CLASSIFIER_AVAILABLE:
        return DocumentClassificatieResultaat(
            type=None,
            leverancier=None,
            rol='onbekend',
            heeft_totaalbedrag=False,
            bestandstype='pdf',
            tekst_lengte=0,
            bericht_gebruiker="PDF classificatie niet beschikbaar (pdf_classifier module ontbreekt)"
        )

    # Stap 1: Bestaande PDF classificatie (hergebruik bestaande module)
    try:
        pdf_classificatie = classificeer_pdf(pdf_pad)
    except Exception as e:
        # Fallback als classificatie faalt
        return DocumentClassificatieResultaat(
            type='gescand',
            leverancier=None,
            rol='onbekend',
            heeft_totaalbedrag=False,
            bestandstype='pdf',
            tekst_lengte=0,
            bericht_gebruiker=f"PDF kan niet worden gelezen: {str(e)}"
        )

    # Stap 2: Extract tekst voor rol-detectie
    tekst = _extract_tekst_van_pdf(pdf_pad)

    # Stap 3: Detecteer documentrol (pakbon/factuur/onbekend)
    rol = _detecteer_document_rol(tekst)

    # Stap 4: Check totaalbedrag
    heeft_totaalbedrag = _heeft_totaalbedrag(tekst)

    # Stap 5: Genereer gebruiksvriendelijke melding (geen angst-woorden)
    bericht = _genereer_bericht_pdf(pdf_classificatie, rol, heeft_totaalbedrag)

    return DocumentClassificatieResultaat(
        type=pdf_classificatie.type,
        leverancier=pdf_classificatie.leverancier,
        rol=rol,
        heeft_totaalbedrag=heeft_totaalbedrag,
        bestandstype='pdf',
        tekst_lengte=pdf_classificatie.tekst_lengte,
        bericht_gebruiker=bericht
    )


def _classificeer_csv_excel(bestand_pad: Path, extensie: str) -> DocumentClassificatieResultaat:
    """
    Classificeert CSV of Excel document.

    CSV/Excel hebben geen tekst-inhoud om te scannen, dus we:
    - Checken kolomnamen voor hints (bijv. "pakbonnummer", "factuurnummer")
    - Default: classificeren als 'onbekend' rol

    Parameters
    ----------
    bestand_pad : Path
        Pad naar CSV/Excel bestand.
    extensie : str
        '.csv', '.xlsx', of '.xls'

    Returns
    -------
    DocumentClassificatieResultaat
        Classificatie voor CSV/Excel.
    """

    bestandstype = 'csv' if extensie == '.csv' else 'excel'

    try:
        # Lees alleen de kolomnamen (eerste rij, geen data)
        if extensie == '.csv':
            df = pd.read_csv(bestand_pad, nrows=0)
        else:
            df = pd.read_excel(bestand_pad, nrows=0)

        kolom_namen = ' '.join(df.columns.str.lower())

        # Detecteer rol op basis van kolomnamen
        rol = _detecteer_document_rol(kolom_namen)

        # CSV/Excel hebben meestal al gestructureerde data
        # Totaalbedrag is minder relevant hier (maar checken voor consistentie)
        heeft_totaalbedrag = 'totaal' in kolom_namen or 'bedrag' in kolom_namen

        bericht = _genereer_bericht_csv_excel(bestandstype, rol)

        return DocumentClassificatieResultaat(
            type=None,  # Niet van toepassing op CSV/Excel
            leverancier=None,  # Kan niet worden gedetecteerd zonder template
            rol=rol,
            heeft_totaalbedrag=heeft_totaalbedrag,
            bestandstype=bestandstype,
            tekst_lengte=len(kolom_namen),
            bericht_gebruiker=bericht
        )

    except Exception as e:
        # Fallback bij read error
        return DocumentClassificatieResultaat(
            type=None,
            leverancier=None,
            rol='onbekend',
            heeft_totaalbedrag=False,
            bestandstype=bestandstype,
            tekst_lengte=0,
            bericht_gebruiker=f"{bestandstype.upper()} kan niet worden gelezen: {str(e)}"
        )


# ============================================================================
# HELPER FUNCTIES (v1.3 - rol detectie)
# ============================================================================

def _extract_tekst_van_pdf(pdf_pad: Path) -> str:
    """
    Extraheert tekst van eerste pagina van PDF voor rol-detectie.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF-bestand.

    Returns
    -------
    str
        Tekst van eerste pagina (lowercase), of lege string bij fout.
    """

    if not PDFPLUMBER_AVAILABLE:
        return ""

    try:
        with pdfplumber.open(pdf_pad) as pdf:
            if len(pdf.pages) > 0:
                tekst = pdf.pages[0].extract_text()
                return tekst.lower() if tekst else ""
    except Exception:
        return ""

    return ""


def _detecteer_document_rol(tekst: str) -> Literal['pakbon', 'factuur', 'onbekend']:
    """
    Detecteert documentrol op basis van keywords (heuristiek).

    Regels:
    - pakbon: bevat "pakbon", "geleverd", "leverdatum"
              bevat GEEN "factuur", "verzamelfactuur", "te betalen"
    - factuur: bevat "factuur", "verzamelfactuur", "te betalen", "btw"
    - onbekend: geen duidelijke match

    Parameters
    ----------
    tekst : str
        Ruwe tekst van document (lowercase).

    Returns
    -------
    str
        Een van: 'pakbon', 'factuur', 'onbekend'

    Voorbeelden
    -----------
    >>> _detecteer_document_rol("pakbonnummer 12345 leverdatum 01-03-2025")
    'pakbon'
    >>> _detecteer_document_rol("factuur verzamelfactuur btw te betalen")
    'factuur'
    >>> _detecteer_document_rol("artikel prijs aantal")
    'onbekend'
    """

    tekst_lower = tekst.lower()

    # Check factuur keywords (eerst, want specifiekere match)
    factuur_keywords = [
        'factuur',
        'verzamelfactuur',
        'factuurnummer',
        'te betalen',
        'totaal incl',
        'totaal excl',
        'btw bedrag',
        'btw-bedrag'
    ]

    heeft_factuur_keywords = any(kw in tekst_lower for kw in factuur_keywords)

    if heeft_factuur_keywords:
        return 'factuur'

    # Check pakbon keywords
    pakbon_keywords = [
        'pakbon',
        'pakbonnummer',
        'leverdatum',
        'geleverd',
        'levering',
        'delivery note',
        'packing slip'
    ]

    heeft_pakbon_keywords = any(kw in tekst_lower for kw in pakbon_keywords)

    if heeft_pakbon_keywords:
        return 'pakbon'

    # Geen duidelijke match
    return 'onbekend'


def _heeft_totaalbedrag(tekst: str) -> bool:
    """
    Detecteert of document een totaalbedrag/BTW-sectie bevat.

    Heuristieken:
    - Bevat "totaal excl", "totaal incl", "btw bedrag"
    - OF bevat cijferpatroon na "te betalen"
    - OF bevat BTW percentage (6%, 21%)

    Parameters
    ----------
    tekst : str
        Ruwe tekst van document (lowercase).

    Returns
    -------
    bool
        True als totaalbedrag wordt gedetecteerd.

    Voorbeelden
    -----------
    >>> _heeft_totaalbedrag("totaal excl btw: €150,00")
    True
    >>> _heeft_totaalbedrag("artikel aantal prijs")
    False
    """

    tekst_lower = tekst.lower()

    # Check voor totaal keywords
    totaal_keywords = [
        'totaal excl',
        'totaal incl',
        'subtotaal',
        'btw bedrag',
        'btw-bedrag',
        'te betalen',
        'totaal te betalen',
        'eindbedrag'
    ]

    heeft_totaal = any(kw in tekst_lower for kw in totaal_keywords)

    if heeft_totaal:
        return True

    # Extra check: zoek naar BTW percentage (6%, 9%, 21%)
    # Dit is vaak indicatief voor een factuur met totaalbedrag
    btw_pattern = r'\b(6|9|21)%?\s*(btw|vat)\b'
    heeft_btw_percentage = bool(re.search(btw_pattern, tekst_lower))

    return heeft_btw_percentage


def _genereer_bericht_pdf(
    pdf_classificatie: PDFClassificatieResultaat,
    rol: str,
    heeft_totaalbedrag: bool
) -> str:
    """
    Genereert gebruiksvriendelijke melding voor PDF document.

    Principe: Geen angst-woorden ("onvolledig", "risico"), contextueel per rol.

    Parameters
    ----------
    pdf_classificatie : PDFClassificatieResultaat
        Resultaat van pdf_classifier.py
    rol : str
        Gedetecteerde rol ('pakbon', 'factuur', 'onbekend')
    heeft_totaalbedrag : bool
        Of totaalbedrag aanwezig is

    Returns
    -------
    str
        Gebruiksvriendelijke melding
    """

    # Gescande PDF (van bestaande classifier)
    if pdf_classificatie.type == 'gescand':
        return "Gescande PDF gedetecteerd — vraag een digitale versie aan"

    # Geen artikelregels
    if pdf_classificatie.type == 'geen_artikelregels':
        return "Geen artikeltabel gevonden — controleer of dit de juiste pagina is"

    # Template herkend (beste scenario)
    if pdf_classificatie.type == 'template_herkend':
        leverancier = pdf_classificatie.leverancier

        if rol == 'pakbon':
            if heeft_totaalbedrag:
                return f"Pakbon herkend ({leverancier})"
            else:
                return f"Pakbon herkend ({leverancier}) — totalen volgen via factuur"

        elif rol == 'factuur':
            return f"Factuur herkend ({leverancier})"

        else:
            return f"Document verwerkt ({leverancier})"

    # Text-based PDF zonder template
    if pdf_classificatie.type == 'text_geen_template':
        if rol == 'pakbon':
            return "Pakbon gedetecteerd — exporteer naar CSV voor beste resultaat"
        elif rol == 'factuur':
            return "Factuur gedetecteerd — exporteer naar CSV voor beste resultaat"
        else:
            return "PDF bevat artikelregels — exporteer naar CSV voor beste resultaat"

    # Fallback
    return "Document gedetecteerd"


def _genereer_bericht_csv_excel(bestandstype: str, rol: str) -> str:
    """
    Genereert gebruiksvriendelijke melding voor CSV/Excel.

    Parameters
    ----------
    bestandstype : str
        'csv' of 'excel'
    rol : str
        Gedetecteerde rol

    Returns
    -------
    str
        Gebruiksvriendelijke melding
    """

    type_naam = "CSV" if bestandstype == 'csv' else "Excel"

    if rol == 'pakbon':
        return f"{type_naam} pakbon herkend"
    elif rol == 'factuur':
        return f"{type_naam} factuur herkend"
    else:
        return f"{type_naam} document verwerkt"


# ============================================================================
# UTILITY FUNCTIES
# ============================================================================

def lijst_ondersteunde_documentrollen() -> list:
    """
    Retourneert lijst van ondersteunde documentrollen (voor in UI).

    Returns
    -------
    list
        Lijst van rol-types.
    """
    return ['pakbon', 'factuur', 'onbekend']
