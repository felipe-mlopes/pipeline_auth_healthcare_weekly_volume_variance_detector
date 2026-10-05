"""Sheet 2 — Drill-Down por UF."""
import plotly.express as px
import streamlit as st

from radar.presentation.streamlit import componentes as ui
from radar.presentation.streamlit import estado
from radar.presentation.streamlit.navegacao import botao_voltar, ir_para

COLUNAS_TABELA = [
    "uf", "cidade", "prestador_executante", "evento", "descricao_procedimento", "classe_evento",
    "classificacao_emergencia", "qtd_historico_evento", "qtd_recente_evento", "taxa_crescimento_pct",
    "score_emergencia",
]


def _clique_uf() -> None:
    pts = st.session_state["bar_uf"].selection.points
    st.session_state[estado.UF_ALVO] = pts[0]["y"] if pts else estado.TODAS


def render() -> None:
    botao_voltar()
    st.title("🗺️ Drill-Down por UF")
    det = estado.detalhe_filtrado()

    if evento := st.session_state.get(estado.EVENTO_ALVO):
        det = det[det["evento"] == evento]
        c1, c2 = st.columns([5, 1])
        c1.info(f"Evento em foco: **{evento}** — {det['descricao_procedimento'].iloc[0] if len(det) else ''}")
        if c2.button("Ver todos os eventos"):
            st.session_state[estado.EVENTO_ALVO] = None
            st.rerun()
    if det.empty:
        st.warning("Sem dados para os filtros atuais.")
        return

    ufs = sorted(det["uf"].unique())
    uf = estado.seletor("UF", [estado.TODAS, *ufs], estado.UF_ALVO)
    det_uf = det if uf == estado.TODAS else det[det["uf"] == uf]

    c1, c2 = st.columns(2)
    with c1:  # Visual 5 — eventos emergentes por UF (clique = filter action)
        por_uf = det.groupby("uf")["evento"].nunique().sort_values().rename("eventos").reset_index()
        fig = px.bar(por_uf, x="eventos", y="uf", orientation="h", text="eventos",
                     color="eventos", color_continuous_scale=["#90CAF9", "#1565C0"])
        fig.update_layout(title="Eventos emergentes por UF", coloraxis_showscale=False,
                          height=max(350, 26 * len(por_uf)), yaxis_title=None, **ui.LAYOUT)
        st.plotly_chart(fig, width="stretch", on_select=_clique_uf,
                        selection_mode="points", key="bar_uf")
    with c2:  # Visual 6 — distribuição por classe
        por_classe = det_uf.groupby("classe_evento")["evento"].nunique().rename("eventos").reset_index()
        fig = px.pie(por_classe, names="classe_evento", values="eventos", hole=0.55)
        fig.update_traces(textinfo="percent+value")
        fig.update_layout(title=f"Distribuição por classe · {uf}", **ui.LAYOUT)
        st.plotly_chart(fig, width="stretch")

    # Visual 7 — tabela UF + prestador (navigation action → Sheet 3)
    st.subheader(f"Prestadores com eventos emergentes · {uf}")
    st.caption("Volumes e crescimento são do prestador; a classificação é a do evento no radar geral.")
    tab = det_uf.sort_values("qtd_recente_evento", ascending=False).reset_index(drop=True)
    escolha = st.dataframe(ui.tabela(tab, COLUNAS_TABELA), hide_index=True, width="stretch",
                           on_select="rerun", selection_mode="single-row", key="tabela_uf", height=420)
    if escolha and escolha.selection.rows:
        linha = tab.iloc[escolha.selection.rows[0]]
        if st.button(f"🏥 Investigar {linha['prestador_executante']}", type="primary"):
            ir_para("prestador", **{estado.PRESTADOR_ALVO: linha["prestador_executante"],
                                    estado.UF_ALVO: linha["uf"]})

    # Visual 8 — top 10 prestadores
    top = (det_uf.groupby("prestador_executante")["qtd_recente_evento"].sum()
           .nlargest(10).sort_values().reset_index())
    fig = px.bar(top, x="qtd_recente_evento", y="prestador_executante", orientation="h",
                 text="qtd_recente_evento", color_discrete_sequence=[ui.LARANJA_REC])
    fig.update_layout(title="Top 10 prestadores — autorizações recentes em eventos emergentes",
                      yaxis_title=None, xaxis_title="Qtd recente", height=420, **ui.LAYOUT)
    st.plotly_chart(fig, width="stretch")


render()
