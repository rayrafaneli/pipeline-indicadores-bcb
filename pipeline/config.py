"""Séries do Sistema Gerenciador de Séries Temporais (SGS) do Banco Central usadas no pipeline."""
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
BANCO = RAIZ / "data" / "indicadores.duckdb"
INICIO = date(2015, 1, 1)
API = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"


@dataclass(frozen=True)
class Serie:
    codigo: int
    nome: str
    unidade: str
    frequencia: str      # "diária" | "mensal"
    agregacao: str       # como vira mensal: "ultimo" (valor de fim de mês) | "media"
    tema: str


SERIES = [
    Serie(432, "Selic (meta)", "% a.a.", "diária", "ultimo", "Juros"),
    Serie(13522, "IPCA 12 meses", "%", "mensal", "ultimo", "Inflação"),
    Serie(433, "IPCA mensal", "%", "mensal", "ultimo", "Inflação"),
    Serie(1, "Dólar (venda)", "R$", "diária", "media", "Câmbio"),
    Serie(24369, "Desocupação", "%", "mensal", "ultimo", "Atividade"),
    Serie(24364, "IBC-Br", "índice", "mensal", "ultimo", "Atividade"),
]
