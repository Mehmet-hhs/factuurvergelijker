📋 FASE 2: DATAMODEL & VERGELIJKINGSLOGICA

🎯 Inleiding
Dit document beschrijft exact hoe het vergelijkingssysteem werkt. Na goedkeuring van dit ontwerp kan een junior developer Fase 3 (implementatie) oppakken zonder verdere vragen.

1️⃣ CANONIEK DATAMODEL
1.1 Definitieve kolommen
Na normalisatie hebben beide bestanden (systeemexport én leveranciersfactuur) deze structuur:
KolomnaamDatatypeVerplichtToelichtingartikelcodestrNee*Unieke code (bijv. "ART-001")artikelnaamstrJaOmschrijving productaantalfloatJaAantal stuks/eenhedenprijs_per_stukfloatJaPrijs exclusief BTWtotaalfloatJaaantal × prijs_per_stukbtw_percentagefloatNeePercentage (bijv. 21.0 voor 21%)
* Toelichting verplicht/optioneel:

artikelcode: Niet verplicht omdat sommige leveranciers deze niet meesturen
btw_percentage: Optioneel, niet alle systemen registreren BTW op regelniveau

1.2 Mapping van ruwe data → canoniek model
Voorbeeld systeemexport (al gestandaardiseerd):
artikelcode,artikelnaam,aantal,prijs_per_stuk,totaal,btw_percentage
ART-001,Laptop Dell,2,599.00,1198.00,21.0
→ Directe mapping, geen transformatie nodig
Voorbeeld leveranciersfactuur (variabel):
artikel,omschrijving,qty,price,total
,Laptop Dell,2,599.00,1198.00
Mappingtabel voor normalizer.py:
LeverancierskolomCanonieke kolomTransformatieartikelartikelcodeTrim whitespace, leeg = NoneomschrijvingartikelnaamTrim whitespaceqtyaantalfloat()priceprijs_per_stukfloat(), 2 decimalentotaltotaalfloat(), 2 decimalen(afwezig)btw_percentageNone
Belangrijke regel: Als een kolom niet bestaat in de ruwe data, krijgt deze de waarde None in het canonieke model.

2️⃣ MATCH-STRATEGIE (DETERMINISTISCH)
2.1 Doel
Een regel uit de systeemexport koppelen aan precies één regel uit de leveranciersfactuur.
2.2 Matchingproces (stap-voor-stap)
VOOR ELKE regel in systeemexport:

  STAP 1: Probeer match op artikelcode
    - Als systeemregel.artikelcode ≠ None EN leveranciersregel.artikelcode ≠ None
    - Vergelijk: systeemregel.artikelcode == leveranciersregel.artikelcode
    - Als MATCH → ga naar STAP 4
    
  STAP 2: Fallback op artikelnaam (indien geen match in STAP 1)
    - Normaliseer beide namen:
      * Lowercase
      * Verwijder dubbele spaties
      * Trim begin/einde
    - Vergelijk: genormaliseerde_naam_systeem == genormaliseerde_naam_leverancier
    - Als MATCH → ga naar STAP 4
    
  STAP 3: Geen match gevonden
    - Status = "ONTBREEKT OP FACTUUR"
    - Sla over naar volgende regel
    
  STAP 4: Match gevonden
    - Onthoud deze koppeling
    - Markeer leveranciersregel als "gebruikt"
    - Voer vergelijking uit (zie sectie 3)
2.3 Edge cases
SituatieOplossingMeerdere matches op artikelcode❌ Mag niet voorkomen (artikelcode = uniek). Als dit toch gebeurt: STATUS = "FOUT: DUPLICAAT ARTIKELCODE"Meerdere matches op artikelnaamPak de eerst gevonden match. Log waarschuwing.Leveranciersregel niet gematchtNa afloop: markeer als "ONTBREEKT IN SYSTEEM"Lege artikelcode in beide bestandenGebruik alleen STAP 2 (naam)
2.4 Voorbeeld
Systeemexport:
artikelcode | artikelnaam
ART-001     | Laptop Dell
ART-002     | Muis Logitech
Leveranciersfactuur:
artikelcode | artikelnaam
            | laptop dell        (geen code, naam anders gespeld)
ART-002     | Muis Logitech
Resultaat:

Regel 1: Match via STAP 2 (naam "laptop dell" → genormaliseerd = "laptop dell")
Regel 2: Match via STAP 1 (artikelcode "ART-002")


3️⃣ VERGELIJKINGSREGELS PER VELD
3.1 Algemeen principe

Vergelijk alleen als beide waarden beschikbaar zijn
Als één waarde None is → STATUS = "GEDEELTELIJK" (niet alles vergelijkbaar)

3.2 Per veld
🔹 ARTIKEL (artikelcode + artikelnaam)
AspectWaardeHoe vergelijken?Exact (na normalisatie)Tolerantie?NeeAfwijking?Als genormaliseerde strings verschillenUitleg gebruiker"Het artikelnummer of de omschrijving komt niet overeen"
Voorbeeld:

Systeem: artikelcode="ART-001", artikelnaam="Laptop Dell"
Factuur: artikelcode="ART-001", artikelnaam="Laptop Dell XPS"
Resultaat: AFWIJKING (naam verschilt)


🔹 AANTAL
AspectWaardeHoe vergelijken?Numeriek exactTolerantie?Instelbaar via config.py (standaard: 0)Afwijking?Als abs(systeem - factuur) > tolerantieUitleg gebruiker"Het aantal stuks verschilt: verwacht X, gekregen Y"
Voorbeeld (tolerantie = 0):

Systeem: aantal=10.0
Factuur: aantal=9.0
Resultaat: AFWIJKING

Voorbeeld (tolerantie = 1):

Systeem: aantal=10.0
Factuur: aantal=9.0
Resultaat: OK (verschil 1.0 ≤ tolerantie)


🔹 PRIJS PER STUK
AspectWaardeHoe vergelijken?Numeriek met tolerantieTolerantie?Instelbaar via config.py (standaard: €0.01)Afwijking?Als abs(systeem - factuur) > tolerantieUitleg gebruiker"De prijs per stuk wijkt af: verwacht €X, gekregen €Y (verschil: €Z)"
Voorbeeld:

Systeem: prijs_per_stuk=10.00
Factuur: prijs_per_stuk=10.01
Tolerantie: 0.01
Resultaat: OK (verschil 0.01 ≤ tolerantie)


🔹 TOTAAL
AspectWaardeHoe vergelijken?Numeriek met tolerantieTolerantie?Instelbaar via config.py (standaard: €0.02)Afwijking?Als abs(systeem - factuur) > tolerantieUitleg gebruiker"Het totaalbedrag wijkt af: verwacht €X, gekregen €Y (verschil: €Z)"
Belangrijke opmerking: Afrondingsverschillen kunnen ontstaan. Daarom standaard tolerantie van €0.02.

🔹 BTW-PERCENTAGE
AspectWaardeHoe vergelijken?Numeriek exactTolerantie?NeeAfwijking?Als waardes verschillenUitleg gebruiker"Het BTW-percentage wijkt af: verwacht X%, gekregen Y%"BijzonderheidAls één van beide None → OVERSLAAN (niet in vergelijking betrekken)
Voorbeeld:

Systeem: btw_percentage=21.0
Factuur: btw_percentage=None
Resultaat: Dit veld wordt niet meegenomen in de beoordeling


4️⃣ STATUSDEFINITIES
4.1 Overzicht
StatusBetekenisVoorbeeldToekenningsregel✅ OKAlles komt overeenAlle velden matchen binnen tolerantieALLE vergelijkbare velden zijn gelijk⚠️ AFWIJKINGÉén of meer velden wijken afPrijs verschilt met €0.50MINIMAAL 1 veld wijkt af❌ ONTBREEKT OP FACTUURRegel staat wel in systeem, niet op factuurArtikel besteld maar niet gefactureerdGeen match gevonden in leveranciersdata❌ ONTBREEKT IN SYSTEEMRegel staat wel op factuur, niet in systeemExtra artikel gefactureerdLeveranciersregel niet gematcht⚡ GEDEELTELIJKNiet alle velden vergelijkbaarBTW ontbreekt in één bestandMatch gevonden, maar niet alle velden beschikbaar
4.2 Gedetailleerde toelichting
✅ OK
Voorwaarden (ALLEMAAL waar):

Match gevonden (via artikelcode of naam)
Alle verplichte velden beschikbaar
Alle vergelijkbare velden binnen tolerantie

Voorbeeld:
Systeem:  ART-001 | Laptop | 2 | €500.00 | €1000.00
Factuur:  ART-001 | Laptop | 2 | €500.01 | €1000.02
Tolerantie prijs: €0.01, totaal: €0.02
→ Status: OK

⚠️ AFWIJKING
Voorwaarden:

Match gevonden
Minimaal 1 veld wijkt af buiten tolerantie

Velden met afwijking worden gelogd.
Voorbeeld:
Systeem:  ART-002 | Muis | 10 | €15.00 | €150.00
Factuur:  ART-002 | Muis |  9 | €15.00 | €135.00
→ Status: AFWIJKING
→ Reden: "aantal verschilt (verwacht 10, gekregen 9)"

❌ ONTBREEKT OP FACTUUR
Voorwaarden:

Regel staat in systeemexport
Geen match gevonden in leveranciersfactuur

Uitleg gebruiker: "Dit artikel is besteld maar niet (of anders) gefactureerd."

❌ ONTBREEKT IN SYSTEEM
Voorwaarden:

Regel staat in leveranciersfactuur
Niet gematcht met systeemexport

Uitleg gebruiker: "Dit artikel is gefactureerd maar niet in ons systeem teruggevonden."

⚡ GEDEELTELIJK
Voorwaarden:

Match gevonden
Niet alle verplichte velden beschikbaar voor volledige vergelijking

Voorbeeld:
Systeem:  ART-003 | Toetsenbord | 5 | €30.00 | €150.00 | 21%
Factuur:  ART-003 | Toetsenbord | 5 | €30.00 | €150.00 | None
→ Status: GEDEELTELIJK (BTW niet vergelijkbaar)
→ Andere velden: OK

5️⃣ CONFIGURATIEBESTAND (config.py)
5.1 Doel
Centraal punt voor instellingen die zonder code-aanpassing aangepast kunnen worden door een functioneel beheerder.
5.2 Inhoud
python# config.py

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

# Mogelijke leveranciersvarianten (voor automatische detectie)
LEVERANCIERS_MAPPING = {
    # artikelcode varianten
    "artikel": CANON_ARTIKELCODE,
    "artikelcode": CANON_ARTIKELCODE,
    "code": CANON_ARTIKELCODE,
    "product_code": CANON_ARTIKELCODE,
    
    # artikelnaam varianten
    "omschrijving": CANON_ARTIKELNAAM,
    "artikelnaam": CANON_ARTIKELNAAM,
    "beschrijving": CANON_ARTIKELNAAM,
    "product": CANON_ARTIKELNAAM,
    
    # aantal varianten
    "qty": CANON_AANTAL,
    "aantal": CANON_AANTAL,
    "hoeveelheid": CANON_AANTAL,
    "quantity": CANON_AANTAL,
    
    # prijs varianten
    "price": CANON_PRIJS,
    "prijs": CANON_PRIJS,
    "prijs_per_stuk": CANON_PRIJS,
    "stukprijs": CANON_PRIJS,
    
    # totaal varianten
    "total": CANON_TOTAAL,
    "totaal": CANON_TOTAAL,
    "totaalbedrag": CANON_TOTAAL,
    
    # BTW varianten
    "btw": CANON_BTW,
    "btw_percentage": CANON_BTW,
    "vat": CANON_BTW,
    "tax": CANON_BTW,
}

# =============================================================================
# EXPORT INSTELLINGEN
# =============================================================================

EXCEL_BESTANDSNAAM = "vergelijkingsresultaat.xlsx"
EXCEL_SHEET_NAAM = "Vergelijking"
5.3 Gebruik in code (voorbeeld)
python# In comparator.py

from config import TOLERANTIE_PRIJS, STATUS_AFWIJKING

def vergelijk_prijs(systeem_prijs, factuur_prijs):
    verschil = abs(systeem_prijs - factuur_prijs)
    
    if verschil <= TOLERANTIE_PRIJS:
        return True, None
    else:
        return False, f"Prijs wijkt €{verschil:.2f} af"
```

---

## 6️⃣ OUTPUT & SAMENVATTING

### 6.1 Resultaattabel (rij-per-rij)

**Kolommen in resultaattabel:**

| Kolomnaam | Type | Voorbeeld | Toelichting |
|-----------|------|-----------|-------------|
| `status` | `str` | "AFWIJKING" | Zie sectie 4 |
| `artikelcode` | `str` | "ART-001" | Van systeemexport (of factuur indien alleen daar) |
| `artikelnaam` | `str` | "Laptop Dell" | Van systeemexport (of factuur indien alleen daar) |
| `aantal_systeem` | `float` | 10.0 | Uit systeemexport |
| `aantal_factuur` | `float` | 9.0 | Uit leveranciersfactuur |
| `prijs_systeem` | `float` | 599.00 | Uit systeemexport |
| `prijs_factuur` | `float` | 599.50 | Uit leveranciersfactuur |
| `totaal_systeem` | `float` | 5990.00 | Uit systeemexport |
| `totaal_factuur` | `float` | 5395.50 | Uit leveranciersfactuur |
| `afwijking_toelichting` | `str` | "aantal verschilt (verwacht 10, gekregen 9); prijs wijkt €0.50 af" | Mensleesbare uitleg |

**Voorbeeld rij:**
```
status: AFWIJKING
artikelcode: ART-001
artikelnaam: Laptop Dell
aantal_systeem: 10.0
aantal_factuur: 9.0
prijs_systeem: 599.00
prijs_factuur: 599.50
totaal_systeem: 5990.00
totaal_factuur: 5395.50
afwijking_toelichting: "aantal verschilt (verwacht 10, gekregen 9); prijs wijkt €0.50 af"
```

---

### 6.2 Samenvattingsblok (bovenaan UI)

**Vaste metrics:**
```
┌─────────────────────────────────────┐
│  VERGELIJKINGSRESULTAAT SAMENVATTING │
├─────────────────────────────────────┤
│  Totaal regels verwerkt:     247    │
│  ✅ OK:                      198    │
│  ⚠️  Afwijkingen:             35    │
│  ❌ Ontbreekt op factuur:     10    │
│  ❌ Ontbreekt in systeem:      3    │
│  ⚡ Gedeeltelijk:              1    │
│  ⛔ Fouten:                    0    │
└─────────────────────────────────────┘
```

**Berekening:**
- Totaal = aantal unieke regels (systeem + factuur gecombineerd)
- Per status: tel aantal regels met die status

---

### 6.3 Excel-export

**Vereisten:**

1. **Twee tabbladen:**
   - `"Samenvatting"` → metrics (zie 6.2)
   - `"Details"` → volledige resultaattabel (zie 6.1)

2. **Opmaak:**
   - Header: **vetgedrukt**
   - Status-kolom: kleurcodering
     - ✅ OK → groen
     - ⚠️ AFWIJKING → oranje
     - ❌ ONTBREEKT → rood
     - ⚡ GEDEELTELIJK → geel

3. **Filters:**
   - Automatische filters op headerrij (Excel AutoFilter)

4. **Kolombreedtes:**
   - Automatisch aanpassen aan inhoud

**Bestandsnaam:**
```
vergelijking_[systeemnaam]_vs_[leveranciersnaam]_[timestamp].xlsx
```

**Voorbeeld:**
```
vergelijking_export_2024-01_vs_leverancier_ABC_20240215_143022.xlsx
```

---

## 7️⃣ AUDIT LOGGING (PRIVACY-PROOF)

### 7.1 Wat wordt gelogd?

**✅ WEL:**
- Timestamp
- Bestandsnamen (systeemexport, leveranciersfactuur)
- Aantal regels per bestand
- Aantal matches gevonden
- Aantal per status (OK, AFWIJKING, etc.)
- Gebruikte toleranties
- Verwerkingstijd

**❌ NIET:**
- Bedragen
- Artikelnamen
- Artikelcodes
- Leveranciersnamen (tenzij al in bestandsnaam)

### 7.2 Voorbeeld logbericht
```
[2024-02-15 14:30:22] INFO - Vergelijking gestart
  Systeembestand: export_2024-01.csv (247 regels)
  Leveranciersbestand: factuur_ABC_jan2024.csv (240 regels)
  Toleranties: prijs=€0.01, totaal=€0.02, aantal=0
  
[2024-02-15 14:30:24] INFO - Matching voltooid
  Matches op artikelcode: 198
  Matches op artikelnaam: 37
  Geen match gevonden: 12
  
[2024-02-15 14:30:26] INFO - Vergelijking afgerond
  Resultaat: 198 OK, 35 AFWIJKING, 10 ONTBREEKT FACTUUR, 3 ONTBREEKT SYSTEEM, 1 GEDEELTELIJK
  Verwerkingstijd: 4.2 seconden
  Output: vergelijking_export_2024-01_vs_factuur_ABC_jan2024_20240215_143026.xlsx

8️⃣ SAMENVATTING ONTWERPKEUZES
✅ Wat is vastgelegd?
AspectBeslissingRedenDatamodel6 vaste kolommen, waarvan 4 verplichtDekking 99% van praktijksituaties, eenvoudig uit te leggenMatchingPrimair artikelcode, fallback naamDeterministisch én robuust tegen ontbrekende codesTolerantiesInstelbaar via config.pyFlexibiliteit zonder code-aanpassingStatuslogica6 duidelijke statussenCompleet én begrijpelijk voor niet-techniciOutputExcel met 2 tabbladenStandaard business tool, breed ondersteundPrivacyGeen bedragen/namen in logsGDPR-proof, audit-compliant