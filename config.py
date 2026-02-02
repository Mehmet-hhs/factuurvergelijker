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