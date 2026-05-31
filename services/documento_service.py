"""Service per la gestione dei documenti allegati a una pratica."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Documento
from utils.config import SUPABASE_BUCKET, SUPABASE_KEY, SUPABASE_URL, UPLOAD_DIR, TipoDocumento


# --------------------------------------------------------------------------- #
# Storage: locale o Supabase Storage
# --------------------------------------------------------------------------- #

def _usa_cloud() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _client_supabase():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def salva_file_su_disco(nome_file: str, contenuto: bytes) -> str:
    estensione = Path(nome_file).suffix
    nome_univoco = f"{uuid.uuid4().hex}{estensione}"
    percorso = UPLOAD_DIR / nome_univoco
    percorso.write_bytes(contenuto)
    return str(percorso)


def _salva_su_supabase(nome_file: str, contenuto: bytes) -> str:
    estensione = Path(nome_file).suffix
    nome_univoco = f"{uuid.uuid4().hex}{estensione}"
    client = _client_supabase()
    client.storage.from_(SUPABASE_BUCKET).upload(
        path=nome_univoco,
        file=contenuto,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )
    return client.storage.from_(SUPABASE_BUCKET).get_public_url(nome_univoco)


def salva_file(nome_file: str, contenuto: bytes) -> str:
    """Salva il file e ritorna il riferimento (percorso locale o URL cloud)."""
    if _usa_cloud():
        return _salva_su_supabase(nome_file, contenuto)
    return salva_file_su_disco(nome_file, contenuto)


def leggi_file(riferimento: str) -> Optional[bytes]:
    """Legge il contenuto del file dal riferimento (percorso locale o URL cloud)."""
    if riferimento.startswith("http"):
        import urllib.request
        try:
            with urllib.request.urlopen(riferimento) as resp:
                return resp.read()
        except Exception:
            return None
    p = Path(riferimento)
    return p.read_bytes() if p.exists() else None


# --------------------------------------------------------------------------- #
# CRUD documenti
# --------------------------------------------------------------------------- #

def aggiungi_documento(
    session: Session,
    pratica_id: int,
    tipo_documento: TipoDocumento,
    nome_file: str,
    contenuto: Optional[bytes] = None,
) -> Documento:
    percorso = salva_file(nome_file, contenuto) if contenuto else None
    doc = Documento(
        pratica_id=pratica_id,
        tipo_documento=tipo_documento.value,
        nome_file=nome_file,
        percorso=percorso,
    )
    session.add(doc)
    session.flush()
    return doc


def lista_documenti(session: Session, pratica_id: int) -> List[Documento]:
    stmt = (
        select(Documento)
        .where(Documento.pratica_id == pratica_id)
        .order_by(Documento.created_at)
    )
    return list(session.scalars(stmt))
