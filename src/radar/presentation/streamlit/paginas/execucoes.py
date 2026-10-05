"""Histórico de execuções guardadas no cache."""
import pandas as pd
import streamlit as st

from radar.presentation.streamlit import estado


def render() -> None:
    st.title("🗂️ Execuções no cache")
    st.caption("Cada extração semanal vira um snapshot imutável. A mesma semana + mesma query não "
               "reconsulta a fonte; se a query mudar, um novo snapshot é criado e o anterior é mantido.")
    df = pd.DataFrame(estado.listar_snapshots())
    st.dataframe(df.rename(columns={"semana_referencia": "Semana de referência", "executado_em": "Executado em",
                                    "assinatura": "Assinatura da query", "origem": "Origem", "linhas": "Linhas"})
                 .drop(columns=["caminho"]), hide_index=True, width="stretch")
    if st.button("Atualizar lista"):
        estado.listar_snapshots.clear()
        st.rerun()


render()
