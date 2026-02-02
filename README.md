# 📊 Factuurvergelijker

Automatische vergelijking van systeemexporten met leveranciersfacturen voor detectie van afwijkingen.

## 🚀 Live App

**[Gebruik de app hier](https://jouw-streamlit-url.streamlit.app)**

## ✨ Features

- ✅ Automatische kolomherkenning (werkt met verschillende leveranciersformaten)
- ✅ Deterministisch matching (artikelcode → naam fallback)
- ✅ Excel export met kleurcodering
- ✅ Privacy-proof audit logging
- ✅ Duidelijke foutmeldingen in Nederlands
- ✅ Geen installatie nodig - werkt direct in browser

## 📖 Documentatie

Zie [GEBRUIKERSHANDLEIDING.md](GEBRUIKERSHANDLEIDING.md) voor uitgebreide instructies.

## 🏗️ Technische Details

### Architectuur
- **Frontend:** Streamlit
- **Backend:** Python 3.9
- **Data processing:** Pandas
- **Export:** OpenPyXL

### Project Structuur
```
factuurvergelijker/
├── app.py                 # Streamlit UI
├── config.py              # Configuratie (toleranties, statussen)
├── modules/
│   ├── data_reader.py     # CSV inlezen
│   ├── data_validator.py  # Data validatie
│   ├── normalizer.py      # Kolom normalisatie
│   ├── comparator.py      # Vergelijkingslogica
│   ├── reporter.py        # Excel rapportage
│   └── logger.py          # Audit logging
└── requirements.txt       # Dependencies
```

## 🔒 Privacy & Compliance

- Geen permanente opslag van geüploade bestanden
- Audit logs bevatten geen bedragen of artikelgegevens
- HTTPS encrypted verbinding
- GDPR-compliant

## 👥 Voor Ontwikkelaars

### Lokaal draaien
```bash
git clone https://github.com/Mehmet-hhs/factuurvergelijker.git
cd factuurvergelijker
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### Tests draaien
```bash
python test_fundament.py
```

## 📝 Changelog

### v1.0 (2 februari 2026)
- Initial release
- Volledige vergelijkingslogica
- Excel export met kleurcodering
- Streamlit Cloud deployment

## 📧 Contact

Voor vragen of suggesties:
- Email: [jouw email]
- GitHub Issues: [link naar issues]

## 📄 Licentie

[Kies een licentie of laat weg]

---

Gebouwd met ❤️ voor [Bedrijfsnaam]
```

---

### **5️⃣ Test de volledige flow nogmaals**

**Finale check:**

1. ✅ Ga naar je Streamlit URL
2. ✅ Upload twee CSV's
3. ✅ Klik "Vergelijk"
4. ✅ Check of resultaten kloppen
5. ✅ Download Excel
6. ✅ Open Excel en controleer beide tabbladen
7. ✅ Test met verschillende browsers (Chrome, Firefox, Safari)

---

## 🎯 **GO/NO-GO CHECKLIST**

| Check | Status |
|-------|--------|
| App is live op Streamlit Cloud | ✅ |
| Getest met echte bedrijfsdata | ⬜ |
| Tempfile fix geïmplementeerd | ⬜ |
| Gebruikershandleiding gemaakt | ⬜ |
| README.md up-to-date | ⬜ |
| Excel download werkt | ⬜ |
| Alle errors zijn gebruiksvriendelijk | ⬜ |
| Getest in verschillende browsers | ⬜ |

---

## ✅ **ALS ALLES GECHECKT IS:**

### **Je kunt het delen met deze email:**
```
Onderwerp: Nieuwe tool: Automatische Factuurvergelijker

Beste [Manager],

Ik heb een automatische factuurvergelijker gebouwd die jullie kunnen 
gebruiken om systeemexporten te vergelijken met leveranciersfacturen.

🔗 Link: https://jouw-app-url.streamlit.app

Voordelen:
✅ Geen installatie nodig - werkt direct in de browser
✅ Automatische detectie van afwijkingen
✅ Excel-rapport met kleurcodering
✅ Privacy-compliant (geen permanente data opslag)

Hoe te gebruiken:
1. Upload systeemexport (CSV)
2. Upload leveranciersfactuur (CSV)
3. Klik op "Vergelijk facturen"
4. Download Excel-rapport

Voor uitgebreide instructies, zie de gebruikershandleiding op GitHub:
https://github.com/Mehmet-hhs/factuurvergelijker

Bij vragen kun je mij altijd bereiken.

Met vriendelijke groet,
[Jouw naam]