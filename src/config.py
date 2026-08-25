"""Constantes da consulta ao BigQuery público da Base dos Dados.

Os códigos abaixo foram confirmados contra a tabela oficial do IBGE/CONCLA
(natureza jurídica) e o layout de dados abertos do CNPJ (situação
cadastral). Ainda assim, DEVEM ser reconfirmados rodando a query real na
Tarefa 6, antes de confiar nos resultados em produção.
"""

ID_MUNICIPIO_MANAUS = "1302603"
NATUREZA_JURIDICA_CONDOMINIO_EDILICIO = "3085"
SITUACAO_CADASTRAL_ATIVA = "02"

BIGQUERY_SQL = """
SELECT
  CONCAT(est.cnpj_basico, est.cnpj_ordem, est.cnpj_dv) AS cnpj,
  emp.razao_social AS razao_social,
  CAST(est.data_inicio_atividade AS STRING) AS data_abertura,
  est.tipo_logradouro AS tipo_logradouro,
  est.logradouro AS logradouro,
  est.numero AS numero,
  est.complemento AS complemento,
  est.bairro AS bairro,
  est.ddd1 AS ddd1,
  est.telefone1 AS telefone1,
  est.email AS email
FROM `basedosdados.br_me_cnpj.estabelecimentos` AS est
JOIN `basedosdados.br_me_cnpj.empresas` AS emp
  ON est.cnpj_basico = emp.cnpj_basico
WHERE est.id_municipio = @municipio
  AND emp.natureza_juridica = @natureza_juridica
  AND est.situacao_cadastral = @situacao_ativa
"""
