-- =============================================================================
-- Autorizações de pequeno risco — 12 semanas FECHADAS (domingo → sábado)
--
-- Parâmetro (substituído pelo pipeline via string.Template):
--   $data_referencia  → domingo que inicia a semana corrente (limite EXCLUSIVO).
--                       Permite reprocessar qualquer semana passada (backfill).
--
-- Correções em relação à query original (query_raw.sql):
--   1. semana_autorizacao agora usa o MESMO deslocamento de +1 dia que
--      numero_semana. Antes, autorizações de domingo caíam na semana anterior
--      em semana_autorizacao e na semana seguinte em numero_semana.
--   2. Limites alinhados a semanas domingo→sábado completas. Antes, o limite
--      inferior (current_date - 12 semanas) cortava a 1ª semana no meio e o
--      superior (< segunda-feira) deixava entrar só o domingo da semana atual.
-- =============================================================================
WITH params AS (
    SELECT
        DATE '$data_referencia'                        AS fim_exclusivo,
        date_add('week', -12, DATE '$data_referencia') AS inicio
),

livreto AS (
    SELECT
        cpf_cnpj,
        razao_social,
        nome_fantasia,
        upper(cidade) AS cidade,
        uf
    FROM "pasa_prod_prestadores"."livreto_gsp"
    WHERE 
        data_ref = (
            SELECT max(data_ref) 
            FROM "pasa_prod_prestadores"."livreto_gsp"
        )
        AND categoria_prest = 'CREDENCIADO'
)

SELECT
    a.cnpj_executante,
    coalesce(l.nome_fantasia, l.razao_social)                                       AS prestador_executante,
    l.cidade,
    l.uf,
    a.evento,
    t.descricao_procedimento,
    t.classe_evento,
    -- Domingo que inicia a semana (mesma regra de numero_semana)
    date_add('day', -1, date_trunc('week', date_add('day', 1, a.data_autorizacao))) AS semana_autorizacao,
    week(date_add('day', 1, a.data_autorizacao))                                    AS numero_semana,
    count(DISTINCT a.autorizacao)                                                   AS qtd_autorizacoes

FROM "pasa_prod_utilizacoes"."autorizacoes" a
CROSS JOIN params p
LEFT JOIN livreto l
       ON a.cnpj_executante = l.cpf_cnpj
LEFT JOIN "pasa_prod_utilizacoes"."tge_completa" t
       ON a.evento = t.cod_procedimento

WHERE 
    a.situacao_tiss_evento = 'AUTORIZADA'
    AND a.cnpj_executante IS NOT NULL
    AND a.data_autorizacao >= p.inicio
    AND a.data_autorizacao <  p.fim_exclusivo
    -- Expurga medicina do trabalho, terceiros e indígenas
    AND NOT regexp_like(a.tipo_autorizacao, '(?i)ami|ama|amt')
    AND a.regime_atendimento IN ('Ambulatorial', 'Pronto Socorro')

GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9