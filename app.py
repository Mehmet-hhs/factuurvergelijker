# app.py
# Fase 3: Streamlit UI
"""
app.py
======

Streamlit gebruikersinterface voor de factuurvergelijker.

Functionaliteit:
    - Upload van twee CSV-bestanden
    - Automatische vergelijking
    - Visuele weergave van resultaten
    - Download van Excel-rapport
    - Duidelijke foutmeldingen

Doelgroep:
    Niet-technische medewerkers (inkoop, finance, administratie).
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
import time
from datetime import datetime

# Import alle backend modules
from modules.data_reader import lees_csv, inspecteer_csv
from modules.data_validator import valideer_dataframe
from modules.normalizer import normaliseer_dataframe
from modules.comparator import vergelijk_facturen
from modules.reporter import genereer_samenvatting, exporteer_naar_excel
from modules.logger import configureer_logger, log_vergelijking_start, log_vergelijking_resultaat
import config


# ============================================================================
# CONFIGURATIE
# ============================================================================

st.set_page_config(
    page_title="Factuurvergelijker",
    page_icon="📊",
    layout="wide"
)

# Initialiseer logger (eenmalig) - FIX VOOR STREAMLIT CLOUD
if 'logger' not in st.session_state:
    log_dir = Path(tempfile.gettempdir()) / 'factuurvergelijker_logs'
    log_dir.mkdir(exist_ok=True)
    st.session_state.logger = configureer_logger(log_dir)


# ============================================================================
# HEADER
# ============================================================================

st.title("📊 Factuurvergelijker")
st.markdown("""
Vergelijk uw systeemexport met de leveranciersfactuur om automatisch afwijkingen te detecteren.

**Hoe werkt het?**
1. Upload uw systeemexport (CSV)
2. Upload de leveranciersfactuur (CSV)
3. Klik op "Vergelijk facturen"
4. Download het Excel-rapport met de resultaten
""")

st.divider()


# ============================================================================
# BESTANDSUPLOAD
# ============================================================================

st.subheader("📤 Stap 1: Upload bestanden")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Systeemexport**")
    bestand_systeem = st.file_uploader(
        "Upload uw systeemexport (CSV)",
        type=['csv'],
        key='systeem',
        help="Het CSV-bestand uit uw eigen systeem"
    )

with col2:
    st.markdown("**Leveranciersfactuur**")
    bestand_factuur = st.file_uploader(
        "Upload de leveranciersfactuur (CSV)",
        type=['csv'],
        key='factuur',
        help="Het CSV-bestand van de leverancier"
    )

st.divider()


# ============================================================================
# VERGELIJKING UITVOEREN
# ============================================================================

st.subheader("⚡ Stap 2: Vergelijk")

# Check of beide bestanden aanwezig zijn
beide_bestanden_aanwezig = bestand_systeem is not None and bestand_factuur is not None

if beide_bestanden_aanwezig:
    st.success("✅ Beide bestanden zijn geüpload en klaar voor vergelijking")
else:
    st.warning("⚠️ Upload eerst beide bestanden voordat u kunt vergelijken")

# Vergelijkingsknop
vergelijk_knop = st.button(
    "🔍 Vergelijk facturen",
    disabled=not beide_bestanden_aanwezig,
    type="primary",
    use_container_width=True
)


# ============================================================================
# VERWERKING
# ============================================================================

if vergelijk_knop:
    
    try:
        # Progress indicator
        with st.spinner('Bestanden worden ingelezen...'):
            start_tijd = time.time()
            
            # Sla uploads tijdelijk op
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_systeem:
                tmp_systeem.write(bestand_systeem.getvalue())
                pad_systeem = Path(tmp_systeem.name)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_factuur:
                tmp_factuur.write(bestand_factuur.getvalue())
                pad_factuur = Path(tmp_factuur.name)
            
            # Lees bestanden
            df_systeem_ruw = lees_csv(pad_systeem)
            df_factuur_ruw = lees_csv(pad_factuur)
        
        # ====================================================================
        # SYSTEEMEXPORT: Valideer VOOR normalisatie
        # (Systeemexport heeft al correcte kolomnamen)
        # ====================================================================
        with st.spinner('Systeemexport wordt gecontroleerd...'):
            is_valid_sys, fouten_sys = valideer_dataframe(df_systeem_ruw, "systeemexport")
            if not is_valid_sys:
                st.error("❌ **Fout in systeemexport:**")
                st.error("Het systeembestand bevat niet alle verplichte kolommen of heeft ongeldige data.")
                for fout in fouten_sys:
                    st.error(f"- {fout}")
                st.info("💡 **Verwachte kolommen:** artikelnaam, aantal, prijs_per_stuk, totaal")
                st.stop()
            
            # Normaliseer systeemexport
            df_systeem_norm = normaliseer_dataframe(df_systeem_ruw, "systeemexport")
        
        # ====================================================================
        # LEVERANCIERSFACTUUR: Normaliseer VOOR validatie
        # (Leverancier gebruikt mogelijk andere kolomnamen zoals "qty", "price")
        # ====================================================================
        with st.spinner('Leveranciersfactuur wordt verwerkt...'):
            # EERST normaliseren (kolommen mappen naar standaard)
            df_factuur_norm = normaliseer_dataframe(df_factuur_ruw, "leveranciersfactuur")
            
            # PAS DAARNA valideren (nu zijn kolommen al correct)
            is_valid_fac, fouten_fac = valideer_dataframe(df_factuur_norm, "leveranciersfactuur")
            if not is_valid_fac:
                st.error("❌ **Fout in leveranciersfactuur:**")
                st.error("De leveranciersfactuur bevat niet alle verplichte gegevens of heeft ongeldige data.")
                for fout in fouten_fac:
                    st.error(f"- {fout}")
                st.info("💡 **Tip:** Controleer of de factuur kolommen bevat voor artikelnaam, aantal, prijs en totaalbedrag.")
                st.stop()
        
        # Log start (nu pas, na succesvolle validatie)
        log_vergelijking_start(
            st.session_state.logger,
            bestand_systeem.name,
            bestand_factuur.name,
            len(df_systeem_norm),
            len(df_factuur_norm)
        )
        
        # Vergelijking
        with st.spinner('Facturen worden vergeleken...'):
            df_resultaat = vergelijk_facturen(df_systeem_norm, df_factuur_norm)
            samenvatting = genereer_samenvatting(df_resultaat)

            # ✨ DEBUG: Controleer aantal rijen
            import sys
            debug_msg = f"🔍 APP.PY: Vergelijking compleet - {len(df_resultaat)} rijen in resultaat\n"
            debug_msg += f"   Shape: {df_resultaat.shape}\n"
            with open('/tmp/excel_debug.log', 'a') as f:
                f.write(debug_msg)
            sys.stdout.write(debug_msg)
            sys.stdout.flush()

        # Excel genereren - FIX VOOR STREAMLIT CLOUD
        with st.spinner('Excel-rapport wordt gegenereerd...'):
            output_dir = Path(tempfile.gettempdir()) / 'factuurvergelijker_output'
            output_dir.mkdir(exist_ok=True)

            # ✨ DEBUG: Bevestig dat volledige DataFrame wordt doorgegeven
            debug_msg = f"📤 APP.PY: Stuur {len(df_resultaat)} rijen naar exporteer_naar_excel()\n"
            with open('/tmp/excel_debug.log', 'a') as f:
                f.write(debug_msg)
            sys.stdout.write(debug_msg)
            sys.stdout.flush()

            excel_pad = exporteer_naar_excel(
                df_resultaat,
                output_dir,
                bestand_systeem.name.replace('.csv', ''),
                bestand_factuur.name.replace('.csv', '')
            )
        
        # Log resultaat
        verwerkingstijd = time.time() - start_tijd
        log_vergelijking_resultaat(
            st.session_state.logger,
            samenvatting,
            verwerkingstijd,
            excel_pad
        )
        
        # Opslaan in session state voor weergave
        st.session_state.resultaat = df_resultaat
        st.session_state.samenvatting = samenvatting
        st.session_state.excel_pad = excel_pad
        st.session_state.verwerkingstijd = verwerkingstijd
        
        st.success(f"✅ **Vergelijking voltooid in {verwerkingstijd:.1f} seconden!**")
        
    except FileNotFoundError as e:
        st.error(f"❌ **Bestand niet gevonden:** {e}")
        
    except ValueError as e:
        st.error(f"❌ **Ongeldige data:** {e}")
        st.info("💡 Controleer of uw CSV-bestanden de juiste kolommen bevatten.")
        
    except Exception as e:
        st.error(f"❌ **Er is een onverwachte fout opgetreden:** {e}")
        st.info("💡 Neem contact op met de systeembeheerder als dit probleem aanhoudt.")


# ============================================================================
# RESULTATEN WEERGEVEN
# ============================================================================

if 'resultaat' in st.session_state:
    
    st.divider()
    st.subheader("📊 Stap 3: Resultaten")
    
    # SAMENVATTING
    st.markdown("### 📈 Samenvatting")
    
    samenvatting = st.session_state.samenvatting
    status_counts = samenvatting['status_counts']
    
    # Metrics in kolommen
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Totaal regels", samenvatting['totaal_regels'])
    
    with col2:
        st.metric(
            "✅ OK",
            status_counts.get(config.STATUS_OK, 0),
            delta=None,
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            "⚠️ Afwijkingen",
            status_counts.get(config.STATUS_AFWIJKING, 0),
            delta=None,
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            "❌ Ontbreekt op factuur",
            status_counts.get(config.STATUS_ONTBREEKT_FACTUUR, 0)
        )
    
    with col5:
        st.metric(
            "❌ Ontbreekt in systeem",
            status_counts.get(config.STATUS_ONTBREEKT_SYSTEEM, 0)
        )
    
    with col6:
        st.metric(
            "⚡ Gedeeltelijk",
            status_counts.get(config.STATUS_GEDEELTELIJK, 0)
        )
    
    # DETAILTABEL (beperkte kolommen)
    st.markdown("### 📋 Details (eerste 100 regels)")
    st.info("💡 **Tip:** Download het Excel-bestand hieronder voor alle details en uitgebreide informatie.")
    
    # Selecteer relevante kolommen
    kolommen_tonen = [
        'status',
        'artikelcode',
        'artikelnaam',
        'aantal_systeem',
        'aantal_factuur',
        'prijs_systeem',
        'prijs_factuur',
        'afwijking_toelichting'
    ]
    
    # Filter kolommen die bestaan
    beschikbare_kolommen = [k for k in kolommen_tonen if k in st.session_state.resultaat.columns]
    
    # Toon tabel (max 100 regels)
    df_tonen = st.session_state.resultaat[beschikbare_kolommen].head(100)
    
    # Kleurcodering via styling
    def kleur_status(val):
        if val == config.STATUS_OK:
            return 'background-color: #c6efce'
        elif val == config.STATUS_AFWIJKING:
            return 'background-color: #ffcc99'
        elif val in [config.STATUS_ONTBREEKT_FACTUUR, config.STATUS_ONTBREEKT_SYSTEEM]:
            return 'background-color: #ffc7ce'
        elif val == config.STATUS_GEDEELTELIJK:
            return 'background-color: #ffeb9c'
        else:
            return 'background-color: #d9d9d9'
    
    df_styled = df_tonen.style.applymap(kleur_status, subset=['status'])
    
    st.dataframe(
        df_styled,
        use_container_width=True,
        height=400
    )
    
    if len(st.session_state.resultaat) > 100:
        st.warning(f"⚠️ Tabel toont eerste 100 van {len(st.session_state.resultaat)} regels. Download Excel voor alle data.")
    
    # DOWNLOAD
    st.divider()
    st.markdown("### 📥 Download rapport")
    
    # Lees Excel bestand
    with open(st.session_state.excel_pad, 'rb') as f:
        excel_data = f.read()
    
    st.download_button(
        label="⬇️ Download Excel-rapport",
        data=excel_data,
        file_name=st.session_state.excel_pad.name,
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        type="primary",
        use_container_width=True
    )
    
    st.success(f"✅ Rapport bevat {samenvatting['totaal_regels']} regels verdeeld over 2 tabbladen (Samenvatting + Details)")


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>Factuurvergelijker v1.0 | Gebouwd met Streamlit</p>
    <p>Alle vergelijkingen worden automatisch gelogd voor audit-doeleinden</p>
</div>
""", unsafe_allow_html=True)