"""Sheet 3 — Drill-Down por Prestador."""
import pandas as pd
import plotly.express as px
import streamlit as st

from radar.domain.schema import Classificacao
from radar.presentation.streamlit import componentes as ui
from radar.presentation.streamlit import estado
from radar.presentation.streamlit.navegacao import botao_voltar

COLUNAS_TABELA = [
    "evento", "descricao_procedimento", "classe_evento", "classificacao_emergencia",
    "qtd_historico_evento", "qtd_recente_evento", "taxa_crescimento_pct", "score_emergencia",
    "semanas_ativas_historico", "semanas_ativas_recente",
]


def render() -> None:
    botao_voltar()
    r = estado.radar()
    det = estado.detalhe_filtrado()
    if det.empty:
        st.warning("Sem dados para os filtros atuais.")
        return

    ranking = det.groupby("prestador_executante")["qtd_recente_evento"].sum().sort_values(ascending=False)
    c1, c2 = st.columns([3, 1])
    with c1:
        prest = estado.seletor("Prestador", ranking.index.tolist(), estado.PRESTADOR_ALVO)
    det_p = det[det["prestador_executante"] == prest]
    with c2:
        uf = estado.seletor("UF", sorted(det_p["uf"].unique()), estado.UF_ALVO)
    det_p = det_p[det_p["uf"] == uf]

    st.title(f"🏥 Investigação: {prest}")
    st.caption(f"{det_p['cidade'].iloc[0]} / {uf} · CNPJ {det_p['cnpj_executante'].iloc[0]}")

    k = st.columns(4)
    k[0].metric("Eventos emergentes", det_p["evento"].nunique())
    k[1].metric("🔴 Novos no radar", int((det_p["classificacao_emergencia"] == Classificacao.NOVO.value).sum()))
    k[2].metric("Autorizações recentes", int(det_p["qtd_recente_evento"].sum()))
    media = det_p["taxa_crescimento_pct"].mean()
    k[3].metric("Crescimento médio", "—" if media != media else f"{media:.0f}%",
                help="Média da taxa local; eventos sem histórico no prestador ficam de fora.")

    # Visual 9 — evolução semanal
    eventos = det_p.nlargest(10, "qtd_recente_evento")["evento"]
    serie = r.base[(r.base["prestador_executante"] == prest) & (r.base["uf"] == uf)
                   & r.base["evento"].isin(eventos)]
    serie = (serie.groupby(["semana_inicio", "numero_semana", "evento", "descricao_procedimento"])
             ["qtd_autorizacoes"].sum().reset_index())
    serie["Evento"] = serie["evento"] + " · " + serie["descricao_procedimento"].str[:35]
    fig = px.line(serie, x="semana_inicio", y="qtd_autorizacoes", color="Evento", markers=True,
                  text="qtd_autorizacoes", hover_data={"numero_semana": True})
    corte = r.janelas.inicio_recente
    fig.add_shape(type="line", x0=corte, x1=corte, y0=0, y1=1, yref="paper",
                  line=dict(color="red", dash="dash"))
    fig.add_annotation(x=corte, y=1, yref="paper", text="Início período recente", showarrow=False,
                       xanchor="left", font_color="red")
    fig.update_traces(textposition="top center")
    fig.update_xaxes(range=[r.janelas.historicas[0] - pd.Timedelta(days=3),
                            r.janelas.recentes[-1] + pd.Timedelta(days=3)])
    fig.update_layout(title=dict(text="Evolução semanal dos eventos emergentes",
                                 subtitle=dict(text="Linha tracejada marca o início do período recente · top 10 eventos")),
                      xaxis_title="Semana (início no domingo)", yaxis_title="Qtd autorizações", height=460, **ui.LAYOUT)
    st.plotly_chart(fig, width="stretch")

    # Visual 10 — eventos do prestador
    st.subheader("Eventos emergentes do prestador")
    st.dataframe(ui.tabela(det_p.sort_values("score_emergencia", ascending=False), COLUNAS_TABELA),
                 hide_index=True, width="stretch")

    # Visual 11 — benchmark: mesmos eventos, outros prestadores da UF
    bench = (det[(det["uf"] == uf) & det["evento"].isin(det_p["evento"])]
             .groupby("prestador_executante")["qtd_recente_evento"].sum()
             .nlargest(15).sort_values().reset_index())
    bench["cor"] = bench["prestador_executante"].eq(prest).map({True: "Investigado", False: "Demais"})
    fig = px.bar(bench, x="qtd_recente_evento", y="prestador_executante", orientation="h", color="cor",
                 text="qtd_recente_evento",
                 color_discrete_map={"Investigado": ui.LARANJA_REC, "Demais": ui.AZUL_CLARO})
    fig.update_layout(title=dict(text=f"Comparativo: prestadores em {uf} nos mesmos eventos",
                                 subtitle=dict(text="Prestador investigado em laranja")),
                      yaxis_title=None, xaxis_title="Qtd recente", showlegend=False,
                      height=max(320, 30 * len(bench)), **ui.LAYOUT)
    st.plotly_chart(fig, width="stretch")


render()
