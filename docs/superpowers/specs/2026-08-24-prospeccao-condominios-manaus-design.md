# Prospecção de Novos Condomínios em Manaus — Design

**Data:** 2026-08-24
**Status:** Aprovado para planejamento de implementação

## Contexto e objetivo

O usuário administra/oferece serviços de administração de condomínios e quer ser
o primeiro a contatar condomínios recém-registrados em Manaus, antes que eles
contratem uma administradora concorrente. Hoje não existe nenhum processo para
detectar esses registros — o objetivo deste projeto é construir um sistema que
identifique automaticamente, todo mês, os condomínios que abriram CNPJ em
Manaus e apresente essa lista num painel de fácil consulta.

## Fonte de dados

Os condomínios (condomínio edilício) não se registram na Junta Comercial — o
CNPJ é emitido diretamente pela Receita Federal. A Receita **não expõe uma
API de consulta/filtro**: publica gratuitamente, uma vez por mês, um snapshot
completo do cadastro nacional de CNPJ como arquivos brutos para download em
massa (CSV zipado, sem filtro, Brasil inteiro). Hoje essa base passa de 85 GB
descompactados, e os servidores oficiais da Receita são conhecidos por serem
lentos/inconsistentes — relatos da comunidade apontam de 2 a 5 horas para
baixar e processar a base completa. Baixar e filtrar isso localmente todo mês
só para extrair os poucos condomínios de Manaus é desproporcional e frágil
(risco de estourar tempo de execução da tarefa agendada).

**Fonte escolhida: Base dos Dados (espelho público no Google BigQuery).**
O projeto [Base dos Dados](https://basedosdados.org) já carrega essa mesma
base da Receita, atualizada no mesmo ritmo mensal, dentro do BigQuery,
pronta para consulta via SQL — a filtragem acontece do lado do servidor do
Google, então a tarefa mensal recebe só o resultado já filtrado (algumas
centenas de linhas, poucos KB) em vez de dezenas de GB brutos. Datasets
usados: `basedosdados.br_me_cnpj.empresas` e
`basedosdados.br_me_cnpj.estabelecimentos`, unidas por `cnpj_basico`:

- **`empresas`**: `cnpj_basico`, razão social, **`natureza_juridica`**.
- **`estabelecimentos`**: `cnpj_basico`, `situacao_cadastral`,
  `data_inicio_atividade`, CNAE, **`id_municipio`**, endereço completo
  (logradouro, número, bairro, CEP), telefone(s), e-mail.

**Filtros usados para identificar os condomínios de Manaus:**
- `natureza_juridica = '3069'` (Condomínio Edilício) — em `empresas`. Este é
  o filtro que garante que o CNPJ é do próprio condomínio, e não de uma
  administradora ou fornecedor (o CNAE "condomínios prediais" sozinho não
  garante isso).
- `id_municipio = '1302603'` (Manaus, código IBGE) — em `estabelecimentos`.
- `situacao_cadastral` = **Ativa** — exclui CNPJs baixados/suspensos.

Consulta de referência (os códigos exatos de `natureza_juridica` e
`situacao_cadastral` serão confirmados rodando a query real na
implementação):

```sql
SELECT
  est.cnpj_basico,
  emp.razao_social,
  est.data_inicio_atividade,
  est.logradouro, est.numero, est.bairro, est.cep,
  est.ddd1, est.telefone1, est.email,
  est.situacao_cadastral
FROM `basedosdados.br_me_cnpj.estabelecimentos` AS est
JOIN `basedosdados.br_me_cnpj.empresas` AS emp
  ON est.cnpj_basico = emp.cnpj_basico
WHERE est.id_municipio = '1302603'
  AND emp.natureza_juridica = '3069'
  AND est.situacao_cadastral = '2'
```

**Pré-requisito único:** uma conta gratuita no Google Cloud com um projeto
para rodar consultas no BigQuery. O BigQuery tem um modo "sandbox" gratuito
que não exige cartão de crédito, com limite de 1 TB de dados consultados por
mês — nossa consulta mensal usa uma fração insignificante disso. É a única
conta externa ao ecossistema Claude/Receita que este sistema depende.

**Cadência:** mensal, alinhada à publicação da Receita Federal (a Base dos
Dados atualiza seu espelho no mesmo ritmo). O usuário confirmou que essa
defasagem (até ~30 dias) é aceitável, já que um condomínio recém-registrado
ainda leva tempo até contratar uma administradora.

## Arquitetura

Sem servidor ou banco de dados para manter: usa as ferramentas já
disponíveis no Claude (tarefa agendada + Artifact) mais uma única conta
gratuita externa (Google Cloud, modo sandbox do BigQuery) só para autenticar
a consulta de dados — ver "Fonte de dados" acima.

### Componentes

1. **Tarefa agendada mensal (cron do Claude)** — dispara o pipeline abaixo
   uma vez por mês (ex.: dia 20, quando a Receita costuma ter publicado a
   atualização do mês).
2. **Coletor de dados** — executa a consulta SQL de referência (seção
   "Fonte de dados") no BigQuery público da Base dos Dados, que já devolve
   a lista atual de condomínios ativos em Manaus filtrada e pronta.
3. **Estado/histórico** — não há banco de dados externo. O próprio painel
   publicado guarda a lista completa já vista (embutida como dado — ex. JSON
   — na página). A cada execução, o pipeline lê o painel atual publicado
   (via busca da URL do Artifact) para saber o que já era conhecido antes de
   calcular o que é novo.
4. **Painel (dashboard)** — um Artifact (página privada) republicado a cada
   execução mensal, sempre no mesmo link.

### Fluxo mensal

```
[Cron mensal]
  → roda a query SQL no BigQuery público (basedosdados.br_me_cnpj)
    filtrando: município = Manaus, natureza jurídica = Condomínio Edilício, situação = Ativa
  → lê o estado atual do painel publicado (lista de CNPJs já conhecidos)
  → calcula o diff: quais CNPJs são novos desde a última execução
  → gera HTML atualizado (lista completa + selo "novo" nos recém-encontrados)
  → republica o mesmo Artifact (mesma URL)
```

### Falhas

Se a consulta ao BigQuery falhar (credencial expirada, mudança de schema na
Base dos Dados, etc.), a execução **aborta sem republicar** o painel (nunca
sobrescreve dados bons com um resultado quebrado ou incompleto) e envia uma
notificação avisando que a atualização do mês falhou e precisa de atenção
manual. Fora isso, o sistema roda silenciosamente — o usuário consulta o
painel quando quiser.

## Conteúdo do painel

Tabela com um condomínio por linha:

| Campo | Fonte | Observação |
|---|---|---|
| Razão social | Empresas | Nome oficial do condomínio |
| Data de abertura do CNPJ | Estabelecimentos | Usada para ordenar (mais novo primeiro) |
| Endereço completo + bairro | Estabelecimentos | Logradouro, número, bairro, CEP |
| Telefone | Estabelecimentos | Pode estar vazio — mostrar "—" |
| E-mail | Estabelecimentos | Pode estar vazio — mostrar "—" |
| Situação cadastral | Estabelecimentos | Painel só lista os **ativos** |
| Selo "🆕 Novo este mês" | Calculado | Baseado no diff contra a execução anterior |

Funcionalidades: busca por nome/bairro e ordenação por data de abertura. Sem
controle de status/pipeline (não é um CRM) — o usuário exporta/copia o que
precisar para seu fluxo de trabalho de contato.

## Carga inicial (bootstrap)

Na primeira execução não existe "mês anterior" para comparar, então marcar
tudo como "novo" seria enganoso (muitos condomínios já existem há anos). A
primeira rodada:

- Traz o histórico completo de condomínios edilícios ativos em Manaus já
  registrados na base da Receita;
- Marca esse lote inicial como **carga histórica**, sem o selo de "novo";
- A partir da 2ª execução (mês seguinte), o selo "🆕 Novo este mês" passa a
  valer, comparando com quem já estava na base no mês anterior.

## Fora de escopo (YAGNI)

- Controle de status por lead (contatado/negociando/fechado) — o usuário
  confirmou que só precisa da lista, não de um CRM.
- Fontes de dados pagas com atualização mais frequente que mensal — o
  usuário confirmou que a cadência mensal e gratuita é suficiente.
- Notificação proativa a cada novo condomínio encontrado — o usuário optou
  por consultar o painel quando quiser, não por alertas.
- Hospedagem própria (servidor, banco de dados externo) — descartada em
  favor do Artifact.

## Riscos conhecidos

- Dependência de um projeto de terceiros (Base dos Dados) para espelhar os
  dados da Receita no BigQuery — se o espelho atrasar ou sair do ar, a
  consulta falha (mitigado pelo tratamento de erro que aborta sem
  sobrescrever o painel).
- Requer uma conta Google Cloud (gratuita, modo sandbox) só para autenticar
  as consultas — é a única dependência externa ao ecossistema Claude/Receita.
- A Receita (e, por consequência, a Base dos Dados) pode alterar o layout
  dos dados sem aviso — mesma mitigação acima.
- Nem todo condomínio tem telefone/e-mail preenchido na base — o painel deve
  lidar com campos ausentes com clareza, sem quebrar.
- Os códigos exatos de `natureza_juridica` (Condomínio Edilício) e
  `situacao_cadastral` (Ativa) usados na query precisam ser confirmados
  contra a tabela de domínio real da Base dos Dados na implementação, antes
  de confiar nos resultados.
