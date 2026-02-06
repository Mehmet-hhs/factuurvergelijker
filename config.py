"""
config.py
=========

Centrale configuratie voor de factuurvergelijker.

Dit bestand bevat alle instellingen die zonder code-aanpassing aangepast
kunnen worden door functioneel beheerders.

Secties:
--------
1. TOLERANTIES
   Numerieke afwijkingen die acceptabel zijn bij vergelijkingen.
   Gebruikt voor: prijs, aantal, totaalbedrag, BTW-percentage.

2. VELDCONFIGURATIE
   Welke velden verplicht zijn in beide bestanden voor een volledige vergelijking.
   Optionele velden worden genegeerd als ze ontbreken.

3. STATUSLABELS
   Uniforme labels voor alle mogelijke uitkomsten van een vergelijking.
   Gebruikt door comparator.py en reporter.py.

4. KOLOMNAMEN
   Definieert de canonieke (interne) kolomnamen en de mapping van
   veelvoorkomende leveranciersvarianten naar deze standaard.

5. EXPORT INSTELLINGEN
   Standaard bestandsnamen en sheet-namen voor Excel-export.
"""

# =============================================================================
# TOLERANTIES (voor numerieke vergelijkingen)
# =============================================================================

TOLERANTIE_AANTAL = 0.0          # Geen tolerantie: aantallen moeten exact kloppen
TOLERANTIE_PRIJS = 0.01          # €0.01 verschil toegestaan (afrondingsverschillen)
TOLERANTIE_TOTAAL = 0.02         # €0.02 verschil toegestaan (cumulatieve afrondingen)
TOLERANTIE_BTW = 0.0             # BTW-percentage moet exact

# =============================================================================
# VELDCONFIGURATIE (verplicht vs optioneel)
# =============================================================================

VERPLICHTE_VELDEN = [
    "artikelnaam",
    "aantal",
    "prijs_per_stuk",
    "totaal"
]

OPTIONELE_VELDEN = [
    "artikelcode",
    "btw_percentage"
]

# =============================================================================
# STATUSLABELS (voor consistentie in hele systeem)
# =============================================================================

STATUS_OK = "OK"
STATUS_AFWIJKING = "AFWIJKING"
STATUS_ONTBREEKT_FACTUUR = "ONTBREEKT OP FACTUUR"
STATUS_ONTBREEKT_SYSTEEM = "ONTBREEKT IN SYSTEEM"
STATUS_GEDEELTELIJK = "GEDEELTELIJK"
STATUS_FOUT = "FOUT"                # Voor technische fouten (bijv. duplicaten)

# =============================================================================
# KOLOMNAMEN (voor mapping)
# =============================================================================

# Canonieke kolomnamen (intern gebruikt)
CANON_ARTIKELCODE = "artikelcode"
CANON_ARTIKELNAAM = "artikelnaam"
CANON_AANTAL = "aantal"
CANON_PRIJS = "prijs_per_stuk"
CANON_TOTAAL = "totaal"
CANON_BTW = "btw_percentage"

# Alle canonieke kolommen in een lijst (voor validatie)
CANONIEKE_KOLOMMEN = [
    CANON_ARTIKELCODE,
    CANON_ARTIKELNAAM,
    CANON_AANTAL,
    CANON_PRIJS,
    CANON_TOTAAL,
    CANON_BTW
]

# Mogelijke leveranciersvarianten (voor automatische detectie)
# Key = wat er in het CSV-bestand staat (lowercase)
# Value = canonieke kolomnaam
LEVERANCIERS_MAPPING = {
    # artikelcode varianten
    "artikel": CANON_ARTIKELCODE,
    "artikelcode": CANON_ARTIKELCODE,
    "code": CANON_ARTIKELCODE,
    "product_code": CANON_ARTIKELCODE,
    "productcode": CANON_ARTIKELCODE,
    
    # artikelnaam varianten
    "omschrijving": CANON_ARTIKELNAAM,
    "artikelnaam": CANON_ARTIKELNAAM,
    "beschrijving": CANON_ARTIKELNAAM,
    "product": CANON_ARTIKELNAAM,
    "naam": CANON_ARTIKELNAAM,
    "description": CANON_ARTIKELNAAM,
    
    # aantal varianten
    "qty": CANON_AANTAL,
    "aantal": CANON_AANTAL,
    "hoeveelheid": CANON_AANTAL,
    "quantity": CANON_AANTAL,
    "aant": CANON_AANTAL,
    
    # prijs varianten
    "price": CANON_PRIJS,
    "prijs": CANON_PRIJS,
    "prijs_per_stuk": CANON_PRIJS,
    "stukprijs": CANON_PRIJS,
    "eenheidsprijs": CANON_PRIJS,
    "unit_price": CANON_PRIJS,
    
    # totaal varianten
    "total": CANON_TOTAAL,
    "totaal": CANON_TOTAAL,
    "totaalbedrag": CANON_TOTAAL,
    "bedrag": CANON_TOTAAL,
    "amount": CANON_TOTAAL,
    
    # BTW varianten
    "btw": CANON_BTW,
    "btw_percentage": CANON_BTW,
    "btwpercentage": CANON_BTW,
    "vat": CANON_BTW,
    "tax": CANON_BTW,
    "btw%": CANON_BTW,
}

# =============================================================================
# EXPORT INSTELLINGEN
# =============================================================================

EXCEL_BESTANDSNAAM = "vergelijkingsresultaat.xlsx"
EXCEL_SHEET_NAAM = "Vergelijking"
EXCEL_SHEET_SAMENVATTING = "Samenvatting"

# =============================================================================
# PDF LEVERANCIER TEMPLATES (v1.2)
# =============================================================================

PDF_LEVERANCIER_TEMPLATES = {
    "Bosal": {
        "naam": "Bosal Distribution",
        "identifier_regex": r"BOSAL DISTRIBUTION|www\.bosal\.com",
        "parser_type": "custom_text",
        "parser_config": {
            "strategy": "single_line_pattern",
            "header_pattern": r"Artikel\s+Artikelomschrijving\s+Geleverd",
            "stop_pattern": r"Commodity Code|Totaal voor Pakbonnummer",
            # Pattern groups: (artikelcode) (omschrijving) (aantal) (prijs) (totaal)
            "line_pattern": r"^([\d-]+\s+\(\d+\))\s+(.*?)\s+(\d+)\s+\w+\s+\d+\s+([\d,]+)\s+([\d,]+)$",
            "decimal_separator": ",",  # NL locale: 36,09
        },
        "kolom_mapping": {
            0: "artikelcode",      # Group 1
            1: "artikelnaam",      # Group 2
            2: "aantal",           # Group 3
            3: "prijs_per_stuk",   # Group 4
            4: "totaal",           # Group 5
        },
        "validatie": {
            "min_regels": 5,
            "vereist_totaalbedrag": True,
            "artikelcode_formaat": r"^\d+-\d+\s+\(\d+\)$"
        }
    },

    "Fource": {
        "naam": "LKQ Netherlands B.V. / Fource",
        "identifier_regex": r"LKQ Netherlands B\.V\.|info@fource\.nl|www\.lkqeurope\.nl",
        "parser_type": "custom_text",
        "parser_config": {
            "strategy": "two_line_pattern",
            "header_pattern": r"Rgl\s+Order\s+Artikelnummer",
            "stop_pattern": None,  # Parse tot einde
            # Pattern groups: (rgl_nr) (order_nr) (artikelnummer) (bruto) (netto) (prijs) (aantal) (bedrag)
            # Omschrijving staat op volgende regel
            "line_pattern": r"^(\d+)\s+([\d-]+)\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s+%?\s*([\d.]+)\s+(\d+)\s+([\d.]+)",
            "decimal_separator": ".",
            "description_follows": True,  # Omschrijving op rij+1
        },
        "kolom_mapping": {
            2: "artikelcode",      # Group 3 (artikelnummer)
            5: "prijs_per_stuk",   # Group 6 (prijs na korting)
            6: "aantal",           # Group 7
            7: "totaal",           # Group 8 (bedrag)
            # artikelnaam komt van volgende regel
        },
        "validatie": {
            "min_regels": 10,
            "vereist_totaalbedrag": True,
            "artikelcode_formaat": r"^\S+"
        }
    },

    "InternSysteem": {
        "naam": "Kilinclar Automaterialen (Intern Systeem)",
        "identifier_regex": r"info@kilinclar\.nl|RETOUR FACTUUR|NL92 ABNA 0510 2163 82",
        "parser_type": "custom_text",
        "parser_config": {
            "strategy": "single_line_pattern",
            "header_pattern": r"Artikelnummer\s+Omschrijving\s+Aantal\s+Stuksprijs\s+Bedrag",
            "stop_pattern": r"Subtotaal|Totaal Excl\.|BTW",
            # Pattern: parse van rechts naar links (cijfers zijn betrouwbaarder)
            # (artikelnummer) (omschrijving) (aantal) (stuksprijs) (bedrag)
            # Artikelnummer en omschrijving kunnen spaties bevatten
            "line_pattern": r"^(.+?)\s+(.+?)\s+(\d+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$",
            "decimal_separator": ",",  # NL format: 14,35
        },
        "kolom_mapping": {
            0: "artikelcode",      # Group 1
            1: "artikelnaam",      # Group 2
            2: "aantal",           # Group 3
            3: "prijs_per_stuk",   # Group 4
            4: "totaal",           # Group 5
        },
        "validatie": {
            "min_regels": 5,
            "vereist_totaalbedrag": True,
            "artikelcode_formaat": r"^.+"  # Flexibel (spaties toegestaan)
        }
    }
}