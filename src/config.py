"""Constantes da consulta ao BigQuery público da Base dos Dados.

Os códigos abaixo foram confirmados contra a tabela oficial do IBGE/CONCLA
(natureza jurídica) e o layout de dados abertos do CNPJ (situação
cadastral), e a query foi validada rodando de verdade contra
`basedosdados.br_me_cnpj` (Tarefa 6, implantação). Duas correções feitas
nessa validação, em relação à primeira versão:

1. Os nomes reais das colunas de telefone são `ddd_1`/`telefone_1` (com
   underscore), não `ddd1`/`telefone1`.
2. `empresas` e `estabelecimentos` guardam um snapshot mensal completo cada
   (colunas `ano`/`mes`/`data`), não só o estado atual — sem fixar
   `data = MAX(data)`, a query devolveria uma linha por mês de histórico
   para cada condomínio, duplicando o resultado.
3. `situacao_cadastral` é armazenada sem zero à esquerda ('2', não '02').
"""

ID_MUNICIPIO_MANAUS = "1302603"
NATUREZA_JURIDICA_CONDOMINIO_EDILICIO = "3085"
SITUACAO_CADASTRAL_ATIVA = "2"

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
  est.ddd_1 AS ddd1,
  est.telefone_1 AS telefone1,
  est.email AS email
FROM `basedosdados.br_me_cnpj.estabelecimentos` AS est
JOIN `basedosdados.br_me_cnpj.empresas` AS emp
  ON est.cnpj_basico = emp.cnpj_basico AND est.data = emp.data
WHERE est.data = (SELECT MAX(data) FROM `basedosdados.br_me_cnpj.estabelecimentos`)
  AND est.id_municipio = @municipio
  AND emp.natureza_juridica = @natureza_juridica
  AND est.situacao_cadastral = @situacao_ativa
"""
