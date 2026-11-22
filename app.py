"""Painel de indicadores econômicos (Streamlit) lendo o modelo estrela do DuckDB, no visual de um relatório Power BI.

Uso: streamlit run app.py   (rode antes: python run.py)
"""
import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.config import BANCO

st.set_page_config(page_title="Indicadores BCB", page_icon="📊", layout="wide")

AMARELO, AZUL, LARANJA, ROXO, ROSA = "#F2C811", "#118DFF", "#E66C37", "#744EC2", "#E044A7"
st.markdown(f"""
<style>
  .stApp {{ background:#161514; }}
  header[data-testid="stHeader"] {{ background:transparent; }}
  .block-container {{ padding-top:1.4rem; max-width:1500px; }}
  .topo {{ display:flex; align-items:center; gap:14px; background:#252423; border:1px solid #3B3A39;
          border-radius:8px; padding:12px 18px; margin-bottom:14px; }}
  .logo span {{ display:inline-block; width:6px; margin-right:3px; border-radius:2px; background:{AMARELO}; vertical-align:bottom; }}
  .topo h1 {{ font-size:20px; margin:0; color:#F3F2F1; font-weight:700; }}
  .topo p {{ margin:0; color:#A19F9D; font-size:13px; }}
  .cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:6px; }}
  .card {{ background:#252423; border:1px solid #3B3A39; border-top:3px solid var(--c); border-radius:6px; padding:16px 18px; }}
  .card .v {{ font-size:32px; font-weight:800; color:#F3F2F1; line-height:1.1; }}
  .card .n {{ font-size:13px; color:#D2D0CE; font-weight:600; margin-top:6px; }}
  .card .d {{ font-size:12px; margin-top:4px; }}
  .stTabs [data-baseweb="tab-list"] {{ gap:6px; }}
  .stTabs [data-baseweb="tab"] {{ background:#252423; border-radius:6px 6px 0 0; padding:8px 18px; color:#A19F9D; }}
  .stTabs [aria-selected="true"] {{ color:#F3F2F1 !important; background:#2D2C2B; }}
  .stTabs [data-baseweb="tab-highlight"] {{ background:{AMARELO}; }}
</style>""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def dados():
    with duckdb.connect(str(BANCO), read_only=True) as con:
        serie = con.execute("SELECT * FROM vw_serie ORDER BY data").df()
        kpis = con.execute("SELECT * FROM vw_kpis").df().set_index("indicador_id")
        juro = con.execute("SELECT * FROM vw_juro_real ORDER BY data").df()
    return serie, kpis, juro


serie, kpis, juro = dados()
ultimo = serie["data"].max()


def br(v, casas=2):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def card(cod, cor, casas=2, prefixo="", sufixo=""):
    k = kpis.loc[cod]
    d = k["variacao_12m"]
    seta, cor_d = ("▲", "#F28B8B") if d > 0 else ("▼", "#6CC995")
    if cod in (24364,):  # para atividade, subir é bom
        cor_d = "#6CC995" if d > 0 else "#F28B8B"
    return (f'<div class="card" style="--c:{cor}"><div class="v">{prefixo}{br(k["valor"], casas)}{sufixo}</div>'
            f'<div class="n">{k["nome"]} · {k["mes_ano"]}</div>'
            f'<div class="d" style="color:{cor_d}">{seta} {br(abs(d), casas)} em 12 meses</div></div>')


def layout(fig, h=360, titulo=""):
    fig.update_layout(
        title=dict(text=titulo, x=0.01, font=dict(size=15, color="#F3F2F1")), height=h,
        paper_bgcolor="#252423", plot_bgcolor="#252423", font=dict(color="#D2D0CE", family="Segoe UI"),
        margin=dict(l=40, r=20, t=50, b=30), legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
        xaxis=dict(gridcolor="#302F2E", showline=False), yaxis=dict(gridcolor="#302F2E", zeroline=False),
        hovermode="x unified")
    return fig


def linha(cod, cor, nome=None):
    s = serie[serie["indicador_id"] == cod]
    return go.Scatter(x=s["data"], y=s["valor"], name=nome or s["nome"].iloc[0], mode="lines",
                      line=dict(color=cor, width=2.6))


st.markdown(f"""<div class="topo"><div class="logo"><span style="height:12px"></span><span style="height:18px"></span>
<span style="height:24px"></span></div><div><h1>Indicadores econômicos do Brasil</h1>
<p>Pipeline ETL · API SGS do Banco Central → modelo estrela no DuckDB · dados até {ultimo:%m/%Y}</p></div></div>""",
            unsafe_allow_html=True)
st.markdown('<div class="cards">' + card(432, AMARELO, sufixo="%") + card(13522, AZUL, sufixo="%")
            + card(1, LARANJA, casas=2, prefixo="R$ ") + card(24369, ROXO, casas=1, sufixo="%") + "</div>",
            unsafe_allow_html=True)

aba1, aba2, aba3 = st.tabs(["Visão geral", "Juros & inflação", "Câmbio & atividade"])

with aba1:
    c1, c2 = st.columns([3, 2])
    fig = go.Figure([linha(432, AMARELO), linha(13522, AZUL)])
    c1.plotly_chart(layout(fig, titulo="Selic × IPCA 12 meses (%)"), width="stretch")
    ipca = serie[(serie["indicador_id"] == 433) & (serie["data"] >= ultimo - pd.DateOffset(months=23))]
    fig = go.Figure(go.Bar(x=ipca["mes_ano"], y=ipca["valor"], marker_color=[AZUL if v >= 0 else LARANJA for v in ipca["valor"]],
                           text=[br(v) for v in ipca["valor"]], textposition="outside"))
    c2.plotly_chart(layout(fig, titulo="IPCA mensal · últimos 24 meses (%)"), width="stretch")
    c3, c4 = st.columns(2)
    c3.plotly_chart(layout(go.Figure([linha(1, LARANJA)]), 300, "Dólar (venda) · média mensal (R$)"), width="stretch")
    c4.plotly_chart(layout(go.Figure([linha(24369, ROXO)]), 300, "Taxa de desocupação (%)"), width="stretch")

with aba2:
    fig = go.Figure(go.Bar(x=juro["data"], y=juro["juro_real"], name="Juro real ex-post",
                           marker_color=[AMARELO if v >= 0 else LARANJA for v in juro["juro_real"]]))
    st.plotly_chart(layout(fig, 380, "Juro real ex-post · Selic − IPCA 12 meses (p.p.)"), width="stretch")
    anual = (serie[serie["indicador_id"] == 433].assign(f=lambda d: 1 + d["valor"] / 100)
             .groupby("ano")["f"].prod().sub(1).mul(100).reset_index())
    fig = go.Figure(go.Bar(x=anual["ano"], y=anual["f"], marker_color=AZUL, text=[br(v) for v in anual["f"]],
                           textposition="outside"))
    st.plotly_chart(layout(fig, 320, "IPCA acumulado no ano (%)"), width="stretch")

with aba3:
    c1, c2 = st.columns(2)
    dol = serie[serie["indicador_id"] == 1].copy()
    dol["var"] = dol["valor"].pct_change(12) * 100
    fig = go.Figure(go.Bar(x=dol["data"], y=dol["var"], marker_color=[LARANJA if v >= 0 else AZUL for v in dol["var"].fillna(0)]))
    c1.plotly_chart(layout(fig, 340, "Dólar · variação em 12 meses (%)"), width="stretch")
    c2.plotly_chart(layout(go.Figure([linha(24364, ROSA)]), 340, "IBC-Br · prévia do PIB (índice)"), width="stretch")
    tabela = kpis.reset_index()[["nome", "tema", "mes_ano", "valor", "valor_12m_antes", "variacao_12m", "unidade"]]
    tabela.columns = ["Indicador", "Tema", "Último mês", "Valor", "12 meses antes", "Variação", "Unidade"]
    st.dataframe(tabela, hide_index=True, width="stretch")

st.caption("Fonte: Banco Central do Brasil · Sistema Gerenciador de Séries Temporais (SGS). "
           "Séries diárias agregadas por mês (Selic: fim de mês; dólar: média).")
