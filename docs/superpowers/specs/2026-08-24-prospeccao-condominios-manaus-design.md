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
CNPJ é emitido diretamente pela Receita Federal. A Receita publica
gratuitamente, uma vez por mês, o dump completo do cadastro nacional de CNPJ
("Dados Abertos do CNPJ"), incluindo:

- Arquivo **Empresas**: `cnpj_basico`, razão social, **natureza jurídica**.
- Arquivo **Estabelecimentos**: `cnpj_basico`, situação cadastral, data de
  início de atividade, CNAE, **código do município**, endereço completo,
  telefone(s), e-mail.

**Filtros usados para identificar os condomínios de Manaus:**
- Natureza jurídica = `306-9` (Condomínio Edilício) — no arquivo Empresas.
  Este é o filtro que garante que o CNPJ é do próprio condomínio, e não de
  uma administradora ou fornecedor (o CNAE "condomínios prediais" sozinho não
  garante isso).
- Código do município = `1302603` (Manaus, IBGE) — no arquivo Estabelecimentos.
- Situação cadastral = **Ativa** (exclui CNPJs baixados/suspensos).

Os dois arquivos são unidos pelo `cnpj_basico`.

**Cadência:** mensal, alinhada à publicação da Receita Federal. O usuário
confirmou que essa defasagem (até ~30 dias) é aceitável, já que um condomínio
recém-registrado ainda leva tempo até contratar uma administradora.

## Arquitetura

Sem infraestrutura própria: usa apenas as ferramentas já disponíveis no
Claude (tarefa agendada + Artifact), sem servidor, banco de dados ou conta em
serviço de terceiros.

### Componentes

1. **Tarefa agendada mensal (cron do Claude)** — dispara o pipeline abaixo
   uma vez por mês (ex.: dia 20, quando a Receita costuma ter publicado a
   atualização do mês).
2. **Coletor de dados** — script(s) que baixam os arquivos abertos de CNPJ da
   Receita Federal, filtram Estabelecimentos + Empresas conforme os critérios
   acima, e produzem a lista atual de condomínios ativos em Manaus.
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
  → baixa Estabelecimentos + Empresas (Dados Abertos do CNPJ, Receita Federal)
  → filtra: município = Manaus, natureza jurídica = Condomínio Edilício, situação = Ativa
  → junta os dois arquivos por cnpj_basico
  → lê o estado atual do painel publicado (lista de CNPJs já conhecidos)
  → calcula o diff: quais CNPJs são novos desde a última execução
  → gera HTML atualizado (lista completa + selo "novo" nos recém-encontrados)
  → republica o mesmo Artifact (mesma URL)
```

### Falhas

Se o download falhar ou a Receita mudar o formato dos arquivos, a execução
**aborta sem republicar** o painel (nunca sobrescreve dados bons com um
resultado quebrado ou incompleto) e envia uma notificação avisando que a
atualização do mês falhou e precisa de atenção manual. Fora isso, o sistema
roda silenciosamente — o usuário consulta o painel quando quiser.

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

- Os arquivos da Receita são nacionais (não vêm pré-filtrados por cidade),
  então cada execução baixa alguns GB antes de filtrar — a implementação
  precisa considerar tempo/memória de processamento dentro dos limites de
  uma tarefa agendada.
- A Receita pode alterar o layout dos arquivos sem aviso — mitigado pelo
  tratamento de erro que aborta sem sobrescrever o painel.
- Nem todo condomínio tem telefone/e-mail preenchido na base — o painel deve
  lidar com campos ausentes com clareza, sem quebrar.
