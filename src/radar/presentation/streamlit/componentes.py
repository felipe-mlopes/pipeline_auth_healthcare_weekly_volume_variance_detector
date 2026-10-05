"""Formatação e gráficos reutilizáveis (cores e regras do roadmap)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from radar.domain.schema import Classificacao

AZUL_HIST, LARANJA_REC, AZUL_CLARO = "#4472C4", "#ED7D31", "#90CAF9"
VERMELHO_TXT = "#9C0006"

CORES_CLASSIFICACAO = {
    Classificacao.NOVO.value: ("#FFC7CE", "#9C0006"),
    Classificacao.ALTA.value: ("#FFE0B2", "#E65100"),
    Classificacao.MODERADA.value: ("#FFF9C4", "#F57F17"),
}

NOMES = {
    "rank_emergencia": "Rank", "classificacao_emergencia": "Classificação", "evento": "Evento",
    "descricao_procedimento": "Descrição", "classe_evento": "Classe",
    "qtd_historico_evento": "Qtd histórico", "qtd_recente_evento": "Qtd recente",
    "media_semanal_historico": "Média sem. hist.", "media_semanal_recente": "Média sem. rec.",
    "taxa_crescimento_pct": "Crescimento", "score_emergencia": "Score",
    "semanas_ativas_historico": "Sem. ativas hist.", "semanas_ativas_recente": "Sem. ativas rec.",
    "uf": "UF", "cidade": "Cidade", "prestador_executante": "Prestador",
}

LAYOUT = dict(margin=dict(l=10, r=10, t=60, b=10), legend=dict(orientation="h", y=1.08, x=0))


def rotulo_curto(df: pd.DataFrame, n: int = 42) -> pd.Series:
    desc = df["descricao_procedimento"].where(df["descricao_procedimento"] != "(sem descrição)",
                                              "Evento " + df["evento"].astype(str))
    curto = desc.where(desc.str.len() <= n, desc.str[: n - 1] + "…")
    novo = df["classificacao_emergencia"] == Classificacao.NOVO.value
    return curto.where(~novo, curto + " 🔴NOVO")


def tabela(df: pd.DataFrame, colunas: list[str]):
    """Renomeia, formata e aplica a formatação condicional do roadmap (pandas Styler)."""
    t = df[colunas].rename(columns=NOMES)

    def classif(v):
        if v in CORES_CLASSIFICACAO:
            bg, fg = CORES_CLASSIFICACAO[v]
            return f"background-color:{bg};color:{fg};font-weight:600"
        return ""

    destaque = f"color:{VERMELHO_TXT};font-weight:bold"
    sty = t.style
    if "Classificação" in t:
        sty = sty.map(classif, subset=["Classificação"])
    if "Crescimento" in t:
        sty = sty.map(lambda v: destaque if pd.notna(v) and v >= 200 else "", subset=["Crescimento"])
    if "Qtd histórico" in t:
        sty = sty.map(lambda v: destaque if v == 0 else "", subset=["Qtd histórico"])
    fmt = {"Crescimento": "{:.0f}%", "Score": "{:.0f}", "Média sem. hist.": "{:.1f}", "Média sem. rec.": "{:.1f}"}
    return sty.format({k: v for k, v in fmt.items() if k in t}, na_rep="—")


def barras_hist_vs_recente(df: pd.DataFrame, titulo: str, subtitulo: str) -> go.Figure:
    d = df.sort_values("qtd_recente_evento")

    fig = go.Figure([
        go.Bar(
            y=d["rotulo"], 
            x=d["qtd_historico_evento"], 
            name="Histórico", 
            orientation="h",
            marker_color=AZUL_HIST, 
            text=d["qtd_historico_evento"], 
            textposition="outside"
        ),
        go.Bar(
            y=d["rotulo"], 
            x=d["qtd_recente_evento"], 
            name="Recente", 
            orientation="h",
            marker_color=LARANJA_REC, 
            text=d["qtd_recente_evento"], 
            textposition="outside"
        )
    ])

    fig.update_layout(**LAYOUT)
    
    fig.update_layout(
        barmode="group", 
        title=dict(text=titulo, subtitle=dict(text=subtitulo)),
        height=max(420, 34 * len(d)), 
        xaxis_title="Qtd autorizações", 
        legend=dict(
            orientation="h",
            yref="container",   # posição relativa à figura inteira, não à área de plotagem
            y=0.02,
            yanchor="bottom",   # cresce para cima a partir da base da figura
            x=0,
            xanchor="left",
            title_text="Classe: ",
        ),
        hoverlabel=dict(
            font_size=16,
            align="left",
            namelength=-1
        )
    )

    fig.update_traces(
        textfont_size=16, 
        textfont_color="#333", 
        textfont_family="Arial Black"
    )

    fig.update_xaxes(
        range=[0, d[["qtd_historico_evento", "qtd_recente_evento"]].max().max() * 1.15]
    )

    fig.update_yaxes(
        tickfont=dict(size=16), 
        automargin=True
    )
    
    return fig



def scatter_emergencia(df: pd.DataFrame, volume_relevante: int, inicio: int, fim: int) -> go.Figure:
    d = df.assign(
        y_pct=df["taxa_crescimento_capped"] * 100,
        nome=df["rotulo"],
    )

    fig = go.Figure()

    for classe, g in d.groupby("classe_evento"):
        fig.add_trace(go.Scatter(
            x=g["qtd_recente_evento"],
            y=g["y_pct"],
            mode="markers",
            name=classe,
            marker=dict(size=9, line=dict(width=1, color="white")),
            customdata=g[["classe_evento", "evento", "nome"]],
            hovertemplate=(
                "<b>%{customdata[2]}</b><br>"
                "Recente: %{x}<br>"
                "Crescimento: %{y:.0f}%"
                "<extra>%{fullData.name}</extra>"
            ),
        ))

    fig.add_hline(
        y=200, 
        line_dash="dash", 
        line_color="#E65100", 
        annotation_text="Alta"
    )

    fig.add_hline(
        y=100, 
        line_dash="dash", 
        line_color="#F57F17", 
        annotation_text="Moderado"
    )

    fig.add_vline(
        x=volume_relevante, 
        line_dash="dot", 
        line_color="gray",
        annotation_text="Volume mínimo relevante"
    )

    fig.update_layout(**LAYOUT)

    fig.update_layout(
        title=dict(
            text="Mapa: Volume Recente × Taxa de Crescimento",
            subtitle=dict(text="Quanto mais à direita e acima, maior o desvio (taxa cap 500%)"),
        ),
        xaxis=dict(
            title=dict(text=f"Qtd Autorizações Recentes (sem {inicio}–{fim})", standoff=10),
            rangemode="tozero",
        ),
        yaxis=dict(title="Taxa de Crescimento (%)", rangemode="tozero"),
        height=620,
        margin=dict(l=10, r=10, t=80, b=170),   # espaço para título do eixo X + legenda
        legend=dict(
            orientation="h",
            yref="container",   # posição relativa à figura inteira, não à área de plotagem
            y=0.02,
            yanchor="bottom",   # cresce para cima a partir da base da figura
            x=0,
            xanchor="left",
            title_text="Classe: ",
        ),
        hoverlabel=dict(
            font_size=16,
            align="left",
            namelength=-1
        )
    )

    return fig
