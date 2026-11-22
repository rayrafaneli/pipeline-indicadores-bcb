"""Transformação: séries brutas -> granularidade mensal -> modelo estrela (dim_tempo, dim_indicador, fato)."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from .config import Serie

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def para_mensal(registros: list[dict], agregacao: str) -> pd.Series:
    """Converte a série (diária ou mensal) para um valor por mês (índice = 1º dia do mês)."""
    if not registros:
        return pd.Series(dtype="float64")
    df = pd.DataFrame(registros)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    s = df.dropna().drop_duplicates("data").set_index("data")["valor"].sort_index()
    mensal = s.resample("MS")
    return (mensal.last() if agregacao == "ultimo" else mensal.mean()).dropna()


def dim_tempo(inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    meses = pd.date_range(inicio, fim, freq="MS")
    return pd.DataFrame({
        "tempo_id": meses.year * 100 + meses.month,
        "data": meses.date,
        "ano": meses.year,
        "mes": meses.month,
        "trimestre": (meses.month - 1) // 3 + 1,
        "mes_ano": [f"{MESES[d.month - 1]}/{d.year}" for d in meses],
    })


def dim_indicador(series: list[Serie]) -> pd.DataFrame:
    return pd.DataFrame([{
        "indicador_id": s.codigo, "nome": s.nome, "unidade": s.unidade, "frequencia": s.frequencia,
        "agregacao_mensal": s.agregacao, "tema": s.tema, "fonte": "Banco Central do Brasil · SGS",
    } for s in series])


def modelo_estrela(brutos: dict[Serie, list[dict]]) -> dict[str, pd.DataFrame]:
    partes = []
    for serie, registros in brutos.items():
        m = para_mensal(registros, serie.agregacao)
        partes.append(pd.DataFrame({
            "tempo_id": m.index.year * 100 + m.index.month,
            "indicador_id": serie.codigo,
            "valor": m.values.round(4),
        }))
    fato = pd.concat(partes, ignore_index=True)
    fato["carregado_em"] = datetime.now().replace(microsecond=0)
    tempos = pd.to_datetime(fato["tempo_id"].astype(str), format="%Y%m")
    return {
        "dim_tempo": dim_tempo(tempos.min(), tempos.max()),
        "dim_indicador": dim_indicador(list(brutos)),
        "fato_indicador_mensal": fato.sort_values(["indicador_id", "tempo_id"]).reset_index(drop=True),
    }
