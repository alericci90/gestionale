"""Pagina mobile-only per il caricamento rapido di foto/documenti."""
import streamlit as st

from services import documento_service
from utils.config import LABEL_TIPO_DOCUMENTO, TipoDocumento

st.set_page_config(page_title="Carica Documento", page_icon="📷", layout="centered")
# Nasconde sidebar per esperienza mobile pulita
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

st.title("📷 Carica documento")
st.caption("Seleziona il tipo, scatta una foto o carica un file, poi premi Carica.")

tipo_sel = st.selectbox(
    "Tipo di documento",
    options=list(TipoDocumento),
    format_func=lambda t: LABEL_TIPO_DOCUMENTO[t],
)

tab_cam, tab_file = st.tabs(["📷 Fotocamera", "📁 Carica file"])
with tab_cam:
    foto = st.camera_input("Scatta una foto")
with tab_file:
    upload = st.file_uploader(
        "Seleziona file", type=["pdf", "jpg", "jpeg", "png"],
        label_visibility="collapsed",
    )

file = foto or upload

if file:
    if st.button("✅ Carica", type="primary", use_container_width=True):
        nome = getattr(file, "name", f"foto_{tipo_sel.value}.jpg")
        with st.spinner("Caricamento in corso…"):
            try:
                documento_service.salva_temp_file(
                    sid=sid,
                    tipo=tipo_sel.value,
                    nome_file=nome,
                    contenuto=file.getvalue(),
                )
                st.success("Documento caricato! Torna sull'app e clicca **Aggiorna documenti** per includerlo.")
                st.balloons()
            except Exception as e:
                st.error(f"Errore durante il caricamento: {e}")
