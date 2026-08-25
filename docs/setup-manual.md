# Configuração manual — Prospecção de Condomínios em Manaus

## 1. Criar o projeto no Google Cloud (usuário)

1. Acesse https://console.cloud.google.com/projectcreate e crie um projeto
   novo (ex.: `condominios-manaus`).
2. No projeto criado, ative a API do BigQuery:
   https://console.cloud.google.com/apis/library/bigquery.googleapis.com
3. Confirme que o projeto está no modo gratuito (sandbox do BigQuery) —
   não é necessário cartão de crédito para consultas dentro de 1 TB/mês.

## 2. Criar a service account e a chave (usuário)

1. Vá em "IAM e administrador" → "Contas de serviço" → "Criar conta de
   serviço". Nome sugerido: `prospeccao-condominios`.
2. Dê a ela o papel **BigQuery Job User** (para rodar consultas) — não
   precisa de mais nenhuma permissão, já que os dados consultados são
   públicos.
3. Gere uma chave JSON para essa conta de serviço e salve como
   `secrets/gcp-key.json` na raiz do projeto (essa pasta já está no
   `.gitignore` — nunca commitar essa chave).

## 3. Validar a consulta localmente (Claude, com o usuário)

Com a chave salva em `secrets/gcp-key.json`:

```bash
export GCP_SA_KEY_JSON="$(cat secrets/gcp-key.json)"
.venv/bin/python src/query_bigquery.py > /tmp/current.json
cat /tmp/current.json
```

Conferir manualmente 2-3 CNPJs do resultado (ex. via
https://opencnpj.org ou consulta no site da Receita) para confirmar que:
- Todos são condomínios de fato (não administradoras/fornecedores).
- Os endereços são de Manaus.

Se a lista vier vazia ou claramente errada, revisar os códigos em
`src/config.py` (`NATUREZA_JURIDICA_CONDOMINIO_EDILICIO`,
`SITUACAO_CADASTRAL_ATIVA`) contra o schema real de
`basedosdados.br_me_cnpj` no console do BigQuery antes de continuar.

## 4. Publicar o primeiro painel (bootstrap) (Claude)

```bash
echo "[]" > /tmp/previous.json
.venv/bin/python src/build_dashboard.py \
  --previous /tmp/previous.json \
  --current /tmp/current.json \
  --run-month "$(date +%Y-%m)" \
  --output /tmp/dashboard.html
```

Publicar `/tmp/dashboard.html` com a ferramenta Artifact (título
"Condomínios Novos — Manaus", favicon 🏢). Guardar a URL gerada — ela é
fixa e será reutilizada em toda atualização mensal.

## 5. Subir o repositório para o GitHub (usuário + Claude)

```bash
gh repo create <owner>/novos-condominios-manaus --private --source=. --remote=origin
git push -u origin main
```

## 6. Criar a rotina agendada (Claude, via schedule/RemoteTrigger)

Rotina mensal (ex.: dia 20 às 09:00 America/Manaus), repositório
`https://github.com/<owner>/novos-condominios-manaus`, com o seguinte
prompt:

```
Você mantém o painel de condominios novos em Manaus. Repositorio já clonado.

1. Rode: python src/query_bigquery.py > /tmp/current.json
   (a variavel de ambiente GCP_SA_KEY_JSON ja deve estar disponivel; se
   nao estiver, pare e reporte a falha sem publicar nada)
2. Busque a URL do painel publicado: <URL_DO_ARTIFACT_AQUI>
   Salve o HTML retornado em /tmp/previous.html
3. Rode: python -c "from extract_state import extract_state_from_html; import json,sys; json.dump(extract_state_from_html(open('/tmp/previous.html').read()), open('/tmp/previous.json','w'))"
4. Rode: python src/build_dashboard.py --previous /tmp/previous.json --current /tmp/current.json --run-month $(date +%Y-%m) --output /tmp/dashboard.html
5. Publique /tmp/dashboard.html com a ferramenta Artifact na MESMA URL: <URL_DO_ARTIFACT_AQUI>
6. Se qualquer passo 1-4 falhar, NAO publique nada e relate exatamente qual passo falhou.
```

**Importante:** a variável `GCP_SA_KEY_JSON` precisa estar configurada como
segredo do Environment usado pela rotina (ver configurações de Environment
em https://claude.ai/code/routines) — não existe um jeito de passá-la pelo
corpo da rotina em texto puro.

## 7. Validar a rotina antes de confiar na cadência mensal (Claude)

Rodar a rotina uma vez manualmente ("run now") e inspecionar o log da
execução antes de deixá-la só no cron: confirmar que o painel foi
republicado com sucesso e que nenhum condomínio da carga inicial apareceu
com o selo "novo".
