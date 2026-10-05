import pandas as pd
from conftest import linha

from radar.domain.semanas import (
    definir_janelas,
    inicio_semana,
    preparar_base,
    semanas_parciais,
)


def test_corrige_bug_de_domingo():
    # Autorização de domingo 27/09: query antiga gera semana_autorizacao=20/09 e numero_semana=40
    bug = linha("E", pd.Timestamp("2026-09-20"), 3)
    bug["numero_semana"] = 40
    ok = linha("E", pd.Timestamp("2026-09-27"), 5)
    base = preparar_base(pd.DataFrame([bug, ok]))
    assert base["semana_inicio"].tolist() == [pd.Timestamp("2026-09-27")]
    assert base["qtd_autorizacoes"].tolist() == [8]


def test_correcao_idempotente(bruto_roadmap):
    uma = preparar_base(bruto_roadmap)
    duas = preparar_base(uma.assign(semana_autorizacao=uma["semana_inicio"]).drop(columns="semana_inicio"))
    assert uma["qtd_autorizacoes"].sum() == duas["qtd_autorizacoes"].sum()
    assert set(uma["semana_inicio"]) == set(duas["semana_inicio"])


def test_semanas_parciais_so_nas_bordas():
    s = pd.date_range("2026-07-05", periods=6, freq="7D")
    df = pd.DataFrame({"semana_inicio": s, "qtd_autorizacoes": [100, 1000, 50, 1000, 1000, 10]})
    assert semanas_parciais(df, 0.5) == [s[0], s[-1]]  # a do meio (feriado) fica


def test_janelas_e_inicio_semana():
    s = list(pd.date_range("2026-07-05", periods=6, freq="7D"))
    j = definir_janelas(s, 4)
    assert len(j.historicas) == 2 and j.inicio_recente == s[2]
    assert str(inicio_semana(pd.Timestamp("2026-10-03").date())) == "2026-09-27"
