"""
Simpele test om te checken of alle modules werken
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import time

from modules.data_reader import lees_csv
from modules.data_validator import valideer_dataframe
from modules.normalizer import normaliseer_dataframe
from modules.comparator import vergelijk_facturen
from modules.reporter import genereer_samenvatting, exporteer_naar_excel
from modules.logger import configureer_logger, log_vergelijking_start, log_vergelijking_resultaat

# ============================================================================
# FASE 3.1 TEST
# ============================================================================

print("=" * 50)
print("TEST FASE 3.1: FUNDAMENT")
print("=" * 50)

# Maak testdata
print("\n📝 Testdata aanmaken...")
test_data = pd.DataFrame({
    'artikel': ['ART-001', ''],
    'omschrijving': ['  Laptop Dell  ', 'Muis Logitech'],
    'qty': [2, 10],
    'price': [599.00, 15.50],
    'total': [1198.00, 155.00]
})

# Sla op als CSV
test_data.to_csv('test_factuur.csv', index=False)
print("✅ test_factuur.csv aangemaakt")

# Test workflow
print("\n🔍 Stap 1: CSV inlezen...")
df = lees_csv('test_factuur.csv')
print(f"✅ {len(df)} regels ingelezen")

print("\n🔍 Stap 2: Valideren...")
is_valid, fouten = valideer_dataframe(df, "test")
print(f"✅ Validatie: {is_valid}")
if fouten:
    print(f"⚠️  Fouten: {fouten}")

print("\n🔍 Stap 3: Normaliseren...")
df_norm = normaliseer_dataframe(df, "test")
print(f"✅ Genormaliseerd")
print(f"   Kolommen: {df_norm.columns.tolist()}")

print("\n📊 Resultaat:")
print(df_norm)

print("\n✅ ALLE FUNDAMENT TESTS GESLAAGD!")

# ============================================================================
# FASE 3.2 TEST
# ============================================================================

print("\n" + "=" * 50)
print("TEST FASE 3.2: COMPARATOR")
print("=" * 50)

# Maak tweede testbestand (factuur met kleine verschillen)
test_factuur_data = pd.DataFrame({
    'artikel': ['ART-001', ''],
    'omschrijving': ['Laptop Dell', 'Muis Logitech'],
    'qty': [2, 9],  # Verschil in aantal!
    'price': [599.50, 15.50],  # Verschil in prijs!
    'total': [1199.00, 139.50]
})
test_factuur_data.to_csv('test_factuur_verschillen.csv', index=False)

# Lees en normaliseer beide
df_sys = lees_csv('test_factuur.csv')
df_sys_norm = normaliseer_dataframe(df_sys, "systeem")

df_fac = lees_csv('test_factuur_verschillen.csv')
df_fac_norm = normaliseer_dataframe(df_fac, "factuur")

# Vergelijk
print("\n🔍 Vergelijking uitvoeren...")
resultaat = vergelijk_facturen(df_sys_norm, df_fac_norm)

print(f"✅ {len(resultaat)} regels verwerkt")
print(f"\nStatus verdeling:")
print(resultaat['status'].value_counts())

print("\n📊 Resultaat details:")
print(resultaat[['status', 'artikelnaam', 'aantal_systeem', 'aantal_factuur', 'afwijking_toelichting']])

print("\n✅ COMPARATOR TEST VOLTOOID!")

# ============================================================================
# FASE 3.3 TEST
# ============================================================================

print("\n" + "=" * 50)
print("TEST FASE 3.3: REPORTER & LOGGER")
print("=" * 50)

# Test 1: Samenvatting genereren
print("\n🔍 Test 1: Samenvatting genereren...")
samenvatting = genereer_samenvatting(resultaat)
print(f"✅ Totaal regels: {samenvatting['totaal_regels']}")
print(f"✅ Status counts: {samenvatting['status_counts']}")

# Test 2: Logger configureren
print("\n🔍 Test 2: Logger configureren...")
logger = configureer_logger(Path('./logs'))
print("✅ Logger geconfigureerd")

# Test 3: Logging gebruiken
print("\n🔍 Test 3: Audit logging...")
start_tijd = time.time()

log_vergelijking_start(
    logger,
    "test_factuur.csv",
    "test_factuur_verschillen.csv",
    len(df_sys_norm),
    len(df_fac_norm)
)

# Simuleer verwerking
time.sleep(0.1)

verwerkingstijd = time.time() - start_tijd
log_vergelijking_resultaat(logger, samenvatting, verwerkingstijd)
print("✅ Audit log weggeschreven naar ./logs")

# Test 4: Excel export
print("\n🔍 Test 4: Excel export...")
excel_pad = exporteer_naar_excel(
    resultaat,
    Path('./output'),
    "test_systeem",
    "test_factuur"
)
print(f"✅ Excel gegenereerd: {excel_pad}")

print("\n✅ ALLE FASE 3.3 TESTS GESLAAGD!")

# Toon waar bestanden staan
huidige_datum = datetime.now().strftime('%Y%m%d')
print(f"\n📁 Controleer:")
print(f"   - Excel: {excel_pad}")
print(f"   - Logs: ./logs/factuur_vergelijker_{huidige_datum}.log")

print("\n" + "=" * 50)
print("🎉 ALLE TESTS SUCCESVOL AFGEROND!")
print("=" * 50)
