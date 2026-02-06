# pdf_classifier.py
# v1.2.2: PDF pre-classificatie voor vriendelijke user experience

"""
pdf_classifier.py
=================

Verantwoordelijkheid:
    Pre-classificatie van PDF's voordat volledige parsing plaatsvindt.

Classificatie Types:
    1. template_herkend: PDF met ondersteund template (Bosal, Fource, InternSysteem)
    2. text_geen_template: Text-based PDF zonder template (vriendelijke melding)
    3. geen_artikelregels: PDF zonder herkenbare artikeltabel (brief, voorpagina)
    4. gescand: Gescande PDF zonder tekst-laag (image-based)

Waarom:
    - Duidelijke feedback zonder technische errors
    - Voorkomt verwarrende foutmeldingen
    - Constructieve suggesties per scenario
"""

from dataclasses import dataclass
from typing import Optional, Literal
import re
from pathlib import Path

# Hergebruik bestaande functie (backward compatible)
from modules.pdf_converter import detecteer_leverancier

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


@dataclass
class PDFClassificatieResultaat:
    """
    Resultaat van PDF classificatie.

    Attributes
    ----------
    type : str
        Een van: 'template_herkend', 'text_geen_template', 'geen_artikelregels', 'gescand'
    leverancier : str, optional
        Naam van herkende leverancier (alleen bij template_herkend).
    tekst_lengte : int
        Aantal karakters tekst in eerste pagina.
    heeft_tabel_structuur : bool
        True als PDF tabel-achtige structuur bevat.
    bericht_gebruiker : str
        Menselijke melding voor in UI.
    """

    type: Literal['template_herkend', 'text_geen_template', 'geen_artikelregels', 'gescand']
    leverancier: Optional[str]
    tekst_lengte: int
    heeft_tabel_structuur: bool
    bericht_gebruiker: str


def classificeer_pdf(pdf_pad: Path) -> PDFClassificatieResultaat:
    """
    Classificeert PDF in 4 categorieën voordat volledige parsing plaatsvindt.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF-bestand.

    Returns
    -------
    PDFClassificatieResultaat
        Classificatie met type, leverancier (indien herkend), en menselijke melding.

    Voorbeelden
    -----------
    >>> result = classificeer_pdf(Path("bosal_factuur.pdf"))
    >>> result.type
    'template_herkend'
    >>> result.leverancier
    'Bosal'

    >>> result = classificeer_pdf(Path("onbekende_leverancier.pdf"))
    >>> result.type
    'text_geen_template'
    """

    # Stap 1: Extract tekst van eerste pagina
    tekst = _extract_eerste_pagina_tekst(pdf_pad)

    # Check 1: Gescande PDF (geen tekst of zeer weinig tekst)
    if not tekst or len(tekst) < 50:
        return PDFClassificatieResultaat(
            type='gescand',
            leverancier=None,
            tekst_lengte=len(tekst) if tekst else 0,
            heeft_tabel_structuur=False,
            bericht_gebruiker="Deze PDF is gescand en bevat geen leesbare tekst."
        )

    # Stap 2: Check template match (hergebruik bestaande detecteer_leverancier)
    try:
        leverancier = detecteer_leverancier(pdf_pad)
    except Exception:
        leverancier = None

    if leverancier is not None:
        # Success case: Template herkend
        return PDFClassificatieResultaat(
            type='template_herkend',
            leverancier=leverancier,
            tekst_lengte=len(tekst),
            heeft_tabel_structuur=True,
            bericht_gebruiker=f"Leverancier herkend: {leverancier}"
        )

    # Stap 3: Check of PDF tabel-structuur heeft (maar geen template)
    heeft_tabel = _heeft_tabel_structuur(tekst)

    if heeft_tabel:
        return PDFClassificatieResultaat(
            type='text_geen_template',
            leverancier=None,
            tekst_lengte=len(tekst),
            heeft_tabel_structuur=True,
            bericht_gebruiker="PDF bevat artikelregels, maar leverancier heeft geen ondersteund template."
        )

    # Stap 4: Geen herkenbare artikeltabel
    return PDFClassificatieResultaat(
        type='geen_artikelregels',
        leverancier=None,
        tekst_lengte=len(tekst),
        heeft_tabel_structuur=False,
        bericht_gebruiker="PDF bevat geen herkenbare artikeltabel."
    )


def _extract_eerste_pagina_tekst(pdf_pad: Path) -> str:
    """
    Extraheert tekst van eerste pagina van PDF.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF-bestand.

    Returns
    -------
    str
        Tekst van eerste pagina, of lege string bij fout.
    """
    if not PDFPLUMBER_AVAILABLE:
        return ""

    try:
        with pdfplumber.open(pdf_pad) as pdf:
            if len(pdf.pages) > 0:
                tekst = pdf.pages[0].extract_text()
                return tekst if tekst else ""
    except Exception:
        return ""

    return ""


def _heeft_tabel_structuur(tekst: str) -> bool:
    """
    Detecteert of tekst tabel-achtige structuur heeft (heuristiek).

    Gebruikt 2 checks:
    1. Minimaal 3 regels met cijferpatroon (bijv. "10  Widget  5.50  55.00")
    2. Bevat tabel-keywords ("artikel", "aantal", "prijs", "totaal")

    Parameters
    ----------
    tekst : str
        Ruwe tekst van PDF.

    Returns
    -------
    bool
        True als tabel-structuur wordt gedetecteerd.
    """

    # Heuristiek 1: Detecteer regels met cijferpatronen
    # Patroon: cijfer(s), gevolgd door tekst, gevolgd door decimaal getal
    # Voorbeelden:
    #   "10  Widget Pro  5.50"
    #   "5   Artikel naam  12,99"
    cijfer_regels = re.findall(r'\d+.*\d+[,\.]\d{2}', tekst)

    if len(cijfer_regels) < 3:
        # Te weinig regels met cijferpatroon
        return False

    # Heuristiek 2: Check voor tabel-gerelateerde keywords
    keywords = ['artikel', 'aantal', 'prijs', 'totaal', 'bedrag', 'omschrijving', 'product']
    tekst_lower = tekst.lower()

    heeft_keywords = any(kw in tekst_lower for kw in keywords)

    # Beide checks moeten slagen
    return len(cijfer_regels) >= 3 and heeft_keywords


def lijst_ondersteunde_leveranciers() -> list:
    """
    Retourneert lijst van ondersteunde leveranciers (voor in UI).

    Returns
    -------
    list
        Lijst van leveranciersnamen.
    """
    return [
        "Bosal Distribution",
        "Fource / LKQ Netherlands B.V.",
        "Kilinclar (intern systeem)"
    ]
