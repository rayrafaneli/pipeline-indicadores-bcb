"""Carga: grava o modelo estrela no DuckDB e cria as views analíticas consumidas pelo painel."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

VIEWS = """
CREATE OR REPLACE VIEW vw_serie AS
SELECT t.data, t.ano, t.mes, t.mes_ano, i.indicador_id, i.nome, i.unidade, i.tema, f.valor
FROM fato_indicador_mensal f
JOIN dim_tempo t USING (tempo_id)
JOIN dim_indicador i USING (indicador_id);

-- último valor de cada indicador e variação contra 12 meses antes
CREATE OR REPLACE VIEW vw_kpis AS
WITH base AS (
    SELECT *, row_number() OVER (PARTITION BY indicador_id ORDER BY data DESC) AS rn
    FROM vw_serie
)
SELECT a.indicador_id, a.nome, a.unidade, a.tema, a.data, a.mes_ano, a.valor,
       b.valor AS valor_12m_antes,
       a.valor - b.valor AS variacao_12m
FROM base a
LEFT JOIN vw_serie b
  ON b.indicador_id = a.indicador_id AND b.data = a.data - INTERVAL 12 MONTH
WHERE a.rn = 1;

-- juro real ex-post: Selic de fim de mês menos IPCA acumulado em 12 meses
CREATE OR REPLACE VIEW vw_juro_real AS
SELECT s.data, s.mes_ano, s.valor AS selic, i.valor AS ipca_12m, s.valor - i.valor AS juro_real
FROM vw_serie s
JOIN vw_serie i ON i.data = s.data AND i.indicador_id = 13522
WHERE s.indicador_id = 432;
"""


def carregar(tabelas: dict[str, pd.DataFrame], banco: Path) -> None:
    banco.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(banco)) as con:
        for nome, df in tabelas.items():
            con.register("df_tmp", df)
            con.execute(f"CREATE OR REPLACE TABLE {nome} AS SELECT * FROM df_tmp")
            con.unregister("df_tmp")
        con.execute("ALTER TABLE dim_tempo ADD PRIMARY KEY (tempo_id)")
        con.execute("ALTER TABLE dim_indicador ADD PRIMARY KEY (indicador_id)")
        con.execute(VIEWS)
