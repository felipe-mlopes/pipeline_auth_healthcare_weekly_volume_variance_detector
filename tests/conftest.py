import pandas as pd
import pytest

SEMANAS = pd.date_range("2026-07-12", periods=8, freq="7D")  # 4 históricas + 4 recentes


def linha(evento, semana, qtd, prestador="P1", uf="MG", desc=None, classe="EXAMES"):
    return dict(cnpj_executante="1", prestador_executante=prestador, cidade="X", uf=uf, evento=evento,
                descricao_procedimento=desc or f"desc {evento}", classe_evento=classe,
                semana_autorizacao=semana, numero_semana=(semana + pd.Timedelta(days=1)).isocalendar().week,
                qtd_autorizacoes=qtd)


def distribuir(evento, hist, rec, **kw):
    """Espalha `hist` nas 4 primeiras semanas e `rec` nas 4 últimas (≥2 semanas ativas)."""
    rows = []
    for total, semanas in [(hist, SEMANAS[:4]), (rec, SEMANAS[4:])]:
        partes = [total // 2 + total % 2, total // 2] if total else []
        rows += [linha(evento, s, q, **kw) for s, q in zip(semanas, partes) if q]
    return rows


@pytest.fixture
def bruto_roadmap():
    """Casos do radar_de_eventos_emergentes.json + volume de fundo estável."""
    rows = (distribuir("PINCA", 3, 10) + distribuir("CAPECITABINA", 3, 6) + distribuir("VENCLEXTA", 0, 6)
            + distribuir("TEMODAL", 1, 5) + distribuir("POUCO", 0, 2) + distribuir("COMUM", 40, 50))
    rows += [linha("FUNDO", s, 1000) for s in SEMANAS]
    return pd.DataFrame(rows)
