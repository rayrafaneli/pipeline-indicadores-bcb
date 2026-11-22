"""Orquestra o pipeline: extração (API SGS) -> transformação (modelo estrela) -> carga (DuckDB) -> qualidade.

Uso: python run.py
"""
import logging
import sys
import time

from pipeline.config import BANCO, SERIES
from pipeline.extract import extrair
from pipeline.load import carregar
from pipeline.quality import validar
from pipeline.transform import modelo_estrela

log = logging.getLogger("pipeline")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    t0 = time.perf_counter()
    log.info("extração · %d séries do SGS/BCB", len(SERIES))
    brutos = {s: extrair(s) for s in SERIES}

    log.info("transformação · modelo estrela mensal")
    tabelas = modelo_estrela(brutos)
    for nome, df in tabelas.items():
        log.info("  %-22s %6d linhas", nome, len(df))

    log.info("carga · %s", BANCO.name)
    carregar(tabelas, BANCO)

    erros = validar(BANCO)
    for e in erros:
        log.error("qualidade · %s", e)
    log.info("fim em %.1f s · %s", time.perf_counter() - t0, "OK" if not erros else f"{len(erros)} erro(s)")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
