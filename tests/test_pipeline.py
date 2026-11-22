import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.config import Serie  # noqa: E402
from pipeline.extract import janelas  # noqa: E402
from pipeline.load import carregar  # noqa: E402
from pipeline.quality import validar  # noqa: E402
from pipeline.transform import modelo_estrela, para_mensal  # noqa: E402

SELIC = Serie(432, "Selic (meta)", "% a.a.", "diária", "ultimo", "Juros")
IPCA12 = Serie(13522, "IPCA 12 meses", "%", "mensal", "ultimo", "Inflação")
DOLAR = Serie(1, "Dólar (venda)", "R$", "diária", "media", "Câmbio")


def test_janelas_cobrem_periodo_sem_sobreposicao():
    js = janelas(date(2015, 1, 1), date(2026, 11, 21), anos=5)
    assert js[0][0] == date(2015, 1, 1) and js[-1][1] == date(2026, 11, 21)
    for (_, fim), (ini, _) in zip(js, js[1:]):
        assert (ini - fim).days == 1


def test_mensal_por_ultimo_e_por_media():
    regs = [{"data": "01/01/2025", "valor": "10"}, {"data": "31/01/2025", "valor": "12"},
            {"data": "15/02/2025", "valor": "13"}]
    assert list(para_mensal(regs, "ultimo")) == [12.0, 13.0]
    assert list(para_mensal(regs, "media")) == [11.0, 13.0]


def test_mensal_ignora_valor_invalido_e_vazio():
    assert para_mensal([], "media").empty
    regs = [{"data": "01/01/2025", "valor": ""}, {"data": "02/01/2025", "valor": "5.5"}]
    assert list(para_mensal(regs, "media")) == [5.5]


@pytest.fixture
def brutos():
    meses = [f"01/{m:02d}/{a}" for a in range(2020, 2027) for m in range(1, 13)][:83]
    return {
        SELIC: [{"data": d, "valor": "10.75"} for d in meses],
        IPCA12: [{"data": d, "valor": "4.5"} for d in meses],
        DOLAR: [{"data": d, "valor": "5.1"} for d in meses],
    }


def test_modelo_estrela(brutos):
    t = modelo_estrela(brutos)
    assert set(t) == {"dim_tempo", "dim_indicador", "fato_indicador_mensal"}
    assert len(t["fato_indicador_mensal"]) == 3 * 83
    assert t["dim_tempo"]["tempo_id"].is_unique
    assert set(t["fato_indicador_mensal"]["tempo_id"]) <= set(t["dim_tempo"]["tempo_id"])


def test_carga_views_e_qualidade(brutos, tmp_path):
    banco = tmp_path / "t.duckdb"
    carregar(modelo_estrela(brutos), banco)
    with duckdb.connect(str(banco), read_only=True) as con:
        real = con.execute("SELECT juro_real FROM vw_juro_real LIMIT 1").fetchone()[0]
        kpi = con.execute("SELECT count(*) FROM vw_kpis").fetchone()[0]
    assert real == pytest.approx(6.25) and kpi == 3
    erros = validar(banco, meses_min=60, defasagem_max_meses=1000)
    assert erros == []
