"""
Interfaccia BROKER.

Form di inserimento di una nuova pratica che rispecchia il flusso del diagramma:
campi condizionali in base a "già cliente", "polizza emessa" e "già pagato".

I widget sono fuori da `st.form` proprio per ottenere il comportamento dinamico
(mostrare/nascondere campi mentre l'utente compie le scelte). Il salvataggio
avviene al click del pulsante finale.
"""
from __future__ import annotations

import io
import socket
import uuid
from datetime import date

import qrcode
import streamlit as st

from app.ui_common import sezione, setup_page
from database.connection import get_session
from services import documento_service, operatore_service, pratica_service
from services.pratica_service import ValidazionePraticaError
from utils.config import (
    COMPAGNIE,
    DB_URL,
    METODI_PAGAMENTO,
    Ruolo,
    TipoCliente,
    TipoDocumento,
    TipoPolizza,
    Urgenza,
)

_is_cloud = not DB_URL.startswith("sqlite")


def _ip_locale() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def _porta_streamlit() -> int:
    try:
        from streamlit import config as _cfg
        return int(_cfg.get_option("server.port"))
    except Exception:
        return 8501


def _avvia_tunnel():
    """Avvia (o riutilizza) un tunnel ngrok. Ritorna URL stringa, o False se non configurato."""
    try:
        from pyngrok import ngrok, exception as ngrok_ex
        porta = _porta_streamlit()
        for t in ngrok.get_tunnels():
            if str(porta) in t.config.get("addr", ""):
                return f"{t.public_url}/Broker"
        tunnel = ngrok.connect(porta, "http")
        return f"{tunnel.public_url}/Broker"
    except Exception:
        return False


def _qr_bytes(url: str) -> bytes:
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _carica_broker():
    with get_session() as session:
        ops = operatore_service.lista_operatori(session, ruolo=Ruolo.BROKER)
        # Estrae (id, nome) per evitare oggetti detached fuori sessione.
        return [(o.id, o.nome) for o in ops]


def _file_a_documento(uploaded, tipo: TipoDocumento):
    """Trasforma un file caricato in un dict-documento per il service."""
    if uploaded is None:
        return None
    return {
        "tipo_documento": tipo.value,
        "nome_file": uploaded.name,
        "contenuto": uploaded.getvalue(),
    }


def _input_documento(label: str, key: str, v: int):
    """File uploader + fotocamera: restituisce il primo input non nullo."""
    tab_file, tab_cam = st.tabs(["📁 Carica file", "📷 Fotocamera"])
    with tab_file:
        da_file = st.file_uploader(
            label, type=["pdf", "jpg", "jpeg", "png"],
            key=f"{key}_file_{v}", label_visibility="collapsed",
        )
    with tab_cam:
        da_camera = st.camera_input("Scatta una foto", key=f"{key}_cam_{v}")
    return da_file or da_camera


def render() -> None:
    setup_page("Inserimento Pratica · Broker", "📝")
    st.title("📝 Inserimento Nuova Pratica")
    st.caption("Compila i dati della pratica assicurativa e invia alla segreteria.")

    if "form_v" not in st.session_state:
        st.session_state.form_v = 0
    v = st.session_state.form_v

    if st.session_state.get("pratica_inviata"):
        st.success(f"✅ Pratica **{st.session_state.pratica_inviata}** inviata correttamente alla segreteria!")
        st.balloons()
        del st.session_state["pratica_inviata"]

    broker = _carica_broker()
    if not broker:
        st.error("Nessun broker configurato. Esegui prima `python -m database.init_db`.")
        return

    # ------------------------------------------------------------------ #
    # Broker che inserisce
    # ------------------------------------------------------------------ #
    sezione("Operatore")
    broker_scelto = st.selectbox(
        "Broker che inserisce la pratica",
        options=broker,
        format_func=lambda x: x[1],
    )
    broker_id = broker_scelto[0]

    # ------------------------------------------------------------------ #
    # Cliente
    # ------------------------------------------------------------------ #
    sezione("Cliente")
    col1, col2 = st.columns(2)
    with col1:
        gia_cliente = st.radio("È già cliente?", ["Sì", "No"], horizontal=True) == "Sì"
    with col2:
        tipo_cliente = st.radio(
            "Tipo cliente", ["Privato", "Azienda"], horizontal=True
        )
    tipo_cliente_enum = (
        TipoCliente.AZIENDA if tipo_cliente == "Azienda" else TipoCliente.PRIVATO
    )

    nome_label = "Ragione Sociale" if tipo_cliente_enum == TipoCliente.AZIENDA else "Nome e Cognome"
    nome_cliente = st.text_input(nome_label)

    partita_iva = ""
    documenti = []

    # ------------------------------------------------------------------ #
    # Polizza
    # ------------------------------------------------------------------ #
    sezione("Polizza")
    col5, col6 = st.columns(2)
    with col5:
        compagnia_sel = st.selectbox("Compagnia assicurativa", COMPAGNIE)
        compagnia = (
            st.text_input("Specifica compagnia") if compagnia_sel == "Altro" else compagnia_sel
        )
    with col6:
        tipo_polizza_label = st.radio(
            "Tipo polizza", ["Auto", "Rami Elementari"], horizontal=True
        )
    tipo_polizza = (
        TipoPolizza.AUTO if tipo_polizza_label == "Auto" else TipoPolizza.RAMI_ELEMENTARI
    )

    if tipo_polizza == TipoPolizza.AUTO:
        prima_volta_macchina = st.radio(
            "La macchina viene inserita per la prima volta?",
            ["No", "Sì"],
            horizontal=True,
            key=f"prima_volta_{v}",
        ) == "Sì"
    else:
        prima_volta_macchina = False

    emissione = st.radio("È stata già emessa la polizza?", ["Sì", "No"], horizontal=True) == "Sì"
    n_polizza = n_preventivo = None
    data_decorrenza = None
    col7, col8 = st.columns(2)
    if emissione:
        with col7:
            n_polizza = st.text_input("Numero polizza")
        with col8:
            data_decorrenza = st.date_input("Data decorrenza (opzionale)", value=None, format="DD/MM/YYYY")
    else:
        with col7:
            n_preventivo = st.text_input("Numero preventivo")
        with col8:
            data_decorrenza = st.date_input("Data decorrenza", value=date.today(), format="DD/MM/YYYY")

    col9, col10 = st.columns(2)
    with col9:
        importo_polizza = st.number_input("Importo polizza (€)", min_value=0.0, step=10.0, format="%.2f")
    with col10:
        importo_cliente = st.number_input("Importo cliente (€)", min_value=0.0, step=10.0, format="%.2f")

    # ------------------------------------------------------------------ #
    # Pagamento
    # ------------------------------------------------------------------ #
    sezione("Pagamento")
    gia_pagato = st.radio("Ha già pagato?", ["Sì", "No"], horizontal=True) == "Sì"
    incasso = None
    invia_mail = None
    metodo_pagamento = None

    if gia_pagato:
        metodo_pagamento = st.selectbox("Metodo di pagamento", METODI_PAGAMENTO)
    else:
        incasso = st.radio("Importo incassato?", ["Sì", "No"], horizontal=True) == "Sì"
        if incasso:
            metodo_pagamento = st.selectbox("Metodo di incasso", METODI_PAGAMENTO)
        else:
            invia_mail = st.radio(
                "Inviare una mail al cliente per effettuare il pagamento?",
                ["Sì", "No"],
                horizontal=True,
            ) == "Sì"

    # ------------------------------------------------------------------ #
    # Gestione / priorità
    # ------------------------------------------------------------------ #
    sezione("Gestione")
    col11, col12 = st.columns([1, 2])
    with col11:
        urgenza_label = st.radio("Urgenza", ["Bassa", "Alta"], horizontal=True)
    urgenza = Urgenza.ALTA if urgenza_label == "Alta" else Urgenza.BASSA
    with col12:
        note = st.text_area("Note (opzionale)", height=80)

    # ------------------------------------------------------------------ #
    # Documenti allegati
    # ------------------------------------------------------------------ #
    if not gia_cliente or prima_volta_macchina:
        sezione("Documenti allegati")
        if prima_volta_macchina and gia_cliente:
            st.info(
                "**Nuova macchina** → carica i documenti del veicolo: Libretto. "
                "Aggiungi eventuali altri documenti se necessario."
            )
        else:
            st.info(
                "**Nuovo cliente** → carica i documenti (fronte e retro): "
                "documento d'identità + Codice Fiscale. "
                "Se azienda: Visura + C.I. del legale rappresentante. "
                "Se polizza Auto: Libretto."
            )
        with st.expander("📎 Documenti allegati", expanded=True):
            if "upload_sid" not in st.session_state:
                st.session_state.upload_sid = uuid.uuid4().hex
            sid = st.session_state.upload_sid

            _usa_storage = documento_service._usa_cloud()

            if _is_cloud and _usa_storage:
                host = st.context.headers.get("host", "")
                mobile_url = f"https://{host}/Upload_Documenti?sid={sid}" if host else None
            elif not _is_cloud:
                mobile_url = f"http://{_ip_locale()}:{_porta_streamlit()}/Upload_Documenti?sid={sid}"
            else:
                mobile_url = None

            if mobile_url:
                col_qr, col_info = st.columns([1, 3])
                with col_qr:
                    st.image(_qr_bytes(mobile_url), width=130)
                with col_info:
                    st.markdown("**Carica foto dal cellulare**")
                    st.caption("Inquadra il QR: si apre solo il form di caricamento foto, non l'intera pratica.")
                    if not _is_cloud:
                        st.caption("Il telefono deve essere sulla stessa rete WiFi.")

                if not _is_cloud:
                    if "tunnel_url" not in st.session_state:
                        st.session_state.tunnel_url = None
                    if st.button("📱 Genera link pubblico (ngrok)", use_container_width=True):
                        with st.spinner("Avvio tunnel…"):
                            st.session_state.tunnel_url = _avvia_tunnel()
                    if isinstance(st.session_state.tunnel_url, str):
                        ngrok_upload = st.session_state.tunnel_url + f"/Upload_Documenti?sid={sid}"
                        col_qr2, col_url2 = st.columns([1, 3])
                        with col_qr2:
                            st.image(_qr_bytes(ngrok_upload), width=130)
                        with col_url2:
                            st.markdown(f"**URL pubblico:** `{ngrok_upload}`")
                            st.caption("Funziona anche senza WiFi condiviso. Scade alla chiusura.")
                    elif st.session_state.tunnel_url is False:
                        st.warning(
                            "ngrok non configurato. Esegui nel terminale:\n\n"
                            "```\nngrok config add-authtoken IL_TUO_TOKEN\n```"
                        )

            if _usa_storage:
                col_aggiorna, _ = st.columns([1, 3])
                with col_aggiorna:
                    if st.button("🔄 Aggiorna documenti ricevuti", use_container_width=True):
                        st.session_state.docs_remoti = documento_service.lista_temp_files(sid)

                docs_remoti = st.session_state.get("docs_remoti", [])
                if docs_remoti:
                    st.success(f"{len(docs_remoti)} documento/i ricevuto/i dal telefono:")
                    for d in docs_remoti:
                        st.markdown(f"• **{d['tipo']}** — {d['nome']}")
                elif "docs_remoti" in st.session_state:
                    st.info("Nessun documento ricevuto ancora. Carica dal telefono e poi aggiorna.")

            st.divider()
            doc_identita = _input_documento(
                "Documento d'identità (Carta d'Identità / Patente / Passaporto)", "identita", v
            )
            doc_cf = _input_documento("Codice Fiscale (tessera)", "cf", v)
            doc_visura = _input_documento("Visura (se azienda)", "visura", v)
            doc_libretto = _input_documento("Libretto (se polizza Auto)", "libretto", v)

            for up, tipo in (
                (doc_identita, TipoDocumento.CARTA_IDENTITA),
                (doc_cf, TipoDocumento.CODICE_FISCALE),
                (doc_visura, TipoDocumento.VISURA),
                (doc_libretto, TipoDocumento.LIBRETTO),
            ):
                d = _file_a_documento(up, tipo)
                if d:
                    documenti.append(d)

    st.divider()

    # ------------------------------------------------------------------ #
    # Invio
    # ------------------------------------------------------------------ #
    if st.button("📨 Invia pratica alla segreteria", type="primary", use_container_width=True):
        # Aggiunge i documenti caricati dal telefono (già su Supabase Storage).
        for d in st.session_state.get("docs_remoti", []):
            documenti.append({
                "tipo_documento": d["tipo"],
                "nome_file": d["nome"],
                "percorso": d["url"],
            })

        dati = {
            "broker_id": broker_id,
            "gia_cliente": gia_cliente,
            "tipo_cliente": tipo_cliente_enum.value,
            "nome_cliente": nome_cliente,
            "partita_iva": partita_iva,
            "compagnia": compagnia,
            "tipo_polizza": tipo_polizza.value,
            "emissione_polizza": emissione,
            "n_polizza": n_polizza,
            "n_preventivo": n_preventivo,
            "data_decorrenza": data_decorrenza,
            "importo_polizza": importo_polizza or None,
            "importo_cliente": importo_cliente or None,
            "gia_pagato": gia_pagato,
            "incasso": incasso,
            "metodo_pagamento": metodo_pagamento,
            "invia_mail": invia_mail,
            "urgenza": urgenza.value,
            "note": note,
            "documenti": documenti,
        }
        try:
            with get_session() as session:
                pratica = pratica_service.crea_pratica(session, dati)
                numero = pratica.numero_pratica
            # Reset del form: cancella upload session e incrementa versione widget.
            for k in ("docs_remoti", "upload_sid", "tunnel_url"):
                st.session_state.pop(k, None)
            st.session_state.pratica_inviata = numero
            st.session_state.form_v += 1
            st.rerun()
        except ValidazionePraticaError as e:
            st.error("Impossibile inviare la pratica. Correggi gli errori seguenti:")
            for err in e.errori:
                st.markdown(f"- {err}")
        except Exception as e:  # pragma: no cover - rete di sicurezza UI
            st.error(f"Errore inatteso durante il salvataggio: {e}")


if __name__ == "__main__":
    render()
