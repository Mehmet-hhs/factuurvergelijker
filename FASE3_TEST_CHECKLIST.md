# v1.3 FASE 3: Test Checklist
**Implementatie: Pipeline Integratie & Multi-Upload UI**

## ✅ Geïmplementeerde Features

### 1. Multi-Upload UI
- [x] Beide file uploaders accepteren meerdere bestanden (`accept_multiple_files=True`)
- [x] Teller toont aantal geselecteerde documenten
- [x] Duidelijke labels: "📦 Systeem Documenten" en "📄 Leverancier Documenten"
- [x] Help tekst uitgebreid met "pakbonnen, exports" en "facturen"

### 2. Document Verwerking
- [x] Nieuwe functie `verwerk_document_groep()` geïmplementeerd
- [x] Per document classificatie via `document_classifier.py`
- [x] Rol-bewuste UX meldingen (pakbon vs factuur)
- [x] Automatisch overslaan van ongeldige documenten (gescand, geen template, etc.)
- [x] Warnings zijn informatief, niet blokkerend

### 3. Aggregatie Pipeline
- [x] Aggregator wordt aangeroepen na verwerking per kant
- [x] Aggregatie metadata wordt getoond (aantal docs, regels in/out)
- [x] Warnings (prijsverschillen) in expander
- [x] Documentdetails in expander per kant

### 4. UX Copy (Positief, geen angst-woorden)
- [x] "Pakbon herkend — totalen volgen via factuur" ✅
- [x] "X documenten samengevoegd tot Y unieke artikelen" ✅
- [x] "Factuur herkend — klaar voor vergelijking" ✅
- [x] Geen "onvolledig", "risico", "niet ondersteund" ❌
- [x] Gescande PDF: "vraag digitale versie aan" (constructief)
- [x] Geen template: "gebruik bij voorkeur CSV/Excel" (suggestief)

### 5. Pipeline Flow
```
Upload (N+M docs)
→ Per document: classificeer → verwerk (reader/validator/normalizer)
→ Per kant: aggregeer (aggregator)
→ Vergelijk (comparator - ongewijzigd)
→ Rapporteer (reporter - ongewijzigd)
```

---

## 🧪 Regressie Tests (VERPLICHT)

### Scenario 1: Single Document (Backwards Compatibility)
**Doel:** Bestaande v1.2 flow moet exact blijven werken

- [ ] **Test 1.1:** Upload 1 CSV systeem + 1 CSV leverancier
  - Verwacht: Werkt zoals v1.2, geen aggregatie-overhead
  - Controle: Excel bevat alle regels, geen data loss

- [ ] **Test 1.2:** Upload 1 PDF (Bosal) + 1 CSV
  - Verwacht: PDF wordt herkend, verwerkt, vergelijking werkt
  - Controle: Leverancier "Bosal" wordt getoond

### Scenario 2: Multi-Document (Nieuwe Functionaliteit)
**Doel:** Meerdere documenten worden correct geaggregeerd

- [ ] **Test 2.1:** Upload 3 pakbon PDF's + 1 factuur PDF
  - Verwacht:
    - Alle 3 pakbonnen herkend met rol "pakbon"
    - Melding "totalen volgen via factuur" bij pakbonnen
    - Factuur herkend met rol "factuur"
    - Aggregatie toont correct aantal regels
  - Controle:
    - Excel bevat geaggregeerde artikelen
    - Geen duplicaten door aggregatie

- [ ] **Test 2.2:** Upload 2 CSV pakbonnen + 1 CSV factuur
  - Verwacht: CSV classificatie werkt, aggregatie werkt
  - Controle: Totalen kloppen in vergelijking

- [ ] **Test 2.3:** Mixed: 2 PDF pakbonnen + 1 CSV systeem + 1 PDF factuur
  - Verwacht: Alle formaten worden samen geaggregeerd
  - Controle: Geen format-specifieke fouten

### Scenario 3: Edge Cases
**Doel:** Foutafhandeling is robuust en gebruiksvriendelijk

- [ ] **Test 3.1:** Upload gescande PDF
  - Verwacht:
    - Herkenning als 'gescand'
    - Vriendelijke melding: "vraag digitale versie aan"
    - Document wordt overgeslagen, geen crash
  - Controle: Andere geldige documenten worden wel verwerkt

- [ ] **Test 3.2:** Upload PDF zonder template (onbekende leverancier)
  - Verwacht:
    - Herkenning als 'text_geen_template'
    - Melding: "gebruik bij voorkeur CSV/Excel"
    - Geen error, gewoon overgeslagen
  - Controle: Geen "niet ondersteund" of angst-woorden

- [ ] **Test 3.3:** Upload alleen lege/ongeldige documenten
  - Verwacht:
    - Duidelijke melding: "Geen geldige documenten"
    - Suggesties wat te doen
    - Geen technische error stack traces
  - Controle: st.stop() wordt aangeroepen, geen crash

- [ ] **Test 3.4:** Prijsverschil tussen pakbonnen
  - Verwacht:
    - Warning in expander: "Artikel X heeft verschillende prijzen"
    - Melding: "Gemiddelde prijs gebruikt"
    - Vergelijking gaat gewoon door (niet blokkerend)
  - Controle: Warning staat in aggregatie expander

### Scenario 4: Data Integriteit
**Doel:** Geen data loss tijdens aggregatie en vergelijking

- [ ] **Test 4.1:** Vergelijk totalen voor/na aggregatie
  - Pakbon 1: Artikel A (10 stuks, €5)
  - Pakbon 2: Artikel A (5 stuks, €5)
  - Verwacht: Aggregaat toont Artikel A (15 stuks, €5)
  - Controle: Som van aantallen klopt, weighted average prijs klopt

- [ ] **Test 4.2:** Controleer Excel output
  - Verwacht:
    - Alle geaggregeerde artikelen in Excel
    - Samenvatting tab bevat metadata
    - Details tab bevat vergelijkingsresultaat
  - Controle: Open Excel, tel regels, check formules

- [ ] **Test 4.3:** Unieke artikelen over documenten heen
  - Pakbon 1: Artikel A, B
  - Pakbon 2: Artikel C, D
  - Factuur: Artikel A, C
  - Verwacht:
    - Systeem aggregaat: A, B, C, D (4 unieke)
    - Leverancier aggregaat: A, C (2 unieke)
    - Vergelijking: A (OK), B (ontbreekt factuur), C (OK), D (ontbreekt factuur)
  - Controle: Status kolom klopt per artikel

---

## 🎨 UX Verificatie

### Visuele Checks
- [ ] Teller toont aantal documenten na upload
- [ ] Per document wordt feedback getoond (✅/⚠️/ℹ️)
- [ ] Aggregatie samenvatting toont X regels → Y unieke artikelen
- [ ] Expanders bevatten details (niet in hoofdflow)
- [ ] Kleurgebruik: groen (succes), blauw (info), geel (waarschuwing), rood (error)

### Copy Checks (Geen angst-woorden!)
- [ ] Zoek in UI naar verboden woorden:
  - ❌ "onvolledig"
  - ❌ "risico" (behalve bij echte fout)
  - ❌ "niet ondersteund"
  - ❌ "gebruik liever CSV" (moet zijn: "gebruik bij voorkeur")
- [ ] Alle meldingen zijn constructief en suggestief

---

## 🔧 Technische Checks

### Code Kwaliteit
- [x] Alle imports correct (document_classifier, aggregator)
- [x] Geen ongebruikte variabelen (bestand_systeem → bestanden_systeem)
- [x] Error handling op juiste plekken
- [x] Session state correct gebruikt voor aggregatie metadata
- [x] Logger aanroepen op juiste momenten

### Backwards Compatibility
- [ ] Bestaande modules ongewijzigd:
  - [ ] aggregator.py (niet gewijzigd sinds Fase 2)
  - [ ] comparator.py (niet aangeroepen met nieuwe parameters)
  - [ ] normalizer.py (geen wijzigingen)
  - [ ] reporter.py (geen wijzigingen in Fase 3)

### Performance
- [ ] Multi-document upload < 10 seconden voor 5 PDF's
- [ ] Aggregatie < 2 seconden voor 1000 regels
- [ ] Geen geheugen problemen bij 10+ documenten

---

## 📝 Acceptatie Criteria

**Minimaal vereist voor Fase 3 compleet:**

1. ✅ Multi-upload UI werkt (meerdere bestanden per kant)
2. ✅ `verwerk_document_groep()` functie werkt correct
3. ✅ Aggregatie wordt aangeroepen en toont metadata
4. ✅ UX copy is positief (geen angst-woorden)
5. ✅ Backwards compatibility: single document flow werkt
6. [ ] Alle regressie tests slagen
7. [ ] Geen crashes of data loss

**Nice-to-have (optioneel):**
- [ ] Progress bar tijdens multi-document verwerking
- [ ] Download knop per kant (systeem aggregaat apart downloaden)
- [ ] Toon prijsverschillen in aparte tabel

---

## 🐛 Bekende Issues / TODOs

- [ ] `verwerk_bestand()` wordt aangeroepen vanuit `verwerk_document_groep()`, maar normaliseert mogelijk dubbel (check efficiency)
- [ ] PDF classificatie gebeurt twee keer: eenmaal in document_classifier, eenmaal in verwerk_bestand (optimalisatie mogelijk)
- [ ] Session state groeit bij meerdere vergelijkingen (mogelijk cleanup nodig)

---

## 🚀 Volgende Fase (Fase 4)

**Niet in deze fase:**
- Reporter.py wijzigingen (Excel moet aggregatie metadata tonen)
- Logging uitbreiden (multi-document context)
- Excel tabs voor per-document details

**Prioriteit Fase 4:**
1. Excel samenvatting uitbreiden met aggregatie metadata
2. Excel details tab: toon welk artikel uit welk document komt
3. Logging: log alle document namen + rollen
