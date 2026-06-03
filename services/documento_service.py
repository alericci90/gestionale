"""Service per la gestione dei documenti allegati a una pratica."""
from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Documento
from utils.config import SUPABASE_BUCKET, SUPABASE_KEY, SUPABASE_URL, UPLOAD_DIR, TipoDocumento

_IMMAGINI = {".jpg", ".jpeg", ".png"}
_MAX_LATO = 1000  # pixel
_JPEG_QUALITY = 80


def _comprimi_se_immagine(nome_file: str, contenuto: bytes) -> Tuple[str, bytes]:
    """Ridimensiona e comprime le immagini a max 1000px sul lato lungo.

    PDF e file non-immagine vengono restituiti invariati.
    PNG viene convertito in JPEG per ridurre ulteriormente le dimensioni.
    """
    estensione = Path(nome_file).suffix.lower()
    if estensione not in _IMMAGINI:
        return nome_file, contenuto
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(contenuto))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > _MAX_LATO:
            scala = _MAX_LATO / max(w, h)
            img = img.resize((int(w * scala), int(h * scala)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        # Se era PNG aggiorna l'estensione del nome file
        nuovo_nome = Path(nome_file).stem + ".jpg" if estensione == ".png" else nome_file
        return nuovo_nome, buf.getvalue()
    except Exception:
        return nome_file, contenuto


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


def elimina_file_cloud(url: str) -> None:
    """Elimina un file da Supabase Storage dato il suo URL pubblico."""
    try:
        marker = f"/object/public/{SUPABASE_BUCKET}/"
        idx = url.find(marker)
        if idx == -1:
            return
        percorso = url[idx + len(marker):]
        _client_supabase().storage.from_(SUPABASE_BUCKET).remove([percorso])
    except Exception:
        pass


def salva_file(nome_file: str, contenuto: bytes) -> str:
    """Salva il file e ritorna il riferimento (percorso locale o URL cloud)."""
    nome_file, contenuto = _comprimi_se_immagine(nome_file, contenuto)
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

def salva_temp_file(sid: str, tipo: str, nome_file: str, contenuto: bytes) -> str:
    """Salva file temporaneo su Supabase Storage per upload mobile. Ritorna URL pubblico."""
    nome_file, contenuto = _comprimi_se_immagine(nome_file, contenuto)
    estensione = Path(nome_file).suffix or ".jpg"
    percorso = f"temp/{sid}/{tipo}__{uuid.uuid4().hex}{estensione}"
    client = _client_supabase()
    client.storage.from_(SUPABASE_BUCKET).upload(
        path=percorso,
        file=contenuto,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )
    return client.storage.from_(SUPABASE_BUCKET).get_public_url(percorso)


def lista_temp_files(sid: str) -> list[dict]:
    """Lista i file caricati dal telefono per questa sessione."""
    try:
        client = _client_supabase()
        files = client.storage.from_(SUPABASE_BUCKET).list(f"temp/{sid}")
        result = []
        for f in (files or []):
            nome = f["name"]
            url = client.storage.from_(SUPABASE_BUCKET).get_public_url(f"temp/{sid}/{nome}")
            tipo = nome.split("__")[0] if "__" in nome else "documento"
            result.append({"tipo": tipo, "url": url, "nome": nome})
        return result
    except Exception:
        return []


def aggiungi_documento(
    session: Session,
    pratica_id: int,
    tipo_documento: TipoDocumento,
    nome_file: str,
    contenuto: Optional[bytes] = None,
    percorso: Optional[str] = None,
) -> Documento:
    if contenuto is not None and percorso is None:
        percorso = salva_file(nome_file, contenuto)
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
