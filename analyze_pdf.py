#!/usr/bin/env python3
"""
analyze_pdf.py
==============

Script om PDF-bestanden te analyseren voor template-ontwerp.

Gebruik:
    python analyze_pdf.py pad/naar/bestand.pdf

Output:
    - Basis informatie (aantal pagina's, tekst-extractie mogelijk?)
    - Tabel detectie (locaties, kolommen)
    - Voorbeeld data (eerste 5 regels)
    - Voorstel voor template-configuratie
"""

import sys
from pathlib import Path
import json

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("⚠️ pdfplumber niet geïnstalleerd. Installeer met: pip install pdfplumber")

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    print("⚠️ tabula-py niet geïnstalleerd. Installeer met: pip install tabula-py")


def analyseer_pdf(pdf_pad: Path):
    """
    Analyseer PDF en genereer rapport.

    Parameters
    ----------
    pdf_pad : Path
        Pad naar PDF-bestand.
    """

    print(f"\n{'='*60}")
    print(f"📄 ANALYSE: {pdf_pad.name}")
    print(f"{'='*60}\n")

    if not pdf_pad.exists():
        print(f"❌ Bestand niet gevonden: {pdf_pad}")
        return

    # SECTIE 1: BASIS INFO
    print("1️⃣ BASIS INFORMATIE")
    print("-" * 40)

    if not PDFPLUMBER_AVAILABLE:
        print("❌ Kan PDF niet analyseren (pdfplumber ontbreekt)")
        return

    try:
        with pdfplumber.open(pdf_pad) as pdf:
            aantal_paginas = len(pdf.pages)
            print(f"   Aantal pagina's: {aantal_paginas}")

            # Lees eerste pagina
            eerste_pagina = pdf.pages[0]
            tekst = eerste_pagina.extract_text()

            if tekst:
                print(f"   ✅ Text-based PDF (tekst extracteerbaar)")
                print(f"   Tekst lengte: {len(tekst)} karakters")
            else:
                print(f"   ❌ GEEN tekst geëxtraheerd (mogelijk gescanned)")
                print(f"   🛑 NO-GO: Scans worden niet ondersteund")
                return

            # Toon eerste 200 karakters (voor identifier detectie)
            print(f"\n   📝 Eerste 200 karakters:")
            print(f"   {repr(tekst[:200])}")

    except Exception as e:
        print(f"❌ Fout bij openen PDF: {e}")
        return

    # SECTIE 2: TABEL DETECTIE (pdfplumber)
    print(f"\n\n2️⃣ TABEL DETECTIE (pdfplumber)")
    print("-" * 40)

    try:
        with pdfplumber.open(pdf_pad) as pdf:
            for pagina_nr, pagina in enumerate(pdf.pages[:3], 1):  # Max 3 pagina's
                print(f"\n   📄 Pagina {pagina_nr}:")

                # Detecteer tabellen
                tabellen = pagina.extract_tables()
                print(f"   Aantal tabellen gevonden: {len(tabellen)}")

                if tabellen:
                    for tabel_nr, tabel in enumerate(tabellen, 1):
                        print(f"\n   📊 Tabel {tabel_nr}:")
                        print(f"      Rijen: {len(tabel)}")
                        print(f"      Kolommen: {len(tabel[0]) if tabel else 0}")

                        # Toon headers
                        if len(tabel) > 0:
                            print(f"      Headers: {tabel[0]}")

                        # Toon eerste 3 data rijen
                        if len(tabel) > 1:
                            print(f"\n      Voorbeeld data (eerste 3 rijen):")
                            for rij in tabel[1:4]:
                                print(f"      {rij}")
                else:
                    print(f"   ⚠️ Geen tabellen gedetecteerd op pagina {pagina_nr}")

    except Exception as e:
        print(f"   ❌ Fout bij tabel detectie: {e}")

    # SECTIE 3: TABEL DETECTIE (tabula - alternatief)
    if TABULA_AVAILABLE:
        print(f"\n\n3️⃣ TABEL DETECTIE (tabula - alternatief)")
        print("-" * 40)

        try:
            tabellen_tabula = tabula.read_pdf(
                str(pdf_pad),
                pages='1',
                multiple_tables=True
            )

            print(f"   Aantal tabellen gevonden: {len(tabellen_tabula)}")

            for tabel_nr, df in enumerate(tabellen_tabula, 1):
                print(f"\n   📊 Tabel {tabel_nr}:")
                print(f"      Shape: {df.shape}")
                print(f"      Kolommen: {list(df.columns)}")
                print(f"\n      Eerste 3 rijen:")
                print(df.head(3).to_string(index=False))

        except Exception as e:
            print(f"   ❌ Tabula fout: {e}")

    # SECTIE 4: VOORSTEL TEMPLATE
    print(f"\n\n4️⃣ VOORSTEL TEMPLATE-CONFIGURATIE")
    print("-" * 40)

    # Genereer basis template
    try:
        with pdfplumber.open(pdf_pad) as pdf:
            eerste_pagina = pdf.pages[0]
            tekst = eerste_pagina.extract_text()
            tabellen = eerste_pagina.extract_tables()

            if tabellen:
                eerste_tabel = tabellen[0]

                template = {
                    "identifier_regex": "TODO: zoek unieke string in PDF",
                    "parser_type": "pdfplumber",  # of "tabula"
                    "aantal_paginas": len(pdf.pages),
                    "kolom_mapping": {},
                    "validatie": {
                        "min_regels": max(1, len(eerste_tabel) - 1),
                        "vereist_totaalbedrag": True
                    }
                }

                # Probeer kolommen te mappen
                if len(eerste_tabel) > 0:
                    headers = eerste_tabel[0]
                    for idx, header in enumerate(headers):
                        if header:
                            header_lower = str(header).lower().strip()

                            # Heuristiek voor mapping
                            if any(x in header_lower for x in ['code', 'artikel', 'sku']):
                                template["kolom_mapping"][idx] = "artikelcode"
                            elif any(x in header_lower for x in ['naam', 'omschrijving', 'description', 'product']):
                                template["kolom_mapping"][idx] = "artikelnaam"
                            elif any(x in header_lower for x in ['aantal', 'qty', 'quantity', 'hoeveelheid']):
                                template["kolom_mapping"][idx] = "aantal"
                            elif any(x in header_lower for x in ['prijs', 'price', 'stukprijs', 'unit']):
                                template["kolom_mapping"][idx] = "prijs_per_stuk"
                            elif any(x in header_lower for x in ['totaal', 'total', 'bedrag', 'amount']):
                                template["kolom_mapping"][idx] = "totaal"

                print(f"\n   Voorgestelde configuratie (DRAFT):")
                print(f"   {json.dumps(template, indent=4)}")

                print(f"\n   ⚠️ LET OP:")
                print(f"   - identifier_regex moet handmatig ingevuld")
                print(f"   - Kolom-mapping controleren en aanpassen")
                print(f"   - Testen met meerdere PDF's van deze leverancier")
            else:
                print(f"   ⚠️ Geen tabel gevonden, kan geen template genereren")

    except Exception as e:
        print(f"   ❌ Fout bij template generatie: {e}")

    # SECTIE 5: GO/NO-GO ADVIES
    print(f"\n\n5️⃣ GO/NO-GO BESLISSING")
    print("-" * 40)

    try:
        with pdfplumber.open(pdf_pad) as pdf:
            eerste_pagina = pdf.pages[0]
            tekst = eerste_pagina.extract_text()
            tabellen = eerste_pagina.extract_tables()

            score = 0
            redenen = []

            # Check 1: Text-based
            if tekst:
                score += 3
                redenen.append("✅ Text-based PDF")
            else:
                redenen.append("❌ Geen tekst (scan)")

            # Check 2: Tabellen detecteerbaar
            if tabellen and len(tabellen) > 0:
                score += 3
                redenen.append(f"✅ Tabel gevonden ({len(tabellen[0])} rijen)")
            else:
                redenen.append("❌ Geen tabel gedetecteerd")

            # Check 3: Kolommen logisch
            if tabellen and len(tabellen[0]) > 0 and len(tabellen[0][0]) >= 3:
                score += 2
                redenen.append(f"✅ Voldoende kolommen ({len(tabellen[0][0])})")
            else:
                redenen.append("⚠️ Te weinig kolommen")

            # Check 4: Data rijen aanwezig
            if tabellen and len(tabellen[0]) > 1:
                score += 2
                redenen.append(f"✅ Data rijen aanwezig ({len(tabellen[0]) - 1})")
            else:
                redenen.append("❌ Geen data rijen")

            # Beslissing
            print(f"   Score: {score}/10")
            print(f"\n   Redenen:")
            for reden in redenen:
                print(f"   {reden}")

            print(f"\n   📊 CONCLUSIE:")
            if score >= 8:
                print(f"   ✅ GO - Hoge confidence, template is haalbaar")
            elif score >= 5:
                print(f"   ⚠️ GO MET RISICO - Middel confidence, handmatige checks nodig")
            else:
                print(f"   ❌ NO-GO - Te laag confidence, niet geschikt voor template")

    except Exception as e:
        print(f"   ❌ Fout bij go/no-go analyse: {e}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Gebruik: python analyze_pdf.py pad/naar/bestand.pdf")
        sys.exit(1)

    pdf_pad = Path(sys.argv[1])
    analyseer_pdf(pdf_pad)
