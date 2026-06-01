"""Pagina mobile-only per il caricamento rapido di foto/documenti."""
import streamlit as st

from services import documento_service

st.set_page_config(page_title="Carica Documenti", page_icon="📷", layout="centered")
st.markdown(
    "<style>[data-testid='stSidebar']{display:none}</style>",
    unsafe_allow_html=True,
)

sid = st.query_params.get("sid")

if not sid:
    st.warning("Apri questa pagina inquadrando il QR code dall'app principale.")
    st.stop()

if not documento_service._usa_cloud():
    st.error("Funzione disponibile solo in modalità cloud con Supabase configurato.")
    st.stop()

st.title("📷 Carica documenti")
st.caption("Scatta foto o seleziona file — puoi caricare tutto in una volta.")

if "n_caricati" not in st.session_state:
    st.session_state.n_caricati = 0

tab_cam, tab_file = st.tabs(["📷 Fotocamera", "📁 File multipli"])

with tab_cam:
    foto = st.camera_input("Scatta una foto")
    if foto and st.button("✅ Carica foto", type="primary", use_container_width=True, key="btn_cam"):
        with st.spinner("Caricamento…"):
            try:
                documento_service.salva_temp_file(
                    sid=sid,
                    tipo="documento",
                    nome_file=f"foto.jpg",
                    contenuto=foto.getvalue(),
                )
                st.session_state.n_caricati += 1
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

with tab_file:
    files = st.file_uploader(
        "Seleziona uno o più file",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if files and st.button("✅ Carica tutti", type="primary", use_container_width=True, key="btn_files"):
        with st.spinner(f"Caricamento {len(files)} file…"):
            errori = []
            for f in files:
                try:
                    documento_service.salva_temp_file(
                        sid=sid,
                        tipo="documento",
                        nome_file=f.name,
                        contenuto=f.getvalue(),
                    )
                    st.session_state.n_caricati += 1
                except Exception as e:
                    errori.append(f"{f.name}: {e}")
            if errori:
                for err in errori:
                    st.error(err)
            else:
                st.rerun()

if st.session_state.n_caricati > 0:
    st.success(f"✅ {st.session_state.n_caricati} documento/i caricato/i.")
    st.info("Torna sull'app principale e clicca **Aggiorna documenti ricevuti** per includerli nella pratica.")
