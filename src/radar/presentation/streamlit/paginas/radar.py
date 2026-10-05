"""Sheet 1 — Radar de Emergentes (visão geral)."""
import streamlit as st

from radar.domain.schema import Classificacao
from radar.presentation.streamlit import componentes as ui
from radar.presentation.streamlit import estado
from radar.presentation.streamlit.navegacao import ir_para

VOLUME_RELEVANTE = 5  # linha de referência do scatter (roadmap)

COLUNAS_TABELA = [
    "rank_emergencia", "classificacao_emergencia", "evento", "descricao_procedimento", "classe_evento",
    "qtd_historico_evento", "qtd_recente_evento", "media_semanal_historico", "media_semanal_recente",
    "taxa_crescimento_pct", "score_emergencia", "semanas_ativas_historico", "semanas_ativas_recente",
]


def _semana(base, ts) -> int:
    return int(base.loc[base["semana_inicio"] == ts, "numero_semana"].iloc[0])


def render() -> None:
    r = estado.radar()
    j = r.janelas
    sh = (_semana(r.base, j.historicas[0]), _semana(r.base, j.historicas[-1]))
    sr = (_semana(r.base, j.recentes[0]), _semana(r.base, j.recentes[-1]))

    st.title("📡 Radar de Procedimentos Emergentes nas Autorizações")
    st.caption(f"Autorizações de pequeno risco · histórico sem. {sh[0]}–{sh[1]} "
               f"({len(j.historicas)} sem.) × recente sem. {sr[0]}–{sr[1]} ({len(j.recentes)} sem.)")

    # ---------------------------------------------------------- KPIs (PRE_FILTER)
    todos = r.emergentes
    contagem = todos["classificacao_emergencia"].value_counts()
    k = st.columns(5)
    k[0].metric("Eventos monitorados", f"{len(r.eventos):,}".replace(",", "."))
    k[1].metric("🔴 Eventos novos", int(contagem.get(Classificacao.NOVO.value, 0)))
    k[2].metric("🟠 Eventos em alta", int(contagem.get(Classificacao.ALTA.value, 0)))
    k[3].metric("🟡 Eventos moderados", int(contagem.get(Classificacao.MODERADA.value, 0)))
    k[4].metric("Semana mais recente", f"Sem. {sr[1]}", f"início {j.recentes[-1]:%d/%m}", delta_color="off")

    if r.semanas_descartadas:
        st.info("Semanas incompletas descartadas da análise (volume muito abaixo da mediana): "
                + ", ".join(f"{s:%d/%m/%Y}" for s in r.semanas_descartadas), icon="🧹")

    ev = estado.emergentes_filtrados()
    if ev.empty:
        st.warning("Nenhum evento emergente com os parâmetros e filtros atuais.")
        return
    ev = ev.assign(rotulo=ui.rotulo_curto(ev))

    # ---------------------------------------------------------- gráficos
    c1, c2 = st.columns(2)
    with c1:
        top = ev.nlargest(15, "qtd_recente_evento")
        st.plotly_chart(ui.barras_hist_vs_recente(
            top, "Top 15 Eventos Emergentes: Histórico vs Recente",
            f"Azul = sem. {sh[0]}–{sh[1]} · Laranja = sem. {sr[0]}–{sr[1]}"), width="stretch")
    with c2:
        sel = st.plotly_chart(ui.scatter_emergencia(ev, VOLUME_RELEVANTE, *sr), width="stretch",
                              on_select="rerun", selection_mode=("points", "box", "lasso"), key="scatter")
    classes_clicadas = {p["customdata"][0] for p in (sel.selection.points if sel else []) if p.get("customdata")}

    # ---------------------------------------------------------- tabela ranking
    tab = ev.sort_values("rank_emergencia")
    if classes_clicadas:
        tab = tab[tab["classe_evento"].isin(classes_clicadas)]
        st.caption(f"Filtrado pelo gráfico: {', '.join(sorted(classes_clicadas))} (clique em área vazia para limpar)")

    st.subheader("Ranking de eventos emergentes")
    escolha = st.dataframe(ui.tabela(tab, COLUNAS_TABELA), hide_index=True, width="stretch",
                           on_select="rerun", selection_mode="single-row", key="tabela_ranking", height=460)
    linhas = escolha.selection.rows if escolha else []
    if linhas:
        evento = tab.iloc[linhas[0]]
        st.write(f"**Selecionado:** {evento['evento']} — {evento['descricao_procedimento']}")
        if st.button("🗺️ Detalhar por UF / prestador", type="primary"):
            ir_para("uf", **{estado.EVENTO_ALVO: evento["evento"], estado.UF_ALVO: None})
    else:
        st.caption("Selecione uma linha para detalhar o evento por UF e prestador.")


render()