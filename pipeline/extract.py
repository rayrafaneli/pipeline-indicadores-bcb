"""Extração: baixa as séries da API do SGS em janelas (a API limita séries diárias a 10 anos por consulta)."""
from __future__ import annotations

import json
import logging
import time
from datetime import date, timedelta

import requests

from .config import API, INICIO, RAW, Serie

log = logging.getLogger(__name__)
JANELA_ANOS = 5


def janelas(inicio: date, fim: date, anos: int = JANELA_ANOS) -> list[tuple[date, date]]:
    """Quebra [inicio, fim] em janelas de até `anos` anos, sem sobreposição."""
    out, atual = [], inicio
    while atual <= fim:
        prox = date(atual.year + anos, atual.month, atual.day) - timedelta(days=1)
        out.append((atual, min(prox, fim)))
        atual = min(prox, fim) + timedelta(days=1)
    return out


def _get(url: str, params: dict, tentativas: int = 4) -> list[dict]:
    for i in range(1, tentativas + 1):
        try:
            r = requests.get(url, params=params, timeout=60, headers={"Accept": "application/json"})
            if r.status_code == 404:
                return []
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            if i == tentativas:
                raise
            espera = 2 ** i
            log.warning("falha (%s), nova tentativa em %ss", e.__class__.__name__, espera)
            time.sleep(espera)
    return []


def extrair(serie: Serie, fim: date | None = None) -> list[dict]:
    fim = fim or date.today()
    registros: list[dict] = []
    for a, b in janelas(INICIO, fim):
        registros += _get(API.format(codigo=serie.codigo),
                          {"formato": "json", "dataInicial": f"{a:%d/%m/%Y}", "dataFinal": f"{b:%d/%m/%Y}"})
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{serie.codigo}.json").write_text(json.dumps(registros), encoding="utf-8")
    log.info("%-14s %6d registros", serie.nome, len(registros))
    return registros
