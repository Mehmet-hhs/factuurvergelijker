# Factuurvergelijker

## Status: Fase 2 voltooid ✅

### Projectoverzicht
Dit systeem vergelijkt systeemexporten met leveranciersfacturen op basis van deterministische regels.

### Architectuur
- 4-lagen architectuur (Presentatie, Verwerking, Data, Output)
- Volledig rule-based, geen ML
- Deterministisch en audit-proof

### Voltooide fases
- [x] Fase 1: Architectuur & Ontwerp
- [x] Fase 2: Datamodel & Vergelijkingslogica
- [ ] Fase 3: Implementatie (volgt na goedkeuring)

### Documentatie
Zie `/docs` map voor gedetailleerde specificaties.

### Installatie (later, na Fase 3)
```bash
pip install -r requirements.txt
streamlit run app.py
```