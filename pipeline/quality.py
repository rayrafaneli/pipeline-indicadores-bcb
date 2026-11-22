"""Checagens de qualidade executadas no fim de cada carga. Falha a execução se algo crítico quebrar."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

CHECKS = {
    "fato sem valores nulos":
        "SELECT count(*) FROM fato_indicador_mensal WHERE valor IS NULL",
    "uma linha por indicador e mês":
        "SELECT count(*) FROM (SELECT tempo_id, indicador_id FROM fato_indicador_mensal GROUP BY ALL HAVING count(*) > 1)",
    "toda chave de tempo existe na dimensão":
        "SELECT count(*) FROM fato_indicador_mensal f ANTI JOIN dim_tempo t USING (tempo_id)",
    "todo indicador existe na dimensão":
        "SELECT count(*) FROM fato_indicador_mensal f ANTI JOIN dim_indicador i USING (indicador_id)",
}


def validar(banco: Path, meses_min: int = 60, defasagem_max_meses: int = 4) -> list[str]:
    erros = []
    with duckdb.connect(str(banco), read_only=True) as con:
        for nome, sql in CHECKS.items():
            n = con.execute(sql).fetchone()[0]
            if n:
                erros.append(f"{nome}: {n} violações")
        for nome, meses, ultimo in con.execute(
                "SELECT nome, count(*), max(data) FROM vw_serie GROUP BY nome").fetchall():
            if meses < meses_min:
                erros.append(f"{nome}: só {meses} meses de histórico")
            hoje = date.today()
            defasagem = (hoje.year - ultimo.year) * 12 + hoje.month - ultimo.month
            if defasagem > defasagem_max_meses:
                erros.append(f"{nome}: último dado em {ultimo:%m/%Y} ({defasagem} meses atrás)")
    return erros
