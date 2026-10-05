import pytest

from radar.application.montar_radar import montar_radar
from radar.domain.emergencia import ParametrosEmergencia
from radar.domain.schema import Classificacao


@pytest.fixture
def eventos(bruto_roadmap):
    return montar_radar(bruto_roadmap, ParametrosEmergencia()).eventos.set_index("evento")


def test_taxas_reproduzem_quicksight(eventos):
    assert eventos.loc["PINCA", "taxa_crescimento_pct"] == pytest.approx(233.33, abs=0.01)
    assert eventos.loc["TEMODAL", "taxa_crescimento_pct"] == pytest.approx(400)
    assert eventos.loc["CAPECITABINA", "taxa_crescimento_pct"] == pytest.approx(100)


def test_classificacao(eventos):
    c = eventos["classificacao_emergencia"]
    assert c["VENCLEXTA"] == Classificacao.NOVO.value
    assert c["PINCA"] == Classificacao.ALTA.value
    assert c["CAPECITABINA"] == Classificacao.MODERADA.value
    assert c["FUNDO"] == Classificacao.ESTAVEL.value
    assert eventos.loc["VENCLEXTA", "label_evento"].endswith("🔴NOVO")


def test_flag_emergente_aplica_criterios_de_qualidade(eventos):
    f = eventos["flag_emergente"]
    assert f["PINCA"] and f["VENCLEXTA"]
    assert not f["POUCO"]   # volume recente < 3
    assert not f["COMUM"]   # histórico > 5 (não é evento raro)
    assert not f["FUNDO"]


def test_ranking_por_score(eventos):
    em = eventos[eventos["flag_emergente"]].sort_values("rank_emergencia")
    assert em.index[0] == "VENCLEXTA"  # 6 × cap 5 = 30 > Pinça 10 × 2,33
    assert em["rank_emergencia"].is_monotonic_increasing


def test_base_media_semanal_muda_taxa(bruto_roadmap):
    p = ParametrosEmergencia(base_comparacao="media_semanal")
    e = montar_radar(bruto_roadmap, p).eventos.set_index("evento")
    assert e.loc["PINCA", "taxa_crescimento_pct"] == pytest.approx(233.33, abs=0.01)  # janelas iguais (4×4)


def test_detalhe_herda_classificacao_do_evento(bruto_roadmap):
    r = montar_radar(bruto_roadmap, ParametrosEmergencia())
    d = r.detalhe(["uf", "prestador_executante"])
    assert set(d.loc[d["evento"] == "PINCA", "classificacao_emergencia"]) == {Classificacao.ALTA.value}
