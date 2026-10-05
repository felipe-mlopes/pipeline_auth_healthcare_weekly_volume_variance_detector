from datetime import date

from radar.application.extrair_snapshot import ExtrairSnapshotSemanal
from radar.infrastructure.repositorio_snapshots import RepositorioSnapshotsParquet


class FonteFake:
    nome = "fake"

    def __init__(self, df, assinatura="v1"):
        self.df, self._sig, self.chamadas = df, assinatura, 0

    def assinatura(self):
        return self._sig

    def extrair(self, ref):
        self.chamadas += 1
        return self.df


def test_cache_evita_reconsulta(tmp_path, bruto_roadmap):
    repo = RepositorioSnapshotsParquet(tmp_path)
    fonte = FonteFake(bruto_roadmap)
    caso = ExtrairSnapshotSemanal(fonte, repo)

    a = caso.executar(date(2026, 10, 3))
    b = caso.executar(date(2026, 10, 1))  # mesma semana (dom 27/09)
    assert not a.do_cache and b.do_cache and fonte.chamadas == 1
    assert a.snapshot.semana_referencia == date(2026, 9, 27)

    caso.executar(date(2026, 10, 3), forcar=True)
    assert fonte.chamadas == 2


def test_query_nova_invalida_cache_e_retencao(tmp_path, bruto_roadmap):
    repo = RepositorioSnapshotsParquet(tmp_path)
    ExtrairSnapshotSemanal(FonteFake(bruto_roadmap, "v1"), repo, retencao=2).executar(date(2026, 9, 20))
    ExtrairSnapshotSemanal(FonteFake(bruto_roadmap, "v1"), repo, retencao=2).executar(date(2026, 9, 27))
    r = ExtrairSnapshotSemanal(FonteFake(bruto_roadmap, "v2"), repo, retencao=2).executar(date(2026, 9, 27))
    assert not r.do_cache
    snaps = repo.listar()
    assert len(snaps) == 2 and all(s.semana_referencia == date(2026, 9, 27) for s in snaps)
    assert len(repo.carregar(r.snapshot.id)) == len(bruto_roadmap)
