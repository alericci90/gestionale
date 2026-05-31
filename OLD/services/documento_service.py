"""Service per la gestione dei documenti allegati a una pratica."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Documento
from utils.config import UPLOAD_DIR, TipoDocumento


def salva_file_su_disco(nome_file: str, contenuto: bytes) -> str:
    """
    Salva i byte di un file caricato dentro data/uploads con un nome univoco.
    Ritorna il percorso relativo come stringa.
    """
    estensione = Path(nome_file).suffix
    nome_univoco = f"{uuid.uuid4().hex}{estensione}"
    percorso = UPLOAD_DIR / nome_univoco
    percorso.write_bytes(contenuto)
    return str(percorso)


def aggiungi_documento(
    session: Session,
    pratica_id: int,
    tipo_documento: TipoDocumento,
    nome_file: str,
    contenuto: Optional[bytes] = None,
) -> Documento:
    percorso = salva_file_su_disco(nome_file, contenuto) if contenuto else None
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
