# 📊 Excel Rapport Lezen - Handleiding voor Eindgebruikers
**Factuurvergelijker v1.3 - Fase 4a**

---

## 🎯 Voor Wie Is Deze Handleiding?

Deze handleiding is bedoeld voor **niet-technische medewerkers** (finance, inkoop, administratie) die Excel rapporten van de Factuurvergelijker moeten lezen en interpreteren.

**Geen technische kennis vereist!** Deze handleiding legt in gewone mensentaal uit wat elk onderdeel betekent en welke acties je moet ondernemen.

---

## 📁 Het Excel Rapport

### Wat Bevat Het Rapport?

Het Excel-bestand bevat **2 tabbladen**:

1. **Samenvatting** - Overzicht van alle documenten en vergelijkingsresultaat
2. **Details** - Alle artikelen met status per regel (OK, Afwijking, etc.)

**In deze handleiding bespreken we vooral de Samenvatting-tab**, want daar zie je in één oogopslag of alles klopt.

---

## 🔍 De Samenvatting-Tab - Stap voor Stap

### Sectie 1: 📦 SYSTEEM DOCUMENTEN

**Wat staat hier?**
```
📦 SYSTEEM DOCUMENTEN

Verwerkt:           3 document(en)
Totaal regels:      43 → 38 unieke artikelen

Documenten:
  • pakbon_01.pdf
  • pakbon_02.pdf
  • pakbon_03.pdf
```

#### Wat Betekent Dit?

| Veld | Betekenis | Hoe Check Je Dit? |
|------|-----------|-------------------|
| **Verwerkt: 3 document(en)** | Het systeem heeft 3 pakbonnen/exports succesvol verwerkt | ✅ Klopt dit aantal met wat je hebt geüpload? |
| **43 → 38 unieke artikelen** | Van 43 regels zijn 38 unieke artikelen overgebleven | ✅ Reductie van 5 is normaal: artikel X stond in meerdere pakbonnen |
| **Documenten lijst** | Welke bestanden zijn gebruikt | ✅ Herken je deze bestandsnamen? |

#### ✅ Groene Vinkjes (Alles OK)
- Aantal documenten klopt met wat je hebt geüpload
- Reductie is klein (< 20%): artikelen komen weinig dubbel voor
- Je herkent alle bestandsnamen

#### ⚠️ Waarschuwingen (Controleren)
- **Te veel reductie (> 30%)**: "43 → 10" betekent 33 artikelen zijn weg. Waarom?
  - **Mogelijke oorzaak:** Veel artikelen hebben aantal=0 (niet geleverd) en zijn gefilterd
  - **Actie:** Check de Streamlit UI tijdens verwerking voor warnings

- **Te weinig documenten**: "1 document(en)" terwijl je 3 pakbonnen hebt geüpload
  - **Mogelijke oorzaak:** 2 documenten waren gescand (geen tekst) of leeg
  - **Actie:** Check Streamlit UI feedback, vraag digitale versies aan

#### ❌ Rode Flags (Direct Actie Vereist)
- **0 documenten verwerkt**: Alle documenten waren ongeldig
  - **Actie:** Gebruik CSV/Excel i.p.v. gescande PDF's
  - **Contact:** IT indien probleem aanhoudt

---

### Sectie 2: 📄 LEVERANCIER DOCUMENTEN

**Identiek aan Sectie 1, maar dan voor leveranciersfacturen.**

**Voorbeeld:**
```
📄 LEVERANCIER DOCUMENTEN

Verwerkt:           1 document(en)
Totaal regels:      35 → 35 unieke artikelen

Documenten:
  • verzamelfactuur_januari.pdf
```

#### Wat Check Je?
- ✅ Aantal facturen klopt (meestal 1 verzamelfactuur)
- ✅ Aantal regels logisch (35 artikelen op factuur)
- ✅ Bestandsnaam herkenbaar

---

### Sectie 3: ⚠️ AGGREGATIE MELDINGEN

**Wat staat hier?**

Deze sectie verschijnt **alleen als er meldingen zijn** uit het samenvoegen van documenten.

**Belangrijkste punt:** Gele achtergrond = **informatief, NIET blokkerend**. De vergelijking is gewoon doorgegaan.

#### Voorbeeld 1: Prijsverschillen
```
⚠️ AGGREGATIE MELDINGEN

  • Artikel A123 heeft verschillende prijzen (€15,00 en €15,50).
    Gemiddelde prijs is gebruikt.
```

**Wat betekent dit?**
- Artikel A123 stond in pakbon_01.pdf met prijs €15,00
- En in pakbon_02.pdf met prijs €15,50
- Het systeem heeft het gemiddelde genomen: €15,25

**Wat moet je doen?**
1. ✅ **Check of dit verwacht is**: Is er een prijswijziging geweest tussen leverdatum pakbon 1 en 2?
2. ✅ **Acceptabel?**: Verschil van €0,50 is meestal geen probleem voor vergelijking
3. ⚠️ **Groot verschil?**: Bij prijsverschil > 10% → check met leverancier

#### Voorbeeld 2: Lege Documenten
```
⚠️ AGGREGATIE MELDINGEN

  • 1 document(en) waren leeg en zijn overgeslagen.
```

**Wat betekent dit?**
- Eén van de geüploade documenten bevatte geen artikelregels
- Het systeem heeft dit document overgeslagen

**Wat moet je doen?**
1. Check in de documentlijst (Sectie 1 of 2) welk document het was
2. Controleer of dit document daadwerkelijk artikelen moet bevatten
3. Indien wel: vraag correcte versie aan

#### Geen Meldingen?
**Perfect!** Als deze sectie er niet is, betekent dit dat:
- ✅ Alle artikelen hebben consistente prijzen
- ✅ Alle documenten bevatten geldige data
- ✅ Geen problemen tijdens samenvoegen

---

### Sectie 4: 🔍 VERGELIJKINGSRESULTAAT

**Wat staat hier?**
```
🔍 VERGELIJKINGSRESULTAAT

Totaal regels vergeleken: 38

Status                          | Aantal
✅ OK                           | 30
⚠️ Afwijking                    | 5
❌ Alleen in systeem            | 2
❌ Alleen in leverancier factuur| 1
```

#### Statussen Uitgelegd

| Status | Kleur | Betekenis | Actie |
|--------|-------|-----------|-------|
| **✅ OK** | Groen | Artikel klopt: zelfde aantal, prijs en totaalbedrag | ✅ Geen actie |
| **⚠️ Afwijking** | Oranje | Artikel nummer klopt, maar aantal/prijs verschilt | ⚠️ Check Details-tab |
| **❌ Alleen in systeem** | Rood | Wij hebben dit artikel geleverd gekregen, maar het staat niet op de factuur | ⚠️ Mogelijk nog niet gefactureerd (normaal) |
| **❌ Alleen in leverancier factuur** | Rood | Leverancier factureert een artikel dat wij niet hebben ontvangen | 🚨 **DIRECT CHECKEN!** |
| **⚡ Gedeeltelijk** | Geel | Artikel is gedeeltelijk geleverd (aantal systeem < aantal factuur) | ℹ️ Controleer |

#### Hoe Beoordeel Je Het Resultaat?

##### ✅ GOED (Geen Actie Nodig)
```
✅ OK: 95%
⚠️ Afwijking: 3%
❌ Alleen in systeem: 2%
```

**Interpretatie:**
- 95% van artikelen klopt → uitstekend
- 3% afwijkingen → acceptabel (kleine verschillen)
- 2% alleen in systeem → waarschijnlijk nog niet gefactureerd (normaal bij pakbonnen vs factuur)

**Actie:** Geen, alles is in orde.

##### ⚠️ CONTROLEREN (Check Details)
```
✅ OK: 70%
⚠️ Afwijking: 20%
❌ Alleen in systeem: 10%
```

**Interpretatie:**
- 20% afwijkingen → relatief veel verschillen
- 10% alleen in systeem → veel artikelen nog niet gefactureerd?

**Actie:**
1. Open Details-tab
2. Filter op "Afwijking" en "Alleen in systeem"
3. Check welke artikelen het zijn
4. Bespreek met leverancier indien nodig

##### 🚨 ALARM (Direct Actie)
```
✅ OK: 80%
❌ Alleen in leverancier factuur: 5 artikelen
```

**Interpretatie:**
- We betalen voor 5 artikelen die we niet hebben ontvangen!

**Actie:**
1. **Direct:** Open Details-tab, filter op "Alleen in leverancier factuur"
2. **Check:** Zijn dit artikelen die in een andere levering zitten? (ander pakbonnummer)
3. **Contact:** Neem contact op met leverancier voor correctie factuur

---

## 📋 De Details-Tab - Hoe Gebruik Je Deze?

### Wanneer Gebruik Je De Details-Tab?

**Gebruik de Details-tab wanneer:**
1. Status "Afwijking" of "Alleen in..." > 5% is
2. Je wilt weten **welke** artikelen het precies zijn
3. Je specifieke artikelnummers wilt opzoeken

### Hoe Gebruik Je Filters?

**Stap 1:** Klik op Details-tab

**Stap 2:** Klik op filter icoon (▼) in header "Status"

**Stap 3:** Selecteer alleen "⚠️ Afwijking" of "❌ Alleen in..."

**Resultaat:** Je ziet nu alleen de problematische artikelen

### Wat Zie Je In De Details-Tab?

| Kolom | Betekenis |
|-------|-----------|
| **artikel_nummer** | Artikelnummer/code |
| **omschrijving** | Omschrijving van artikel |
| **aantal_systeem** | Aantal volgens onze systeem/pakbonnen |
| **aantal_factuur** | Aantal volgens leveranciersfactuur |
| **prijs_systeem** | Prijs volgens onze systeem |
| **prijs_factuur** | Prijs volgens leverancier |
| **totaal_systeem** | Totaalbedrag systeem (aantal × prijs) |
| **totaal_factuur** | Totaalbedrag factuur |
| **status** | Status (OK / Afwijking / etc.) |

---

## 🧠 Veelgestelde Vragen

### Q1: Waarom Zijn Er Minder Artikelen Dan Regels?

**Antwoord:** Het systeem voegt duplicaten samen.

**Voorbeeld:**
- Pakbon 1: Artikel A123 (10 stuks)
- Pakbon 2: Artikel A123 (5 stuks)
- **Resultaat:** Artikel A123 (15 stuks) → 1 uniek artikel

Dit is **normaal en correct**. Je wilt uiteindelijk weten: "Hoeveel van artikel A123 heb ik in totaal ontvangen?"

---

### Q2: Wat Als Prijzen Verschillen Tussen Pakbonnen?

**Antwoord:** Het systeem gebruikt het **gemiddelde** en toont een melding.

**Voorbeeld:**
- Pakbon 1: Artikel B456 (prijs €10,00)
- Pakbon 2: Artikel B456 (prijs €12,00)
- **Resultaat:** Gemiddelde prijs €11,00 wordt gebruikt

**Is dit een probleem?**
- ✅ **Klein verschil (< €1)**: Meestal geen probleem (afrondingen, tijdelijke acties)
- ⚠️ **Groot verschil (> 10%)**: Check met leverancier of er prijswijziging is geweest

---

### Q3: Wat Is "Alleen In Systeem" en Is Dat Erg?

**Antwoord:** Artikel staat in onze pakbonnen maar niet op de factuur.

**Is dit erg?**
- ✅ **Bij pakbonnen vs verzamelfactuur**: Vaak normaal
  - **Reden:** Leverancier factureert wekelijks/maandelijks, pakbon is dagelijks
  - **Artikel kan nog gefactureerd worden** in volgende verzamelfactuur

- ⚠️ **Bij definitieve factuur**: Controleren
  - **Reden:** Artikel is mogelijk vergeten op factuur
  - **Actie:** Check met leverancier

**Hoe weet je het verschil?**
- Check de bestandsnaam in "Leverancier Documenten"
- "verzamelfactuur" of "maandfactuur" → waarschijnlijk normaal
- "definitieve_factuur" of "eindfactuur" → mogelijk probleem

---

### Q4: Wat Is "Alleen In Leverancier Factuur" en Is Dat Erg?

**Antwoord:** Artikel staat op factuur maar niet in onze pakbonnen/systeem.

**Is dit erg?**
- 🚨 **Ja, altijd checken!**
  - **Mogelijkheid 1:** We betalen voor iets dat we niet hebben ontvangen
  - **Mogelijkheid 2:** Artikel zit in een andere levering (ander pakbonnummer) die niet is geüpload

**Wat moet je doen?**
1. Check Details-tab: welke artikelen zijn dit?
2. Zoek in je administratie: is dit artikel inderdaad geleverd (andere pakbon)?
3. Indien niet geleverd: contact met leverancier voor creditnota

---

### Q5: Hoeveel "OK" Is Goed Genoeg?

**Antwoord:** Hangt af van je proces.

| OK Percentage | Beoordeling | Actie |
|---------------|-------------|-------|
| **> 95%** | ✅ Uitstekend | Geen actie, alles prima |
| **80-95%** | ✅ Goed | Normale variatie, check grote afwijkingen |
| **60-80%** | ⚠️ Matig | Check wat de oorzaak is (veel afwijkingen?) |
| **< 60%** | ❌ Slecht | Structureel probleem, check met leverancier |

**Let op:** "Alleen in systeem" is vaak acceptabel (zie Q3), maar "Alleen in leverancier factuur" is altijd een rode vlag.

---

## ✅ Checklist: Wanneer Is Het Rapport Betrouwbaar?

### Voor Je Het Rapport Opent

- [ ] Heb ik alle relevante documenten geüpload? (alle pakbonnen + factuur)
- [ ] Waren de documenten digitaal (niet gescand)?
- [ ] Heb ik de Streamlit feedback gecheckt tijdens verwerking?

### Bij Het Lezen Van De Samenvatting

**Sectie 1 & 2: Documenten**
- [ ] Aantal verwerkte documenten klopt
- [ ] Alle bestandsnamen zijn herkenbaar
- [ ] Reductie (regels → unieke artikelen) is logisch (< 30%)

**Sectie 3: Meldingen**
- [ ] Geen meldingen, of
- [ ] Meldingen zijn verklaarbaar (prijswijziging, verwachte duplicaten)

**Sectie 4: Resultaat**
- [ ] Status "OK" > 80%
- [ ] Status "Alleen in leverancier factuur" = 0 (of verklaard via andere levering)
- [ ] Grote afwijkingen zijn gecheckt in Details-tab

### Als Alle Vinkjes Groen Zijn

✅ **Het rapport is betrouwbaar en je kunt de factuur goedkeuren!**

---

## 🆘 Hulp Nodig?

### Stap 1: Check Deze Handleiding
- Zoek je vraag in de FAQ (Q1-Q5)
- Gebruik de checklists

### Stap 2: Check Streamlit UI Feedback
- Tijdens het verwerken toont Streamlit per document feedback
- Stonden daar warnings? Welke?

### Stap 3: Contact IT
**Wanneer?**
- Rapport bevat technische errors
- Alle documenten worden afgekeurd (0 verwerkt)
- Excel rapport opent niet correct

**Geef door:**
- Screenshot van het probleem
- Welke bestanden je hebt geüpload
- Streamlit feedback (indien beschikbaar)

---

## 📚 Begrippenlijst

| Term | Betekenis |
|------|-----------|
| **Aggregatie** | Het samenvoegen van meerdere documenten tot één overzicht |
| **Unieke artikelen** | Artikelen zonder duplicaten (artikel A123 telt 1x, ook al staat het in 3 pakbonnen) |
| **Reductie** | Verschil tussen aantal regels en unieke artikelen (43 → 38 = 5 duplicaten) |
| **Verzamelfactuur** | Factuur die meerdere leveringen bevat (bijv. alle leveringen van januari) |
| **Pakbon** | Leveringsbewijs dat bij de levering meegaat |
| **Gescande PDF** | PDF gemaakt door papier te scannen (geen doorzoekbare tekst) |
| **Digitale PDF** | PDF gegenereerd door systeem (wel doorzoekbare tekst) |

---

## 📊 Voorbeeld Scenario - Volledige Walkthrough

### Situatie
Je hebt deze documenten geüpload:
- 3 pakbonnen (pakbon_01.pdf, pakbon_02.pdf, pakbon_03.pdf)
- 1 verzamelfactuur (verzamelfactuur_jan2025.pdf)

### Excel Rapport: Samenvatting Tab

```
📦 SYSTEEM DOCUMENTEN
Verwerkt: 3 document(en)
Totaal regels: 87 → 82 unieke artikelen

Documenten:
  • pakbon_01.pdf
  • pakbon_02.pdf
  • pakbon_03.pdf

📄 LEVERANCIER DOCUMENTEN
Verwerkt: 1 document(en)
Totaal regels: 78 → 78 unieke artikelen

Documenten:
  • verzamelfactuur_jan2025.pdf

⚠️ AGGREGATIE MELDINGEN
  • Artikel A123 heeft verschillende prijzen (€15,00 en €15,50). Gemiddelde prijs is gebruikt.

🔍 VERGELIJKINGSRESULTAAT
Totaal regels vergeleken: 82

Status                          | Aantal
✅ OK                           | 75
⚠️ Afwijking                    | 3
❌ Alleen in systeem            | 4
❌ Alleen in leverancier factuur| 0
```

### Analyse

#### Stap 1: Check Documenten Sectie
- ✅ **Systeem:** 3 pakbonnen verwerkt → klopt
- ✅ **Reductie:** 87 → 82 (5 duplicaten) → acceptabel (6% reductie)
- ✅ **Leverancier:** 1 factuur verwerkt → klopt
- ✅ **Leverancier reductie:** 78 → 78 (geen duplicaten) → logisch (verzamelfactuur heeft al unieke artikelen)

#### Stap 2: Check Meldingen
- ⚠️ **Prijsverschil artikel A123:** €15,00 vs €15,50
  - **Check:** Was er een prijswijziging tussen levering 1 en 2?
  - **Actie:** Acceptabel, verschil van €0,50 is minimaal
  - **Gemiddelde €15,25 gebruikt** → correct

#### Stap 3: Check Resultaat
- ✅ **75 van 82 OK (91%)** → uitstekend!
- ⚠️ **3 afwijkingen (4%)** → klein percentage, check Details-tab
- ⚠️ **4 alleen in systeem (5%)** → logisch bij verzamelfactuur (mogelijk andere periode)
- ✅ **0 alleen in leverancier factuur** → perfect, we betalen niet voor onbekende artikelen

#### Stap 4: Conclusie
**Rapport is betrouwbaar, factuur kan worden goedgekeurd!**

**Optionele actie:** Check Details-tab voor de 3 afwijkingen (welke artikelen zijn dit? Grote verschillen?).

---

**Veel succes met het lezen van de rapporten!** 📊✅
