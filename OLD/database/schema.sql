-- =====================================================================
-- Schema del database (riferimento, generato dai modelli ORM).
-- Lo schema effettivo viene creato da: python -m database.init_db
-- Motore: SQLite. I tipi sono quelli emessi da SQLAlchemy per SQLite.
-- =====================================================================

CREATE TABLE clienti (
	id INTEGER NOT NULL, 
	nome VARCHAR(200) NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	codice_fiscale VARCHAR(16), 
	partita_iva VARCHAR(11), 
	email VARCHAR(180), 
	telefono VARCHAR(40), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE operatori (
	id INTEGER NOT NULL, 
	nome VARCHAR(120) NOT NULL, 
	email VARCHAR(180), 
	ruolo VARCHAR(20) NOT NULL, 
	attivo BOOLEAN NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE TABLE pratiche (
	id INTEGER NOT NULL, 
	numero_pratica VARCHAR(30) NOT NULL, 
	cliente_id INTEGER NOT NULL, 
	broker_id INTEGER NOT NULL, 
	operatore_assegnato_id INTEGER, 
	gia_cliente BOOLEAN NOT NULL, 
	compagnia VARCHAR(80) NOT NULL, 
	tipo_polizza VARCHAR(30) NOT NULL, 
	emissione_polizza BOOLEAN NOT NULL, 
	n_polizza VARCHAR(60), 
	n_preventivo VARCHAR(60), 
	data_decorrenza DATE, 
	importo_polizza NUMERIC(12, 2), 
	importo_cliente NUMERIC(12, 2), 
	gia_pagato BOOLEAN NOT NULL, 
	incasso BOOLEAN, 
	metodo_pagamento VARCHAR(40), 
	invia_mail BOOLEAN, 
	urgenza VARCHAR(10) NOT NULL, 
	stato VARCHAR(20) NOT NULL, 
	note TEXT, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (numero_pratica), 
	FOREIGN KEY(cliente_id) REFERENCES clienti (id), 
	FOREIGN KEY(broker_id) REFERENCES operatori (id), 
	FOREIGN KEY(operatore_assegnato_id) REFERENCES operatori (id)
);

CREATE TABLE documenti (
	id INTEGER NOT NULL, 
	pratica_id INTEGER NOT NULL, 
	tipo_documento VARCHAR(40) NOT NULL, 
	nome_file VARCHAR(255) NOT NULL, 
	percorso VARCHAR(500), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pratica_id) REFERENCES pratiche (id) ON DELETE CASCADE
);

