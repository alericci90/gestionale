"""
Package dei modelli ORM.

Importare i modelli da qui garantisce che tutte le classi siano registrate
sulla stessa `Base` prima della creazione delle tabelle.
"""
from models.cliente import Cliente
from models.documento import Documento
from models.operatore import Operatore
from models.pratica import Pratica

__all__ = ["Cliente", "Documento", "Operatore", "Pratica"]
