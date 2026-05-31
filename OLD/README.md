# Gestionale Pratiche Assicurative per Broker

Piattaforma interna per la gestione delle pratiche assicurative, con due interfacce web:

- **Broker** — inserimento di nuove pratiche (form dinamico che ricalca il flusso operativo).
- **Segreteria** — gestione delle pratiche come **sistema di ticket**: elenco, filtri, ordinamenti, assegnazione agli operatori, aggiornamento dello stato.

Stack: **Python + Streamlit** (UI) + **SQLAlchemy 2.0** (ORM) + **SQLite** (persistenza). Nessun framework pesante.

---

## 1. Architettura

Il progetto segue una separazione a livelli chiara: la UI non parla mai direttamente con il database, ma passa sempre dai *service*, che a loro volta usano i *model* ORM. Questo rende il codice testabile, leggibile ed estendibile (es. sostituire SQLite con PostgreSQL = cambiare una sola riga in `utils/config.py`).

```
┌─────────────────────────────────────────────┐
│  UI  (Streamlit)   Home.py + pages/ + app/   │  ← presentazione
├─────────────────────────────────────────────┤
│  Services          services/                 │  ← logica di business
├─────────────────────────────────────────────┤
│  Models (ORM)      models/                    │  ← entità di dominio
├─────────────────────────────────────────────┤
│  Database          database/ (SQLAlchemy)     │  ← connessione/persistenza
└─────────────────────────────────────────────┘
        utils/  = configurazione, validazione, formattazione (trasversale)
```

### Ruolo di ogni modulo

| Cartella / file | Ruolo |
|---|---|
| `Home.py` | Entry point Streamlit (landing page multipagina). |
| `pages/1_Broker.py`, `pages/2_Segreteria.py` | Pagine sottili: importano e invocano la logica in `app/`. |
| `app/ui_common.py` | Helper UI condivisi: bootstrap del path, config pagina, CSS, componenti. |
| `app/broker/broker_app.py` | Form di inserimento pratica (campi condizionali secondo il flusso). |
| `app/segreteria/segreteria_app.py` | Dashboard, filtri, tabella ticket, pannello di dettaglio e azioni. |
| `models/` | Entità ORM: `Operatore`, `Cliente`, `Pratica`, `Documento`. |
| `services/` | Logica di business e accesso ai dati (creazione, ricerca, aggiornamenti). |
| `database/connection.py` | Engine, sessioni, `Base` dichiarativa, context manager `get_session()`. |
| `database/init_db.py` | Creazione tabelle + dati di esempio (`--reset` per ripartire da zero). |
| `database/schema.sql` | DDL di riferimento (generato dai modelli). |
| `utils/config.py` | Percorsi, enum di dominio, liste controllate (compagnie, metodi pagamento). |
| `utils/validators.py` | Regole di validazione derivate dal diagramma di flusso. |
| `utils/formatting.py` | Formattazione valuta/date, badge ed etichette per la UI. |
| `tests/` | Test (pytest) di service e validazione, su DB in memoria isolato. |
| `data/` | Database SQLite e file caricati (non versionato). |

### Modello dati

Quattro entità collegate:

- **operatori** — utenti del sistema (`ruolo`: broker o segreteria).
- **clienti** — persone fisiche o aziende.
- **pratiche** — entità centrale (il "ticket"); FK verso cliente, broker e operatore assegnato; contiene tutti i campi del flusso + `stato` e `urgenza`.
- **documenti** — allegati (fronte/retro) collegati alla pratica.

Il file `database/schema.sql` contiene il DDL completo.

### Logica del flusso (dal diagramma)

I campi mostrati e richiesti seguono le diramazioni del diagramma, implementate in `utils/validators.py`:

- **Polizza emessa?** Sì → numero polizza · No → numero preventivo + data decorrenza.
- **Già pagato?** Sì → metodo di pagamento · No → incassato? → se no, inviare mail al cliente?
- **Nuovo cliente** → richiesti i documenti (identità + Codice Fiscale; Visura se azienda; Libretto se Auto).
- **Urgenza** (bassa/alta) = priorità del ticket.

---

## 2. Avvio rapido (terminale)

```bash
# 1. (consigliato) ambiente virtuale
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. dipendenze
pip install -r requirements.txt

# 3. inizializza il database con dati di esempio
python -m database.init_db

# 4. avvia l'app
streamlit run Home.py
```

Si apre il browser su `http://localhost:8501`. Usa il menu a sinistra per passare tra **Broker** e **Segreteria**.

Per ripartire da un database pulito: `python -m database.init_db --reset`.

---

## 3. Esecuzione in PyCharm (passo passo)

1. **Apri il progetto**: `File ▸ Open` → seleziona la cartella `gestionale_broker`.
2. **Interprete / venv**: `File ▸ Settings ▸ Project ▸ Python Interpreter` → `Add Interpreter ▸ Add Local Interpreter ▸ Virtualenv ▸ New`. PyCharm crea il `.venv`.
3. **Installa le dipendenze**: apri il terminale integrato (in basso) e lancia
   `pip install -r requirements.txt`. (In alternativa PyCharm propone l'installazione aprendo `requirements.txt`.)
4. **Inizializza il DB**: nel terminale integrato → `python -m database.init_db`.
5. **Crea la run configuration per Streamlit**:
   - `Run ▸ Edit Configurations… ▸ + ▸ Python`.
   - **Name**: `Streamlit`.
   - Imposta **module** (non *script*): clicca l'icona a destra del campo e scegli *module name* → `streamlit`.
   - **Parameters**: `run Home.py`.
   - **Working directory**: la root del progetto (`…/gestionale_broker`).
   - Interprete: il `.venv` del progetto. Salva.
6. **Avvia**: premi ▶︎ sulla configurazione `Streamlit`. PyCharm mostra l'URL `http://localhost:8501`.
7. **Test** (opzionale): tasto destro sulla cartella `tests` → `Run 'pytest in tests'`. PyCharm rileva pytest automaticamente.

> Suggerimento: se i tasti ▶︎ accanto a `run Home.py` non funzionano (Streamlit non è un normale script Python), usa **sempre** la configurazione "module: streamlit" del punto 5.

---

## 4. Test

```bash
pytest -q
```

I test coprono: validazione del flusso, generazione del numero pratica, riuso del cliente, ordinamento per priorità, filtri per stato, assegnazione (che porta automaticamente la pratica "in lavorazione") e aggiornamento dello stato. Girano su un database SQLite **in memoria**, senza toccare quello reale.

---

## 5. Estendere il progetto

- **Nuova compagnia / metodo di pagamento**: aggiungi una voce in `utils/config.py`.
- **Nuovo campo della pratica**: aggiungi la colonna nel modello `models/pratica.py`, gestiscila nel form (`broker_app.py`) e nel dettaglio (`segreteria_app.py`), poi `python -m database.init_db --reset`.
- **Autenticazione / ruoli reali**: il modello `Operatore` ha già il campo `ruolo`; si può innestare un login (es. `streamlit-authenticator`).
- **Database di produzione**: cambia `DB_URL` in `utils/config.py` (es. PostgreSQL) e installa il driver; il resto del codice non cambia.

---

## 6. Struttura del progetto

```
gestionale_broker/
├── Home.py                      # entry point Streamlit
├── pages/
│   ├── 1_Broker.py
│   └── 2_Segreteria.py
├── app/
│   ├── ui_common.py
│   ├── broker/broker_app.py
│   └── segreteria/segreteria_app.py
├── models/
│   ├── operatore.py · cliente.py · pratica.py · documento.py
├── services/
│   ├── operatore_service.py · cliente_service.py
│   ├── pratica_service.py · documento_service.py
├── database/
│   ├── connection.py · init_db.py · schema.sql
├── utils/
│   ├── config.py · validators.py · formatting.py
├── tests/
│   └── test_services.py
├── data/                        # DB SQLite + upload (non versionato)
├── requirements.txt
└── README.md
```
