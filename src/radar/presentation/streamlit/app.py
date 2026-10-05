"""Radar de Eventos Emergentes — Streamlit.

    streamlit run src/radar/presentation/streamlit/app.py

Equivalência com o roadmap QuickSight:
  Sheet 1 → paginas/radar.py · Sheet 2 → paginas/uf.py · Sheet 3 → paginas/prestador.py
  Parâmetros/controles (paramSemanaCorte, paramVolumeMinimo, filtros) → barra lateral global
  Navigation actions → navegacao.ir_para()  ·  Filter actions → seleção em gráficos (on_select)
"""
import streamlit as st

from radar.domain.emergencia import ParametrosEmergencia
from radar.presentation.streamlit import estado
from radar.presentation.streamlit.navegacao import PAGINAS

st.set_page_config(page_title="Radar de Eventos Emergentes", page_icon="📡", layout="wide")

PAGINAS.update({
    "radar": st.Page("paginas/radar.py", title="Radar de Emergentes", icon="📡", url_path="radar", default=True),
    "uf": st.Page("paginas/uf.py", title="Drill-Down por UF", icon="🗺️", url_path="uf"),
    "prestador": st.Page("paginas/prestador.py", title="Drill-Down Prestador", icon="🏥", url_path="prestador"),
    "execucoes": st.Page("paginas/execucoes.py", title="Execuções (cache)", icon="🗂️", url_path="execucoes"),
})
nav = st.navigation(list(PAGINAS.values()))

# ---------------------------------------------------------------- barra lateral
snapshots = estado.listar_snapshots()
if not snapshots:
    st.warning("Nenhum snapshot no cache ainda. Rode `radar extrair` (Athena) ou "
               "`radar importar-csv <arquivos>` e recarregue a página.")
    st.stop()

with st.sidebar:
    st.subheader("Base")
    ids = [s["id"] for s in snapshots]
    meta = {s["id"]: s for s in snapshots}
    st.session_state["snapshot_id"] = st.selectbox(
        "Snapshot", ids, key="sb_snapshot",
        format_func=lambda i: f"Ref. {meta[i]['semana_referencia']:%d/%m/%Y} · {meta[i]['origem']} "
                              f"· {meta[i]['executado_em']:%d/%m %H:%M}",
        help="Cada execução semanal fica salva no cache. Selecione uma anterior para ver o radar daquela semana.",
    )

    st.subheader("Parâmetros")
    semanas_recentes = st.slider("Semanas no período recente", 1, 8, 4, key="p_semanas",
                                 help="paramSemanaCorte: as N últimas semanas fechadas formam o período recente.")
    volume_minimo = st.slider("Volume mínimo recente", 1, 20, 3, key="p_volume", help="paramVolumeMinimo")
    sem_limite = st.checkbox("Sem limite de histórico", key="p_sem_limite",
                             help="Por padrão só entram eventos raros (≤ N autorizações no histórico).")
    max_historico = None if sem_limite else st.slider("Máx. autorizações no histórico", 0, 50, 5, key="p_maxhist")
    base = st.radio("Base da taxa de crescimento", ["absoluta", "media_semanal"], key="p_base",
                    format_func={"absoluta": "Soma do período (igual QuickSight)",
                                 "media_semanal": "Média por semana"}.get)
    st.session_state["params"] = ParametrosEmergencia(
        semanas_recentes=semanas_recentes, volume_minimo=volume_minimo,
        max_historico=max_historico, base_comparacao=base,
    )

    st.subheader("Filtros")
    try:
        r = estado.radar()
    except ValueError as e:
        st.error(str(e))
        st.stop()
    st.multiselect("Classificação", estado.CLASSIFICACOES_EMERGENTES,
                   default=estado.CLASSIFICACOES_EMERGENTES, key="filtro_classificacao")
    st.multiselect("Classe do evento", sorted(r.emergentes["classe_evento"].unique()),
                   key="filtro_classe", placeholder="Todas")

nav.run()
