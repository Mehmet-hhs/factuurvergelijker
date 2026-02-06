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
from modules.logger import configureer_logger, log_vergelijking_start, log_vergelijking_resultaat, log_pdf_conversie
from modules.formatter import formatteer_aantal, formatteer_prijs
from modules.pdf_converter import (
    detecteer_leverancier,
    converteer_pdf_naar_df,
    LeverancierOnbekendError,
    PDFParseError,
    PDFValidatieError
)
from modules.pdf_classifier import classificeer_pdf
from modules.document_classifier import classificeer_document
from modules.aggregator import aggregeer_documenten, AggregatieResultaat
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
# HELPER FUNCTIES
# ============================================================================

def verwerk_bestand(uploaded_file, bestandstype_label: str):
    """
    Verwerkt een geüpload bestand (CSV, Excel, of PDF).

    Parameters
    ----------
    uploaded_file : UploadedFile
        Streamlit uploaded file object.
    bestandstype_label : str
        Label voor logging ("systeemexport" of "leveranciersfactuur").

    Returns
    -------
    pd.DataFrame
        Verwerkte DataFrame.

    Raises
    ------
    Exception
        Bij fouten tijdens verwerking (met duidelijke gebruikersmelding).
    """
    bestandsnaam = uploaded_file.name
    bestandsextensie = Path(bestandsnaam).suffix.lower()

    # Sla bestand tijdelijk op
    with tempfile.NamedTemporaryFile(delete=False, suffix=bestandsextensie) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_pad = Path(tmp.name)

    try:
        # Detecteer bestandstype
        if bestandsextensie == '.pdf':
            # ✨ v1.2.2: PDF pre-classificatie voor vriendelijke UX
            st.info(f"📄 PDF gedetecteerd: {bestandsnaam}")

            # Pre-classificatie (voordat volledige parsing plaatsvindt)
            with st.spinner('PDF wordt geanalyseerd...'):
                classificatie = classificeer_pdf(tmp_pad)

            # 4-way branching op basis van classificatie type
            if classificatie.type == 'gescand':
                # Scenario 1: Gescande PDF (image-based, geen tekst)
                st.warning("⚠️ **Gescande PDF gedetecteerd**")
                st.info("""
                Deze PDF is gescand als afbeelding en bevat geen doorzoekbare tekst.
                Automatische verwerking is niet mogelijk.

                💡 **Wat kunt u doen?**
                • Vraag uw leverancier om een digitale (niet-gescande) factuur
                • Gebruik een CSV of Excel export in plaats van PDF
                • Als dit een eenmalige factuur is, kunt u handmatig vergelijken
                """)
                log_pdf_conversie(
                    st.session_state.logger,
                    bestandsnaam,
                    None,
                    0,
                    False,
                    "Gescande PDF"
                )
                st.stop()

            elif classificatie.type == 'text_geen_template':
                # Scenario 2: Text-based maar geen ondersteund template
                st.info("ℹ️ **PDF bevat artikelregels, maar geen ondersteund formaat**")
                st.info("""
                Deze PDF heeft wel leesbare tekst en artikelregels, maar het formaat
                komt niet overeen met onze ondersteunde leveranciers.

                💡 **Alternatief:**
                • Exporteer de factuur naar CSV of Excel vanuit uw leverancierssysteem
                • Stuur ons deze PDF zodat we het formaat kunnen toevoegen

                📋 **Ondersteunde PDF-leveranciers:**
                • Bosal Distribution
                • Fource / LKQ Netherlands B.V.
                • Kilinclar (intern systeem)
                """)
                log_pdf_conversie(
                    st.session_state.logger,
                    bestandsnaam,
                    None,
                    0,
                    False,
                    "Geen template"
                )
                st.stop()

            elif classificatie.type == 'geen_artikelregels':
                # Scenario 3: PDF zonder artikeltabel
                st.error("❌ **Geen artikeltabel gevonden**")
                st.info("""
                Deze PDF lijkt geen artikelregels te bevatten. Het kan gaan om een
                voorpagina, begeleidende brief, of samenvattingspagina.

                💡 **Controleer:**
                • Is dit de juiste pagina van de factuur?
                • Bevat de PDF wel een gedetailleerde artikellijst?
                • Misschien heeft u een samenvattingspagina geüpload?

                Als de PDF wel artikelen bevat, neem dan contact op met support.
                """)
                log_pdf_conversie(
                    st.session_state.logger,
                    bestandsnaam,
                    None,
                    0,
                    False,
                    "Geen artikelen"
                )
                st.stop()

            elif classificatie.type == 'template_herkend':
                # Scenario 4: Success - Template herkend, parse PDF
                leverancier = classificatie.leverancier
                st.success(f"✅ Leverancier herkend: **{leverancier}**")

                # Converteer PDF naar DataFrame
                with st.spinner(f'PDF wordt verwerkt ({leverancier})...'):
                    df = converteer_pdf_naar_df(tmp_pad, leverancier)

                    st.success(f"✅ PDF verwerkt: **{len(df)} regels** geëxtraheerd")

                    # Log succes
                    log_pdf_conversie(
                        st.session_state.logger,
                        bestandsnaam,
                        leverancier,
                        len(df),
                        True
                    )

                    return df

        elif bestandsextensie in ['.csv', '.xlsx', '.xls']:
            # CSV/Excel verwerking (bestaande functionaliteit)
            df = lees_csv(tmp_pad)
            return df

        else:
            st.error(f"❌ **Ongeldig bestandstype: {bestandsextensie}**")
            st.info("💡 Ondersteunde formaten: CSV, Excel (.xlsx), PDF")
            st.stop()

    except LeverancierOnbekendError as e:
        st.error("❌ **Onbekende leverancier**")
        st.error(str(e))
        st.info("""
        💡 **Ondersteunde leveranciers:**
        - Bosal Distribution
        - Fource / LKQ Netherlands B.V.
        - Kilinclar (intern systeem)
        """)
        log_pdf_conversie(
            st.session_state.logger,
            bestandsnaam,
            None,
            0,
            False,
            str(e)
        )
        st.stop()

    except PDFParseError as e:
        st.error("❌ **PDF kan niet worden gelezen**")
        st.error(str(e))
        st.warning("⚠️ Mogelijke oorzaken:")
        st.warning("- Gescande PDF (image-based, geen tekst)")
        st.warning("- Corrupte of beschadigde PDF")
        st.warning("- Onverwachte tabelstructuur")
        st.info("💡 **Alternatief:** Gebruik een CSV of Excel export van uw leverancier.")
        log_pdf_conversie(
            st.session_state.logger,
            bestandsnaam,
            None,
            0,
            False,
            f"Parse error: {str(e)}"
        )
        st.stop()

    except PDFValidatieError as e:
        st.warning("⚠️ **PDF verwerkt, maar data lijkt onvolledig**")
        st.warning(str(e))
        st.error("**Risico:** Als u doorgaat, kunnen artikelen ontbreken in de vergelijking.")

        # Laat gebruiker beslissen
        if not st.checkbox("Ik begrijp het risico en wil toch doorgaan", key=f"risk_accept_{bestandsnaam}"):
            st.info("💡 **Veiliger alternatief:** Gebruik een CSV/Excel export.")
            log_pdf_conversie(
                st.session_state.logger,
                bestandsnaam,
                None,
                0,
                False,
                f"Validatie error: {str(e)}"
            )
            st.stop()
        else:
            # Gebruiker accepteert risico - probeer opnieuw zonder strikte validatie
            # (Voor nu: gewoon stoppen, later kan dit verfijnd worden)
            st.error("Doorgaan met incomplete data is momenteel niet ondersteund.")
            st.stop()

    except Exception as e:
        st.error(f"❌ **Onverwachte fout bij verwerken van bestand**")
        st.error(f"Details: {str(e)}")
        st.info("💡 Neem contact op met support als dit probleem blijft bestaan.")
        st.session_state.logger.error(f"Fout bij verwerken bestand {bestandsnaam}: {str(e)}")
        st.stop()

    finally:
        # Ruim tijdelijk bestand op
        if tmp_pad.exists():
            tmp_pad.unlink()


def verwerk_document_groep(bestanden, groep_naam: str) -> AggregatieResultaat:
    """
    Verwerkt meerdere documenten en aggregeert ze tot één overzicht.

    Parameters
    ----------
    bestanden : list[UploadedFile]
        Lijst van geüploade bestanden (Streamlit file_uploader).
    groep_naam : str
        Naam van de groep voor logging ("systeem" of "leverancier").

    Returns
    -------
    AggregatieResultaat
        Geaggregeerd resultaat met df_aggregaat, metadata en warnings.

    Raises
    ------
    Exception
        Als geen enkel document succesvol kon worden verwerkt.
    """

    if not bestanden:
        st.error(f"❌ Geen {groep_naam}documenten geüpload")
        st.stop()

    st.info(f"📦 **{len(bestanden)} {groep_naam}document(en)** wordt(en) verwerkt...")

    # Verzamel verwerkte documenten
    df_list = []
    document_namen = []
    document_rollen = []
    verwerkte_documenten_info = []

    # Verwerk elk bestand
    for idx, uploaded_file in enumerate(bestanden, start=1):
        bestandsnaam = uploaded_file.name
        bestandsextensie = Path(bestandsnaam).suffix.lower()

        st.write(f"**{idx}. {bestandsnaam}**")

        # Sla bestand tijdelijk op voor classificatie
        with tempfile.NamedTemporaryFile(delete=False, suffix=bestandsextensie) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_pad = Path(tmp.name)

        try:
            # Stap 1: Classificeer document
            with st.spinner(f'  → Classificeren...'):
                classificatie = classificeer_document(tmp_pad)

            # Stap 2: Toon classificatie feedback (POSITIEF, geen angst-woorden)
            if classificatie.type == 'gescand':
                st.warning(f"  ⚠️ Gescande PDF — overgeslagen (vraag digitale versie aan)")
                continue

            elif classificatie.type == 'text_geen_template':
                st.info(f"  ℹ️ PDF zonder ondersteund template — gebruik bij voorkeur CSV/Excel")
                continue

            elif classificatie.type == 'geen_artikelregels':
                st.warning(f"  ⚠️ Geen artikeltabel gevonden — overgeslagen")
                continue

            elif classificatie.type == 'template_herkend':
                # PDF met template: toon leverancier + rol
                if classificatie.rol == 'pakbon':
                    if classificatie.heeft_totaalbedrag:
                        st.success(f"  ✅ Pakbon herkend ({classificatie.leverancier})")
                    else:
                        st.success(f"  ✅ Pakbon herkend ({classificatie.leverancier}) — totalen volgen via factuur")
                elif classificatie.rol == 'factuur':
                    st.success(f"  ✅ Factuur herkend ({classificatie.leverancier}) — klaar voor vergelijking")
                else:
                    st.success(f"  ✅ Document verwerkt ({classificatie.leverancier})")

            else:
                # CSV/Excel
                if classificatie.rol == 'pakbon':
                    st.success(f"  ✅ Pakbon herkend")
                elif classificatie.rol == 'factuur':
                    st.success(f"  ✅ Factuur herkend — klaar voor vergelijking")
                else:
                    st.success(f"  ✅ Document verwerkt")

            # Stap 3: Verwerk document (reader → validator → normalizer)
            with st.spinner(f'  → Verwerken...'):
                df = verwerk_bestand(uploaded_file, groep_naam)

                # Normaliseer (als nog niet gebeurd in verwerk_bestand voor PDF)
                df_norm = normaliseer_dataframe(df, groep_naam)

                # Valideer genormaliseerde data
                is_valid, fouten = valideer_dataframe(df_norm, groep_naam)

                if not is_valid:
                    st.warning(f"  ⚠️ Document heeft missende gegevens — overgeslagen")
                    for fout in fouten:
                        st.caption(f"     • {fout}")
                    continue

                # Document succesvol verwerkt
                df_list.append(df_norm)
                document_namen.append(bestandsnaam)
                document_rollen.append(classificatie.rol)

                verwerkte_documenten_info.append({
                    'naam': bestandsnaam,
                    'rol': classificatie.rol,
                    'aantal_regels': len(df_norm)
                })

                st.success(f"  ✅ **{len(df_norm)} artikelregels** geëxtraheerd")

        except Exception as e:
            st.warning(f"  ⚠️ Document kon niet worden verwerkt: {str(e)}")
            st.session_state.logger.warning(f"Fout bij verwerken {bestandsnaam}: {str(e)}")
            continue

        finally:
            # Ruim tijdelijk bestand op
            if tmp_pad.exists():
                tmp_pad.unlink()

    # Check of er geldige documenten zijn
    if not df_list:
        st.error(f"❌ **Geen geldige {groep_naam}documenten**")
        st.info("""
        💡 **Wat kunt u doen?**
        • Controleer of de documenten artikelregels bevatten
        • Gebruik CSV of Excel formaat voor beste resultaten
        • Zorg dat PDF's niet gescand zijn (digitale versie nodig)
        """)
        st.stop()

    # Stap 4: Aggregeer documenten
    st.divider()
    st.write(f"**📊 Aggregatie {groep_naam}documenten**")

    with st.spinner('Documenten worden samengevoegd...'):
        try:
            result = aggregeer_documenten(
                df_list=df_list,
                document_namen=document_namen,
                document_rollen=document_rollen
            )
        except Exception as e:
            st.error(f"❌ Fout bij aggregeren: {str(e)}")
            st.session_state.logger.error(f"Aggregatie fout ({groep_naam}): {str(e)}")
            st.stop()

    # Stap 5: Toon aggregatie samenvatting
    totaal_input = result.metadata['totaal_regels_input']
    totaal_output = result.metadata['totaal_regels_output']
    aantal_docs = result.metadata['aantal_documenten_verwerkt']

    st.success(f"✅ **{aantal_docs} document(en) samengevoegd tot {totaal_output} unieke artikelen**")
    st.caption(f"   ({totaal_input} regels → {totaal_output} unieke artikelen)")

    # Toon warnings (prijsverschillen, etc.)
    if result.warnings:
        with st.expander(f"⚠️ {len(result.warnings)} waarschuwing(en) — niet-blokkerend"):
            for warning in result.warnings:
                st.caption(f"• {warning}")

    # Toon details in expander
    with st.expander("📋 Documentdetails"):
        for info in verwerkte_documenten_info:
            rol_emoji = "📦" if info['rol'] == 'pakbon' else "📄" if info['rol'] == 'factuur' else "📋"
            st.caption(f"{rol_emoji} **{info['naam']}** — {info['rol']} — {info['aantal_regels']} regels")

    st.divider()

    return result


# ============================================================================
# HEADER
# ============================================================================

st.title("📊 Factuurvergelijker")
st.markdown("""
Vergelijk uw systeemdocumenten met leveranciersdocumenten om automatisch afwijkingen te detecteren.

**Hoe werkt het?**
1. Upload één of meerdere systeemdocumenten (pakbonnen, exports)
2. Upload één of meerdere leveranciersdocumenten (facturen)
3. Klik op "Vergelijk facturen"
4. Download het Excel-rapport met de resultaten

**✨ Nieuw in v1.3:** Multi-document vergelijking! Upload meerdere pakbonnen + facturen tegelijk.
""")

st.divider()


# ============================================================================
# BESTANDSUPLOAD
# ============================================================================

st.subheader("📤 Stap 1: Upload bestanden")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**📦 Systeem Documenten**")
    bestanden_systeem = st.file_uploader(
        "Upload één of meerdere documenten",
        type=['csv', 'xlsx', 'xls', 'pdf'],
        key='systeem',
        accept_multiple_files=True,
        help="Pakbonnen, exports uit uw eigen systeem (CSV, Excel, PDF)"
    )
    if bestanden_systeem:
        st.caption(f"✅ {len(bestanden_systeem)} document(en) geselecteerd")

with col2:
    st.markdown("**📄 Leverancier Documenten**")
    bestanden_factuur = st.file_uploader(
        "Upload één of meerdere documenten",
        type=['csv', 'xlsx', 'xls', 'pdf'],
        key='factuur',
        accept_multiple_files=True,
        help="Facturen van leverancier (CSV, Excel, PDF)"
    )
    if bestanden_factuur:
        st.caption(f"✅ {len(bestanden_factuur)} document(en) geselecteerd")

st.divider()


# ============================================================================
# VERGELIJKING UITVOEREN
# ============================================================================

st.subheader("⚡ Stap 2: Vergelijk")

# Check of beide kanten documenten hebben
beide_kanten_aanwezig = (
    bestanden_systeem is not None and len(bestanden_systeem) > 0 and
    bestanden_factuur is not None and len(bestanden_factuur) > 0
)

if beide_kanten_aanwezig:
    st.success(f"✅ Beide kanten hebben documenten ({len(bestanden_systeem)} systeem, {len(bestanden_factuur)} leverancier)")
else:
    st.warning("⚠️ Upload eerst documenten aan beide kanten voordat u kunt vergelijken")

# Vergelijkingsknop
vergelijk_knop = st.button(
    "🔍 Vergelijk documenten",
    disabled=not beide_kanten_aanwezig,
    type="primary",
    use_container_width=True
)


# ============================================================================
# VERWERKING
# ============================================================================

if vergelijk_knop:

    try:
        start_tijd = time.time()

        st.divider()
        st.subheader("🔄 Verwerking")

        # ====================================================================
        # STAP 1: VERWERK SYSTEEM DOCUMENTEN
        # ====================================================================
        st.markdown("### 📦 Systeem Documenten")
        result_systeem = verwerk_document_groep(bestanden_systeem, "systeem")

        # ====================================================================
        # STAP 2: VERWERK LEVERANCIER DOCUMENTEN
        # ====================================================================
        st.markdown("### 📄 Leverancier Documenten")
        result_leverancier = verwerk_document_groep(bestanden_factuur, "leverancier")

        # ====================================================================
        # STAP 3: VERGELIJKING
        # ====================================================================
        st.markdown("### 🔍 Vergelijking")

        # Log start
        systeem_namen = ", ".join(result_systeem.metadata['document_namen'])
        leverancier_namen = ", ".join(result_leverancier.metadata['document_namen'])

        log_vergelijking_start(
            st.session_state.logger,
            systeem_namen,
            leverancier_namen,
            len(result_systeem.df_aggregaat),
            len(result_leverancier.df_aggregaat)
        )

        # Voer vergelijking uit op geaggregeerde data
        with st.spinner('Geaggregeerde documenten worden vergeleken...'):
            df_resultaat = vergelijk_facturen(
                result_systeem.df_aggregaat,
                result_leverancier.df_aggregaat
            )
            samenvatting = genereer_samenvatting(df_resultaat)

        st.success(f"✅ **Vergelijking voltooid** — {len(df_resultaat)} artikelen vergeleken")

        # ====================================================================
        # STAP 4: EXCEL RAPPORT
        # ====================================================================
        with st.spinner('Excel-rapport wordt gegenereerd...'):
            output_dir = Path(tempfile.gettempdir()) / 'factuurvergelijker_output'
            output_dir.mkdir(exist_ok=True)

            # Gebruik eerste bestandsnaam per kant voor Excel naam
            systeem_naam = result_systeem.metadata['document_namen'][0].replace('.pdf', '').replace('.csv', '')
            leverancier_naam = result_leverancier.metadata['document_namen'][0].replace('.pdf', '').replace('.csv', '')

            excel_pad = exporteer_naar_excel(
                df_resultaat,
                output_dir,
                systeem_naam,
                leverancier_naam,
                aggregatie_systeem=result_systeem,        # v1.3 Fase 4a
                aggregatie_leverancier=result_leverancier  # v1.3 Fase 4a
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
        st.session_state.aggregatie_systeem = result_systeem
        st.session_state.aggregatie_leverancier = result_leverancier

        st.success(f"✅ **Volledige verwerking voltooid in {verwerkingstijd:.1f} seconden!**")

    except FileNotFoundError as e:
        st.error(f"❌ **Bestand niet gevonden:** {e}")

    except ValueError as e:
        st.error(f"❌ **Ongeldige data:** {e}")
        st.info("💡 Controleer of uw bestanden de juiste kolommen bevatten.")

    except Exception as e:
        st.error(f"❌ **Er is een onverwachte fout opgetreden:** {e}")
        st.info("💡 Neem contact op met de systeembeheerder als dit probleem aanhoudt.")
        st.session_state.logger.error(f"Onverwachte fout tijdens vergelijking: {str(e)}")


# ============================================================================
# RESULTATEN WEERGEVEN
# ============================================================================

if 'resultaat' in st.session_state:

    st.divider()
    st.subheader("📊 Stap 3: Resultaten")

    # AGGREGATIE INFORMATIE (indien beschikbaar)
    if 'aggregatie_systeem' in st.session_state and 'aggregatie_leverancier' in st.session_state:
        st.markdown("### 📋 Verwerkte Documenten")

        col_sys, col_lev = st.columns(2)

        with col_sys:
            agg_sys = st.session_state.aggregatie_systeem
            st.info(f"""
            **📦 Systeem:** {agg_sys.metadata['aantal_documenten_verwerkt']} document(en)
            - {agg_sys.metadata['totaal_regels_input']} regels → {agg_sys.metadata['totaal_regels_output']} unieke artikelen
            """)

        with col_lev:
            agg_lev = st.session_state.aggregatie_leverancier
            st.info(f"""
            **📄 Leverancier:** {agg_lev.metadata['aantal_documenten_verwerkt']} document(en)
            - {agg_lev.metadata['totaal_regels_input']} regels → {agg_lev.metadata['totaal_regels_output']} unieke artikelen
            """)

    # SAMENVATTING
    st.markdown("### 📈 Vergelijkingsresultaat")
    
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
    
    # ✨ v1.2.2: Styling met kleurcodering EN number formatting
    df_styled = df_tonen.style \
        .applymap(kleur_status, subset=['status']) \
        .format({
            'aantal_systeem': lambda x: formatteer_aantal(x),
            'aantal_factuur': lambda x: formatteer_aantal(x),
            'prijs_systeem': lambda x: formatteer_prijs(x),
            'prijs_factuur': lambda x: formatteer_prijs(x),
            'totaal_systeem': lambda x: formatteer_prijs(x),
            'totaal_factuur': lambda x: formatteer_prijs(x)
        })

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
    <p>Factuurvergelijker v1.3 | Gebouwd met Streamlit</p>
    <p>✨ Multi-document vergelijking • PDF ondersteuning • Automatische aggregatie</p>
    <p>Alle vergelijkingen worden automatisch gelogd voor audit-doeleinden</p>
</div>
""", unsafe_allow_html=True)