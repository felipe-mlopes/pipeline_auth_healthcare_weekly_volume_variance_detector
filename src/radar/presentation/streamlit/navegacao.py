"""Registro das páginas para navegação programática (drill-down entre 'sheets')."""
import streamlit as st

PAGINAS: dict[str, "st.Page"] = {}


def ir_para(nome: str, **estado) -> None:
    st.session_state.update(estado)
    st.switch_page(PAGINAS[nome])


def botao_voltar() -> None:
    if st.button("← Voltar ao Radar"):
        from .estado import EVENTO_ALVO, PRESTADOR_ALVO, UF_ALVO
        ir_para("radar", **{EVENTO_ALVO: None, UF_ALVO: None, PRESTADOR_ALVO: None})
