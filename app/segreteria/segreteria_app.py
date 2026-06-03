"""
Interfaccia SEGRETERIA.

Gestione delle pratiche come sistema di ticket:
- dashboard con conteggi per stato;
- filtri (testo, stato, urgenza, compagnia, assegnazione) nella sidebar;
- ordinamento per priorità / data / numero;
- tabella con evidenziazione della priorità alta;
- pannello di dettaglio con aggiornamento stato, assegnazione operatore,
  modifica urgenza e note.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.ui_common import campo_dettaglio, sezione, setup_page
from database.connection import get_session
from services import operatore_service, pratica_service
from services.documento_service import lista_documenti
from services.pratica_service import FiltriPratiche
from utils.config import (
    COMPAGNIE,
    LABEL_TIPO_DOCUMENTO,
    Ruolo,
    StatoPratica,
    TipoDocumento,
    Urgenza,
)
from utils.formatting import (
    badge_stato,
    badge_urgenza,
    data_it,
    emoji_stato,
    emoji_urgenza,
    euro,
    label_stato,
    label_tipo_polizza,
    label_urgenza,
)

# Mappe etichetta <-> enum per i widget.
_STATI = {label_stato(s.value): s for s in StatoPratica}
_URGENZE = {label_urgenza(u.value): u for u in Urgenza}


def _carica_operatori_segreteria():
    with get_session() as session:
        ops = operatore_service.lista_operatori(session, ruolo=Ruolo.SEGRETERIA)
        return [(o.id, o.nome) for o in ops]


def _to_record(p) -> dict:
    """Riduce una pratica (caricata con relazioni) a un dict serializzabile."""
    return {
        "id": p.id,
        "numero": p.numero_pratica,
        "cliente": p.cliente.nome,
        "compagnia": p.compagnia,
        "tipo_polizza": label_tipo_polizza(p.tipo_polizza),
        "urgenza": p.urgenza,
        "stato": p.stato,
        "importo_cliente": float(p.importo_cliente) if p.importo_cliente is not None else None,
        "assegnato": p.operatore_assegnato.nome if p.operatore_assegnato else "—",
        "broker": p.broker.nome if p.broker else "—",
        "creata": p.created_at,
    }


def _dettaglio_record(p) -> dict:
    """Snapshot completo di una pratica per il pannello dettaglio."""
    with get_session() as session:
        documenti = [
            (d.tipo_documento, d.nome_file, d.percorso)
            for d in lista_documenti(session, p.id)
        ]
    return {
        "id": p.id,
        "numero": p.numero_pratica,
        "stato": p.stato,
        "urgenza": p.urgenza,
        "cliente": p.cliente.nome,
        "tipo_cliente": p.cliente.tipo,
        "gia_cliente": p.gia_cliente,
        "compagnia": p.compagnia,
        "tipo_polizza": label_tipo_polizza(p.tipo_polizza),
        "emissione_polizza": p.emissione_polizza,
        "n_polizza": p.n_polizza,
        "n_preventivo": p.n_preventivo,
        "data_decorrenza": p.data_decorrenza,
        "importo_polizza": float(p.importo_polizza) if p.importo_polizza is not None else None,
        "importo_cliente": float(p.importo_cliente) if p.importo_cliente is not None else None,
        "gia_pagato": p.gia_pagato,
        "incasso": p.incasso,
        "metodo_pagamento": p.metodo_pagamento,
        "invia_mail": p.invia_mail,
        "note": p.note or "",
        "broker": p.broker.nome if p.broker else "—",
        "assegnato_id": p.operatore_assegnato_id,
        "assegnato": p.operatore_assegnato.nome if p.operatore_assegnato else None,
        "creata": p.created_at,
        "documenti": documenti,
    }


def _bool_it(v) -> str:
    if v is None:
        return "—"
    return "Sì" if v else "No"


# --------------------------------------------------------------------------- #
# Sidebar: filtri e ordinamento
# --------------------------------------------------------------------------- #
def _sidebar_filtri() -> FiltriPratiche:
    st.sidebar.header("🔎 Filtri")
    testo = st.sidebar.text_input("Cerca (numero / cliente / compagnia)")

    urgenze_sel = st.sidebar.multiselect("Urgenza", list(_URGENZE.keys()))
    compagnia_sel = st.sidebar.selectbox("Compagnia", ["Tutte"] + COMPAGNIE)

    operatori = _carica_operatori_segreteria()
    opzioni_assegn = ["Tutte", "Solo non assegnate"] + [f"{n}" for _, n in operatori]
    assegn_sel = st.sidebar.selectbox("Assegnazione", opzioni_assegn)

    st.sidebar.divider()
    st.sidebar.subheader("↕️ Ordinamento")
    ordina_label = st.sidebar.radio(
        "Ordina per", ["Priorità", "Data inserimento", "Numero pratica"]
    )
    ordina_map = {"Priorità": "priorita", "Data inserimento": "data", "Numero pratica": "numero"}
    crescente = True
    if ordina_label != "Priorità":
        crescente = st.sidebar.toggle("Ordine crescente", value=True)

    filtri = FiltriPratiche(
        testo=testo or None,
        urgenze=[_URGENZE[u] for u in urgenze_sel],
        compagnia=None if compagnia_sel == "Tutte" else compagnia_sel,
        ordina_per=ordina_map[ordina_label],
        ordine_crescente=crescente,
    )
    if assegn_sel == "Solo non assegnate":
        filtri.solo_non_assegnate = True
    elif assegn_sel != "Tutte":
        for oid, nome in operatori:
            if nome == assegn_sel:
                filtri.operatore_assegnato_id = oid
                break
    return filtri


# --------------------------------------------------------------------------- #
# Dashboard metriche
# --------------------------------------------------------------------------- #
def _dashboard() -> None:
    with get_session() as session:
        conteggi = pratica_service.conta_per_stato(session)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Totale pratiche", sum(conteggi.values()))
    c2.metric("🆕 Nuove", conteggi.get(StatoPratica.NUOVA.value, 0))
    c3.metric("⚙️ In lavorazione", conteggi.get(StatoPratica.IN_LAVORAZIONE.value, 0))
    c4.metric("✅ Completate", conteggi.get(StatoPratica.COMPLETATA.value, 0))


# --------------------------------------------------------------------------- #
# Tabella
# --------------------------------------------------------------------------- #
def _tabella(records: list[dict]) -> None:
    if not records:
        st.info("Nessuna pratica corrisponde ai filtri selezionati.")
        return

    df = pd.DataFrame([{
        "N. Pratica": r["numero"],
        "Cliente": r["cliente"],
        "Compagnia": r["compagnia"],
        "Polizza": r["tipo_polizza"],
        "Urgenza": emoji_urgenza(r["urgenza"]),
        "Stato": emoji_stato(r["stato"]),
        "Importo cliente": euro(r["importo_cliente"]),
        "Assegnata a": r["assegnato"],
        "Creata il": data_it(r["creata"]),
    } for r in records])

    def _evidenzia(row):
        is_alta = row["Urgenza"].startswith("🔴")
        return ["background-color: #fdecea" if is_alta else "" for _ in row]

    styler = df.style.apply(_evidenzia, axis=1)
    st.dataframe(styler, use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------- #
# Pannello dettaglio + azioni
# --------------------------------------------------------------------------- #
def _pannello_dettaglio(records: list[dict]) -> None:
    sezione("Dettaglio e gestione pratica")
    if not records:
        return

    numeri = {r["numero"]: r["id"] for r in records}
    scelto = st.selectbox("Apri il dettaglio della pratica", list(numeri.keys()))
    pratica_id = numeri[scelto]

    with get_session() as session:
        p = pratica_service.get_pratica(session, pratica_id)
        if p is None:
            st.warning("Pratica non trovata.")
            return
        det = _dettaglio_record(p)

    # Intestazione con badge.
    st.markdown(
        f"### {det['numero']} &nbsp; {badge_stato(det['stato'])} &nbsp; {badge_urgenza(det['urgenza'])}",
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        campo_dettaglio("Cliente", f"{det['cliente']} ({det['tipo_cliente']})")
        campo_dettaglio("Già cliente", _bool_it(det["gia_cliente"]))
        campo_dettaglio("Broker", det["broker"])
    with col_b:
        campo_dettaglio("Compagnia", det["compagnia"])
        campo_dettaglio("Tipo polizza", det["tipo_polizza"])
        campo_dettaglio("Polizza emessa", _bool_it(det["emissione_polizza"]))
    with col_c:
        if det["emissione_polizza"]:
            campo_dettaglio("N. polizza", det["n_polizza"] or "—")
        else:
            campo_dettaglio("N. preventivo", det["n_preventivo"] or "—")
        campo_dettaglio("Data decorrenza", data_it(det["data_decorrenza"]))
        campo_dettaglio("Creata il", data_it(det["creata"]))

    col_d, col_e, col_f = st.columns(3)
    with col_d:
        campo_dettaglio("Importo polizza", euro(det["importo_polizza"]))
    with col_e:
        campo_dettaglio("Importo cliente", euro(det["importo_cliente"]))
    with col_f:
        campo_dettaglio("Già pagato", _bool_it(det["gia_pagato"]))

    col_g, col_h, col_i = st.columns(3)
    with col_g:
        campo_dettaglio("Incassato", _bool_it(det["incasso"]))
    with col_h:
        campo_dettaglio("Metodo", det["metodo_pagamento"] or "—")
    with col_i:
        campo_dettaglio("Mail al cliente", _bool_it(det["invia_mail"]))

    if det["note"]:
        campo_dettaglio("Note del Broker", det["note"])

    # Documenti.
    if det["documenti"]:
        st.markdown("**Documenti allegati:**")
        for tipo, nome, percorso in det["documenti"]:
            etichetta = LABEL_TIPO_DOCUMENTO.get(TipoDocumento(tipo), tipo)
            col_nome, col_btn = st.columns([4, 1])
            with col_nome:
                st.markdown(f"- {etichetta}: `{nome}`")
            with col_btn:
                if percorso:
                    if percorso.startswith("http"):
                        st.link_button("⬇️ Scarica", percorso)
                    elif Path(percorso).exists():
                        st.download_button(
                            label="⬇️ Scarica",
                            data=Path(percorso).read_bytes(),
                            file_name=nome,
                            key=f"dl_{percorso}",
                        )

    st.divider()

    # ----- Azioni: stato, assegnazione, urgenza, note ----------------- #
    operatori = _carica_operatori_segreteria()
    nomi_operatori = ["— Non assegnata —"] + [n for _, n in operatori]
    id_per_nome = {n: oid for oid, n in operatori}

    with st.form(f"azioni_{pratica_id}"):
        st.markdown("#### Aggiorna pratica")
        ca, cb = st.columns(2)
        with ca:
            stati_lista = list(_STATI.keys())
            stato_corrente = label_stato(det["stato"])
            nuovo_stato = st.selectbox(
                "Stato", stati_lista, index=stati_lista.index(stato_corrente)
            )
            urgenze_lista = list(_URGENZE.keys())
            urgenza_corrente = label_urgenza(det["urgenza"])
            nuova_urgenza = st.selectbox(
                "Urgenza", urgenze_lista, index=urgenze_lista.index(urgenza_corrente)
            )
        with cb:
            assegn_corrente = det["assegnato"] or "— Non assegnata —"
            idx = nomi_operatori.index(assegn_corrente) if assegn_corrente in nomi_operatori else 0
            nuovo_assegn = st.selectbox("Assegna a", nomi_operatori, index=idx)

        salva = st.form_submit_button("💾 Salva modifiche", type="primary", use_container_width=True)

    if salva:
        try:
            with get_session() as session:
                pratica_service.aggiorna_stato(session, pratica_id, _STATI[nuovo_stato])
                pratica_service.aggiorna_urgenza(session, pratica_id, _URGENZE[nuova_urgenza])
                op_id = None if nuovo_assegn == "— Non assegnata —" else id_per_nome[nuovo_assegn]
                pratica_service.assegna_operatore(session, pratica_id, op_id)
            st.success("Modifiche salvate.")
            st.rerun()
        except Exception as e:  # pragma: no cover
            st.error(f"Errore durante il salvataggio: {e}")

    st.divider()
    st.markdown("#### Elimina pratica")
    chiave_confirm = f"confirm_elimina_{pratica_id}"
    if not st.session_state.get(chiave_confirm):
        if st.button("🗑️ Elimina pratica", type="secondary", use_container_width=True, key=f"btn_elimina_{pratica_id}"):
            st.session_state[chiave_confirm] = True
            st.rerun()
    else:
        st.warning(
            f"Stai per eliminare definitivamente la pratica **{det['numero']}** "
            "e tutti i documenti allegati. L'operazione è irreversibile."
        )
        col_si, col_no = st.columns(2)
        with col_si:
            if st.button("✅ Sì, elimina", type="primary", use_container_width=True, key=f"btn_si_{pratica_id}"):
                try:
                    with get_session() as session:
                        pratica_service.elimina_pratica(session, pratica_id)
                    st.session_state.pop(chiave_confirm, None)
                    st.success(f"Pratica {det['numero']} eliminata.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante l'eliminazione: {e}")
        with col_no:
            if st.button("❌ Annulla", use_container_width=True, key=f"btn_no_{pratica_id}"):
                st.session_state.pop(chiave_confirm, None)
                st.rerun()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def render() -> None:
    setup_page("Segreteria · Gestione Pratiche", "📋")
    st.title("📋 Segreteria — Gestione Pratiche")
    st.caption("Visualizza, filtra, assegna e lavora le pratiche come ticket.")

    _dashboard()
    st.divider()

    filtri = _sidebar_filtri()
    with get_session() as session:
        pratiche = pratica_service.cerca_pratiche(session, filtri)
        records = [_to_record(p) for p in pratiche]

    attive = [r for r in records if r["stato"] in (
        StatoPratica.NUOVA.value, StatoPratica.IN_LAVORAZIONE.value
    )]
    completate = [r for r in records if r["stato"] == StatoPratica.COMPLETATA.value]

    sezione(f"Da lavorare / In lavorazione ({len(attive)})")
    _tabella(attive)
    st.divider()
    sezione(f"Completate ({len(completate)})")
    _tabella(completate)
    st.divider()
    _pannello_dettaglio(records)


if __name__ == "__main__":
    render()
