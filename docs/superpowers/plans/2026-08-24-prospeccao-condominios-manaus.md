# Prospecção de Novos Condomínios em Manaus — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o pipeline que consulta mensalmente o BigQuery público (Base
dos Dados) por condomínios ativos recém-registrados em Manaus e publica/atualiza
um painel (Artifact) com a lista consolidada.

**Architecture:** Um pequeno pacote Python com funções puras testáveis
(diferença de estado, extração de estado anterior a partir do HTML publicado,
renderização do painel) mais um script fino que consulta o BigQuery. Um
`RemoteTrigger` (rotina agendada na nuvem) roda mensalmente, encadeando esses
scripts via Bash e publicando o resultado com a ferramenta Artifact — sem
servidor, sem banco de dados externo. Ver
`docs/superpowers/specs/2026-08-24-prospeccao-condominios-manaus-design.md`
para o desenho completo.

**Tech Stack:** Python 3.11+, `google-cloud-bigquery`, `pytest`. Sem
framework web — a "aplicação" é o Artifact publicado.

## Global Constraints

- Fonte de dados: BigQuery público `basedosdados.br_me_cnpj` (tabelas
  `empresas` + `estabelecimentos`, unidas por `cnpj_basico`).
- Filtros: `id_municipio = '1302603'` (Manaus), `natureza_juridica = '3085'`
  (Condomínio Edilício), `situacao_cadastral = '02'` (Ativa). Estes códigos
  devem ser confirmados contra a base real na Tarefa 6 antes de confiar nos
  resultados.
- Cadência: mensal. Nunca sobrescrever o painel publicado se qualquer etapa
  do pipeline falhar.
- O painel não é um CRM: sem controle de status por lead.
- Campos ausentes (telefone/e-mail) devem aparecer como "—", nunca quebrar a
  renderização.
- Carga inicial (bootstrap, quando não há estado anterior) nunca marca itens
  como "🆕 Novo este mês" — vira "carga histórica".

---

## Task 1: Estrutura do projeto

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `pytest.ini`

**Interfaces:**
- Produces: layout de pastas `src/` (código) e `tests/` (testes) usado por
  todas as tarefas seguintes; `pytest.ini` configura `pythonpath = src` para
  que os testes importem os módulos como `from diff_state import ...` sem
  instalar o pacote.

- [ ] **Step 1: Criar `requirements.txt`**

```
google-cloud-bigquery==3.27.0
pytest==8.3.3
```

- [ ] **Step 2: Criar `.gitignore`**

```
__pycache__/
*.pyc
.venv/
secrets/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 3: Criar `src/__init__.py` (vazio) e `pytest.ini`**

`src/__init__.py`:
```python
```

`pytest.ini`:
```ini
[pytest]
pythonpath = src
testpaths = tests
```

- [ ] **Step 4: Instalar dependências e confirmar que o pytest roda (sem testes ainda)**

Run: `cd "/Users/lucasimao/Documents/Claude/Projects/Novos Condominios" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -q && .venv/bin/pytest`
Expected: `no tests ran` (sem erro de configuração)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore src/__init__.py pytest.ini
git commit -m "chore: estrutura inicial do projeto Python"
```

---

## Task 2: Diferença de estado (`diff_state.py`)

**Files:**
- Create: `src/diff_state.py`
- Test: `tests/test_diff_state.py`

**Interfaces:**
- Consumes: nada (função pura, sem dependências externas).
- Produces: `compute_diff(previous: list[dict], current: list[dict], run_month: str) -> list[dict]`
  — usada pela Tarefa 6 (`build_dashboard.py`). Cada dict de entrada em
  `current` deve ter ao menos a chave `"cnpj"`; cada dict de saída tem todas
  as chaves de `current` mais `primeira_vez_em: str`, `carga_historica: bool`
  e `novo: bool`. `previous` é `[]` na carga inicial (bootstrap é inferido
  automaticamente quando `previous` está vazio — sem flag manual).

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/test_diff_state.py
from diff_state import compute_diff


def _condo(cnpj, data_abertura="2026-01-10"):
    return {"cnpj": cnpj, "razao_social": f"Condominio {cnpj}", "data_abertura": data_abertura}


def test_bootstrap_marca_tudo_como_carga_historica_sem_novo():
    current = [_condo("111"), _condo("222")]

    resultado = compute_diff(previous=[], current=current, run_month="2026-08")

    assert len(resultado) == 2
    for item in resultado:
        assert item["carga_historica"] is True
        assert item["novo"] is False
        assert item["primeira_vez_em"] == "2026-08"


def test_condominio_ja_visto_nao_e_marcado_como_novo():
    previous = [
        {"cnpj": "111", "primeira_vez_em": "2026-07", "carga_historica": True}
    ]
    current = [_condo("111")]

    resultado = compute_diff(previous=previous, current=current, run_month="2026-08")

    assert resultado[0]["novo"] is False
    assert resultado[0]["carga_historica"] is True
    assert resultado[0]["primeira_vez_em"] == "2026-07"


def test_condominio_inedito_em_execucao_normal_e_marcado_como_novo():
    previous = [
        {"cnpj": "111", "primeira_vez_em": "2026-07", "carga_historica": True}
    ]
    current = [_condo("111"), _condo("222")]

    resultado = compute_diff(previous=previous, current=current, run_month="2026-08")

    novo = next(c for c in resultado if c["cnpj"] == "222")
    assert novo["novo"] is True
    assert novo["carga_historica"] is False
    assert novo["primeira_vez_em"] == "2026-08"


def test_condominio_que_sumiu_do_current_e_descartado():
    previous = [
        {"cnpj": "111", "primeira_vez_em": "2026-07", "carga_historica": True}
    ]
    current = []

    resultado = compute_diff(previous=previous, current=current, run_month="2026-08")

    assert resultado == []


def test_resultado_ordenado_por_data_abertura_decrescente():
    current = [_condo("111", "2026-01-01"), _condo("222", "2026-06-15")]

    resultado = compute_diff(previous=[], current=current, run_month="2026-08")

    assert [c["cnpj"] for c in resultado] == ["222", "111"]
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `.venv/bin/pytest tests/test_diff_state.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'diff_state'`

- [ ] **Step 3: Implementar `src/diff_state.py`**

```python
"""Compara a lista atual de condomínios com o estado anterior do painel."""
from __future__ import annotations


def compute_diff(previous: list[dict], current: list[dict], run_month: str) -> list[dict]:
    """Enriquece cada condomínio de `current` com `primeira_vez_em`, `carga_historica` e `novo`.

    O bootstrap (carga inicial) é inferido automaticamente: se `previous`
    estiver vazio, todo mundo em `current` vira carga histórica (nunca
    "novo"). Isso evita depender de uma flag manual que alguém possa
    esquecer de desligar depois da primeira execução.

    - Um condomínio já visto antes (mesmo `cnpj` em `previous`) mantém seus
      valores originais de `primeira_vez_em`/`carga_historica` e `novo=False`.
    - Um condomínio inédito, fora do bootstrap, é um achado real deste mês
      (`carga_historica=False`, `novo=True`).

    Condomínios que existiam em `previous` mas não aparecem mais em `current`
    (ex.: baixados, situação deixou de ser "Ativa") são descartados — o
    painel só lista ativos.

    Retorna a lista resultante ordenada por `data_abertura` decrescente.
    """
    is_bootstrap = len(previous) == 0
    previous_by_cnpj = {c["cnpj"]: c for c in previous}

    merged = []
    for condo in current:
        anterior = previous_by_cnpj.get(condo["cnpj"])
        enriched = dict(condo)
        if anterior is not None:
            enriched["primeira_vez_em"] = anterior["primeira_vez_em"]
            enriched["carga_historica"] = anterior["carga_historica"]
            enriched["novo"] = False
        else:
            enriched["primeira_vez_em"] = run_month
            enriched["carga_historica"] = is_bootstrap
            enriched["novo"] = not is_bootstrap
        merged.append(enriched)

    merged.sort(key=lambda c: c["data_abertura"], reverse=True)
    return merged
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `.venv/bin/pytest tests/test_diff_state.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/diff_state.py tests/test_diff_state.py
git commit -m "feat: comparar estado anterior x atual dos condominios"
```

---

## Task 3: Extrair estado anterior do painel publicado (`extract_state.py`)

**Files:**
- Create: `src/extract_state.py`
- Test: `tests/test_extract_state.py`

**Interfaces:**
- Consumes: nada além do HTML bruto do painel (obtido pela rotina agendada
  via `WebFetch` na Tarefa 6 — fora do escopo deste módulo).
- Produces: `extract_state_from_html(html: str) -> list[dict]`, usada pela
  Tarefa 6. O formato esperado do bloco embutido é definido pela Tarefa 4
  (`render_dashboard.py`): `<script type="application/json" id="condo-data">[...]</script>`.

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/test_extract_state.py
from extract_state import extract_state_from_html


def test_extrai_lista_de_condominios_do_html():
    html = """
    <html><body>
    <script type="application/json" id="condo-data">[{"cnpj": "111", "razao_social": "Condominio A"}]</script>
    </body></html>
    """

    resultado = extract_state_from_html(html)

    assert resultado == [{"cnpj": "111", "razao_social": "Condominio A"}]


def test_retorna_lista_vazia_quando_bloco_nao_existe():
    html = "<html><body><p>Painel ainda nao existe</p></body></html>"

    assert extract_state_from_html(html) == []


def test_retorna_lista_vazia_quando_bloco_esta_vazio():
    html = '<script type="application/json" id="condo-data">[]</script>'

    assert extract_state_from_html(html) == []
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `.venv/bin/pytest tests/test_extract_state.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'extract_state'`

- [ ] **Step 3: Implementar `src/extract_state.py`**

```python
"""Extrai o estado anterior (lista de condominios) embutido no HTML do painel publicado."""
from __future__ import annotations

import json
import re

_DATA_BLOCK_RE = re.compile(
    r'<script type="application/json" id="condo-data">(.*?)</script>',
    re.DOTALL,
)


def extract_state_from_html(html: str) -> list[dict]:
    """Lê o bloco JSON embutido no painel.

    Retorna lista vazia se o painel ainda não existir (primeira execução,
    bootstrap) ou se o bloco estiver presente mas vazio.
    """
    match = _DATA_BLOCK_RE.search(html)
    if not match:
        return []
    return json.loads(match.group(1))
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `.venv/bin/pytest tests/test_extract_state.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/extract_state.py tests/test_extract_state.py
git commit -m "feat: extrair estado anterior do HTML do painel"
```

---

## Task 4: Renderizar o painel (`render_dashboard.py`)

**Files:**
- Create: `src/render_dashboard.py`
- Test: `tests/test_render_dashboard.py`

**Interfaces:**
- Consumes: lista de dicts no formato produzido por `compute_diff` (Tarefa 2):
  chaves `razao_social`, `data_abertura`, `endereco`, `bairro`, `telefone`,
  `email`, `novo` (bool), mais as usadas só para persistência
  (`cnpj`, `primeira_vez_em`, `carga_historica`).
- Produces: `render_dashboard(condominios: list[dict], atualizado_em: str | None = None) -> str`,
  usada pela Tarefa 6. O HTML retornado embute a lista completa de
  `condominios` (com todas as chaves, inclusive `cnpj`/`primeira_vez_em`/
  `carga_historica`) no bloco `<script type="application/json" id="condo-data">`
  que a Tarefa 3 sabe ler — isso fecha o ciclo de estado entre execuções.

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/test_render_dashboard.py
import json

from render_dashboard import render_dashboard


def _condo(**overrides):
    base = {
        "cnpj": "111",
        "razao_social": "Condominio Solar das Palmeiras",
        "data_abertura": "2026-08-10",
        "endereco": "Rua das Flores, 100",
        "bairro": "Adrianópolis",
        "telefone": "(92) 3234-5678",
        "email": "contato@solar.com.br",
        "primeira_vez_em": "2026-08",
        "carga_historica": False,
        "novo": False,
    }
    base.update(overrides)
    return base


def test_renderiza_uma_linha_por_condominio():
    html = render_dashboard([_condo(cnpj="1"), _condo(cnpj="2")], atualizado_em="24/08/2026")

    assert html.count("<tr data-busca=") == 2


def test_mostra_selo_novo_somente_para_entradas_novas():
    html = render_dashboard(
        [_condo(cnpj="1", novo=True), _condo(cnpj="2", novo=False)],
        atualizado_em="24/08/2026",
    )

    assert html.count("Novo este mês") == 1


def test_embute_lista_completa_como_json_para_proxima_execucao():
    condominios = [_condo(cnpj="1"), _condo(cnpj="2")]

    html = render_dashboard(condominios, atualizado_em="24/08/2026")

    inicio = html.index('id="condo-data">') + len('id="condo-data">')
    fim = html.index("</script>", inicio)
    dados = json.loads(html[inicio:fim])
    assert dados == condominios


def test_mostra_estado_vazio_quando_nao_ha_condominios():
    html = render_dashboard([], atualizado_em="24/08/2026")

    assert "Nenhum condomínio encontrado" in html


def test_escapa_html_nos_campos():
    html = render_dashboard(
        [_condo(razao_social="Condominio <script>alert(1)</script>")],
        atualizado_em="24/08/2026",
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html

    # O bloco JSON embutido preserva o dado bruto (sem escapar) — é ele que
    # extract_state.py lê de volta no mes seguinte. O que impede a quebra da
    # tag <script id="condo-data"> é a neutralizacao pontual de "</script"
    # dentro do JSON (ver Step 3), não o escaping do valor do campo.
    inicio = html.index('id="condo-data">') + len('id="condo-data">')
    fim = html.index("</script>", inicio)
    dados = json.loads(html[inicio:fim])
    assert dados[0]["razao_social"] == "Condominio <script>alert(1)</script>"


def test_json_embutido_preserva_caracteres_especiais_sem_escapar():
    condominio = _condo(razao_social='Solar & Cia "Palmeiras" <Torre>')

    html = render_dashboard([condominio], atualizado_em="24/08/2026")

    inicio = html.index('id="condo-data">') + len('id="condo-data">')
    fim = html.index("</script>", inicio)
    dados = json.loads(html[inicio:fim])

    assert dados == [condominio]
    assert "&amp;" not in dados[0]["razao_social"]
    assert "&lt;" not in dados[0]["razao_social"]
    assert "&quot;" not in dados[0]["razao_social"]
```

**Nota (achada durante a implementação):** a primeira versão deste código
mandava `json.dumps(condominios, ensure_ascii=False)` sem qualquer
neutralização — isso permite que um campo contendo o literal `</script`
feche prematuramente a tag `<script id="condo-data">` no HTML final (bug
real de quebra de tag, já que `json.dumps` não escapa `<`/`>`). A correção
certa é neutralizar **apenas a sequência `</script`** dentro da string JSON
já serializada (`\/` é um escape JSON válido, decodificado de volta sem
perdas por `json.loads`) — nunca escapar os valores dos campos antes de
serializar, porque esse bloco é a única fonte de estado entre execuções
mensais (ver `extract_state.py`), e escapar os campos corromperia os dados
cumulativamente a cada mês. Ver Step 3 abaixo, que já reflete a correção.

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `.venv/bin/pytest tests/test_render_dashboard.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'render_dashboard'`

- [ ] **Step 3: Implementar `src/render_dashboard.py`**

```python
"""Gera o HTML do painel de condominios a partir da lista consolidada."""
from __future__ import annotations

import json
from datetime import datetime

_TEMPLATE = """<title>Condomínios Novos — Manaus</title>
<style>
  :root {{
    --bg: #f7f7f5;
    --surface: #ffffff;
    --text: #1a1a1a;
    --text-muted: #6b6b6b;
    --border: #e2e2df;
    --badge-bg: #e6f4ea;
    --badge-text: #1e6b3c;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #17181a;
      --surface: #202124;
      --text: #eaeaea;
      --text-muted: #a0a0a0;
      --border: #333438;
      --badge-bg: #1e3a2a;
      --badge-text: #7fd8a4;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #17181a;
    --surface: #202124;
    --text: #eaeaea;
    --text-muted: #a0a0a0;
    --border: #333438;
    --badge-bg: #1e3a2a;
    --badge-text: #7fd8a4;
  }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 0;
    padding: 24px;
  }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  .subtitle {{ color: var(--text-muted); margin-bottom: 20px; font-size: 0.9rem; }}
  #busca {{
    width: 100%;
    max-width: 320px;
    padding: 8px 12px;
    margin-bottom: 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    color: var(--text);
    font-size: 0.9rem;
  }}
  .table-wrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--surface); font-size: 0.85rem; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  th {{ color: var(--text-muted); font-weight: 600; }}
  tr:last-child td {{ border-bottom: none; }}
  .badge {{
    display: inline-block;
    background: var(--badge-bg);
    color: var(--badge-text);
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-left: 6px;
  }}
  .empty {{ color: var(--text-muted); padding: 24px; text-align: center; }}
</style>

<h1>Condomínios Novos — Manaus</h1>
<p class="subtitle">{total} condomínios ativos encontrados · atualizado em {atualizado_em}</p>
<input id="busca" type="text" placeholder="Buscar por nome ou bairro...">
<div class="table-wrap">
  <table id="tabela">
    <thead>
      <tr>
        <th>Razão social</th>
        <th>Abertura</th>
        <th>Endereço</th>
        <th>Bairro</th>
        <th>Telefone</th>
        <th>E-mail</th>
      </tr>
    </thead>
    <tbody>
      {linhas}
    </tbody>
  </table>
</div>

<script type="application/json" id="condo-data">{dados_json}</script>
<script>
  const busca = document.getElementById("busca");
  const linhas = Array.from(document.querySelectorAll("#tabela tbody tr"));
  busca.addEventListener("input", () => {{
    const termo = busca.value.toLowerCase();
    linhas.forEach((linha) => {{
      linha.style.display = linha.dataset.busca.includes(termo) ? "" : "none";
    }});
  }});
</script>
"""

_LINHA_TEMPLATE = """<tr data-busca="{busca_attr}">
        <td>{razao_social}{badge}</td>
        <td>{data_abertura}</td>
        <td>{endereco}</td>
        <td>{bairro}</td>
        <td>{telefone}</td>
        <td>{email}</td>
      </tr>"""


def _escape(texto: str) -> str:
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_dashboard(condominios: list[dict], atualizado_em: str | None = None) -> str:
    """Gera o HTML completo do painel a partir da lista consolidada de condominios.

    Cada item de `condominios` deve ter, no mínimo, as chaves: razao_social,
    data_abertura, endereco, bairro, telefone, email, novo (bool). Quaisquer
    outras chaves (cnpj, primeira_vez_em, carga_historica) são preservadas
    no JSON embutido, para a próxima execução conseguir ler o estado
    completo de volta (ver extract_state.py).
    """
    if atualizado_em is None:
        atualizado_em = datetime.now().strftime("%d/%m/%Y")

    if not condominios:
        linhas_html_str = '<tr><td colspan="6" class="empty">Nenhum condomínio encontrado.</td></tr>'
    else:
        linhas = []
        for c in condominios:
            badge = ' <span class="badge">🆕 Novo este mês</span>' if c.get("novo") else ""
            busca_attr = _escape(f"{c['razao_social']} {c['bairro']}".lower())
            linhas.append(
                _LINHA_TEMPLATE.format(
                    busca_attr=busca_attr,
                    razao_social=_escape(c["razao_social"]),
                    badge=badge,
                    data_abertura=_escape(c["data_abertura"]),
                    endereco=_escape(c["endereco"]),
                    bairro=_escape(c["bairro"]),
                    telefone=_escape(c["telefone"]),
                    email=_escape(c["email"]),
                )
            )
        linhas_html_str = "\n      ".join(linhas)

    # Serializa os dados brutos (sem escapar) para preservar o estado
    # persistido byte-a-byte na próxima leitura (ver extract_state.py).
    # Apenas a sequência "</script" é neutralizada via escape JSON válido
    # ("\/") para impedir o fechamento prematuro da tag <script>.
    dados_json = json.dumps(condominios, ensure_ascii=False)
    dados_json = dados_json.replace("</script", "<\\/script")

    return _TEMPLATE.format(
        total=len(condominios),
        atualizado_em=_escape(atualizado_em),
        linhas=linhas_html_str,
        dados_json=dados_json,
    )
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `.venv/bin/pytest tests/test_render_dashboard.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/render_dashboard.py tests/test_render_dashboard.py
git commit -m "feat: renderizar HTML do painel de condominios"
```

---

## Task 5: Consulta ao BigQuery (`query_bigquery.py`)

**Files:**
- Create: `src/config.py`
- Create: `src/query_bigquery.py`
- Test: `tests/test_query_bigquery.py`

**Interfaces:**
- Consumes: nada das tarefas anteriores.
- Produces: `row_to_condominio(row: dict) -> dict` (chaves compatíveis com o
  que `compute_diff`/`render_dashboard` esperam: `cnpj`, `razao_social`,
  `data_abertura`, `endereco`, `bairro`, `telefone`, `email`,
  `situacao_cadastral`) e `query_new_condominios(client) -> list[dict]`,
  usadas pela Tarefa 6 através do script de linha de comando (`main`).

Este módulo faz I/O real (BigQuery), então só as funções puras de
formatação (`format_telefone`, `format_endereco`, `row_to_condominio`) são
cobertas por teste unitário aqui. A consulta real contra o BigQuery é
validada manualmente na Tarefa 6, com credenciais de verdade.

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/test_query_bigquery.py
from query_bigquery import format_endereco, format_telefone, row_to_condominio


def test_format_telefone_formata_ddd_e_numero():
    assert format_telefone("92", "32345678") == "(92) 32345678"


def test_format_telefone_retorna_traco_quando_ausente():
    assert format_telefone("", "") == "—"
    assert format_telefone(None, None) == "—"


def test_format_endereco_junta_logradouro_numero_e_complemento():
    row = {
        "tipo_logradouro": "RUA",
        "logradouro": "DAS FLORES",
        "numero": "100",
        "complemento": "BLOCO A",
    }

    assert format_endereco(row) == "RUA DAS FLORES, 100 - BLOCO A"


def test_format_endereco_retorna_traco_quando_vazio():
    assert format_endereco({}) == "—"


def test_row_to_condominio_mapeia_campos_da_receita():
    row = {
        "cnpj": "12345678000199",
        "razao_social": "CONDOMINIO EDIFICIO SOLAR",
        "data_abertura": "2026-08-10",
        "tipo_logradouro": "RUA",
        "logradouro": "DAS FLORES",
        "numero": "100",
        "complemento": None,
        "bairro": "ADRIANOPOLIS",
        "ddd1": "92",
        "telefone1": "32345678",
        "email": None,
    }

    condominio = row_to_condominio(row)

    assert condominio == {
        "cnpj": "12345678000199",
        "razao_social": "CONDOMINIO EDIFICIO SOLAR",
        "data_abertura": "2026-08-10",
        "endereco": "RUA DAS FLORES, 100",
        "bairro": "ADRIANOPOLIS",
        "telefone": "(92) 32345678",
        "email": "—",
        "situacao_cadastral": "Ativa",
    }
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `.venv/bin/pytest tests/test_query_bigquery.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'query_bigquery'`

- [ ] **Step 3: Implementar `src/config.py`**

```python
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
```

- [ ] **Step 4: Implementar `src/query_bigquery.py`**

```python
"""Consulta o BigQuery público (Base dos Dados) e devolve os condominios ativos em Manaus como JSON."""
from __future__ import annotations

import json
import os
import sys

from config import (
    BIGQUERY_SQL,
    ID_MUNICIPIO_MANAUS,
    NATUREZA_JURIDICA_CONDOMINIO_EDILICIO,
    SITUACAO_CADASTRAL_ATIVA,
)


def format_telefone(ddd, telefone) -> str:
    if not ddd or not telefone:
        return "—"
    return f"({ddd}) {telefone}"


def format_endereco(row: dict) -> str:
    logradouro = " ".join(
        p for p in [row.get("tipo_logradouro"), row.get("logradouro")] if p
    )
    partes = []
    if logradouro and row.get("numero"):
        partes.append(f"{logradouro}, {row['numero']}")
    elif logradouro:
        partes.append(logradouro)
    if row.get("complemento"):
        partes.append(row["complemento"])
    return " - ".join(partes) if partes else "—"


def row_to_condominio(row: dict) -> dict:
    """Converte uma linha crua do BigQuery no formato usado pelo resto do pipeline."""
    return {
        "cnpj": row["cnpj"],
        "razao_social": row["razao_social"],
        "data_abertura": row["data_abertura"],
        "endereco": format_endereco(row),
        "bairro": row.get("bairro") or "—",
        "telefone": format_telefone(row.get("ddd1"), row.get("telefone1")),
        "email": row.get("email") or "—",
        "situacao_cadastral": "Ativa",
    }


def build_client(credentials_json: str):
    """Cria um cliente BigQuery a partir do conteúdo JSON (string) de uma service account."""
    from google.cloud import bigquery
    from google.oauth2 import service_account

    info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/bigquery.readonly"]
    )
    return bigquery.Client(project=info["project_id"], credentials=credentials)


def query_new_condominios(client) -> list[dict]:
    """Roda a query de condominios ativos em Manaus e devolve como lista de dicts."""
    from google.cloud import bigquery

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("municipio", "STRING", ID_MUNICIPIO_MANAUS),
            bigquery.ScalarQueryParameter(
                "natureza_juridica", "STRING", NATUREZA_JURIDICA_CONDOMINIO_EDILICIO
            ),
            bigquery.ScalarQueryParameter(
                "situacao_ativa", "STRING", SITUACAO_CADASTRAL_ATIVA
            ),
        ]
    )
    rows = client.query(BIGQUERY_SQL, job_config=job_config).result()
    return [row_to_condominio(dict(row.items())) for row in rows]


def main():
    credentials_json = os.environ.get("GCP_SA_KEY_JSON")
    if not credentials_json:
        print("Erro: variável de ambiente GCP_SA_KEY_JSON não definida.", file=sys.stderr)
        sys.exit(1)
    client = build_client(credentials_json)
    condominios = query_new_condominios(client)
    json.dump(condominios, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `.venv/bin/pytest tests/test_query_bigquery.py -v`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add src/config.py src/query_bigquery.py tests/test_query_bigquery.py
git commit -m "feat: consultar BigQuery publico por condominios de Manaus"
```

---

## Task 6: CLI de orquestração (`build_dashboard.py`) e implantação

**Files:**
- Create: `src/build_dashboard.py`
- Test: `tests/test_build_dashboard.py`
- Create: `docs/setup-manual.md`

**Interfaces:**
- Consumes: `compute_diff` (Tarefa 2), `render_dashboard` (Tarefa 4).
- Produces: script executável via
  `python src/build_dashboard.py --previous <arquivo.json> --current <arquivo.json> --run-month AAAA-MM --output <arquivo.html>`,
  que é o comando que a rotina agendada (RemoteTrigger) chama depois de obter
  `previous` (via `extract_state_from_html`, Tarefa 3, sobre o HTML lido do
  Artifact atual) e `current` (via `query_bigquery.py`, Tarefa 5).

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/test_build_dashboard.py
import json

from build_dashboard import main


def test_gera_html_combinando_estado_anterior_e_atual(tmp_path):
    previous_file = tmp_path / "previous.json"
    current_file = tmp_path / "current.json"
    output_file = tmp_path / "dashboard.html"

    previous_file.write_text(
        json.dumps(
            [
                {
                    "cnpj": "111",
                    "razao_social": "Condominio Antigo",
                    "data_abertura": "2026-01-01",
                    "endereco": "Rua A, 1",
                    "bairro": "Centro",
                    "telefone": "—",
                    "email": "—",
                    "situacao_cadastral": "Ativa",
                    "primeira_vez_em": "2026-01",
                    "carga_historica": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    current_file.write_text(
        json.dumps(
            [
                {
                    "cnpj": "111",
                    "razao_social": "Condominio Antigo",
                    "data_abertura": "2026-01-01",
                    "endereco": "Rua A, 1",
                    "bairro": "Centro",
                    "telefone": "—",
                    "email": "—",
                    "situacao_cadastral": "Ativa",
                },
                {
                    "cnpj": "222",
                    "razao_social": "Condominio Novo",
                    "data_abertura": "2026-08-20",
                    "endereco": "Rua B, 2",
                    "bairro": "Adrianópolis",
                    "telefone": "—",
                    "email": "—",
                    "situacao_cadastral": "Ativa",
                },
            ]
        ),
        encoding="utf-8",
    )

    main(
        [
            "--previous", str(previous_file),
            "--current", str(current_file),
            "--run-month", "2026-08",
            "--output", str(output_file),
        ]
    )

    html = output_file.read_text(encoding="utf-8")
    assert "Condominio Antigo" in html
    assert "Condominio Novo" in html
    assert html.count("Novo este mês") == 1
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `.venv/bin/pytest tests/test_build_dashboard.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'build_dashboard'`

- [ ] **Step 3: Implementar `src/build_dashboard.py`**

```python
"""CLI que junta o estado anterior com os dados atuais e gera o HTML final do painel."""
from __future__ import annotations

import argparse
import json

from diff_state import compute_diff
from render_dashboard import render_dashboard


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--previous", required=True,
        help="JSON com o estado anterior (lista de condominios). Use um arquivo com [] na carga inicial.",
    )
    parser.add_argument(
        "--current", required=True,
        help="JSON com o resultado fresco da consulta ao BigQuery (saida de query_bigquery.py).",
    )
    parser.add_argument(
        "--run-month", required=True,
        help="Mes desta execucao no formato AAAA-MM.",
    )
    parser.add_argument(
        "--output", required=True,
        help="Caminho onde salvar o HTML final do painel.",
    )
    args = parser.parse_args(argv)

    with open(args.previous, encoding="utf-8") as f:
        previous = json.load(f)
    with open(args.current, encoding="utf-8") as f:
        current = json.load(f)

    merged = compute_diff(previous, current, run_month=args.run_month)
    html = render_dashboard(merged)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    novos = sum(1 for c in merged if c.get("novo"))
    print(f"OK: {len(merged)} condominios no total, {novos} novos neste mes. HTML salvo em {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `.venv/bin/pytest tests/test_build_dashboard.py -v`
Expected: `1 passed`

- [ ] **Step 5: Rodar a suíte inteira antes de seguir para a implantação**

Run: `.venv/bin/pytest -v`
Expected: todos os testes das Tarefas 2-6 passam (20 testes no total)

- [ ] **Step 6: Commit do código**

```bash
git add src/build_dashboard.py tests/test_build_dashboard.py
git commit -m "feat: CLI de orquestracao do pipeline mensal"
```

### Implantação (manual, fora do ciclo de TDD)

As etapas abaixo criam recursos reais (conta Google Cloud, repositório
GitHub, rotina agendada) que não podem ser feitas por código/teste — exigem
ação direta do usuário ou uma única execução supervisionada. Documentar
tudo em `docs/setup-manual.md`:

- [ ] **Step 7: Escrever `docs/setup-manual.md`**

```markdown
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

\`\`\`bash
export GCP_SA_KEY_JSON="$(cat secrets/gcp-key.json)"
.venv/bin/python src/query_bigquery.py > /tmp/current.json
cat /tmp/current.json
\`\`\`

Conferir manualmente 2-3 CNPJs do resultado (ex. via
https://opencnpj.org ou consulta no site da Receita) para confirmar que:
- Todos são condomínios de fato (não administradoras/fornecedores).
- Os endereços são de Manaus.

Se a lista vier vazia ou claramente errada, revisar os códigos em
`src/config.py` (`NATUREZA_JURIDICA_CONDOMINIO_EDILICIO`,
`SITUACAO_CADASTRAL_ATIVA`) contra o schema real de
`basedosdados.br_me_cnpj` no console do BigQuery antes de continuar.

## 4. Publicar o primeiro painel (bootstrap) (Claude)

\`\`\`bash
echo "[]" > /tmp/previous.json
.venv/bin/python src/build_dashboard.py \
  --previous /tmp/previous.json \
  --current /tmp/current.json \
  --run-month "$(date +%Y-%m)" \
  --output /tmp/dashboard.html
\`\`\`

Publicar `/tmp/dashboard.html` com a ferramenta Artifact (título
"Condomínios Novos — Manaus", favicon 🏢). Guardar a URL gerada — ela é
fixa e será reutilizada em toda atualização mensal.

## 5. Subir o repositório para o GitHub (usuário + Claude)

\`\`\`bash
gh repo create <owner>/novos-condominios-manaus --private --source=. --remote=origin
git push -u origin main
\`\`\`

## 6. Criar a rotina agendada (Claude, via schedule/RemoteTrigger)

Rotina mensal (ex.: dia 20 às 09:00 America/Manaus), repositório
`https://github.com/<owner>/novos-condominios-manaus`, com o seguinte
prompt:

\`\`\`
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
\`\`\`

**Importante:** a variável `GCP_SA_KEY_JSON` precisa estar configurada como
segredo do Environment usado pela rotina (ver configurações de Environment
em https://claude.ai/code/routines) — não existe um jeito de passá-la pelo
corpo da rotina em texto puro.

## 7. Validar a rotina antes de confiar na cadência mensal (Claude)

Rodar a rotina uma vez manualmente ("run now") e inspecionar o log da
execução antes de deixá-la só no cron: confirmar que o painel foi
republicado com sucesso e que nenhum condomínio da carga inicial apareceu
com o selo "novo".
```

- [ ] **Step 8: Executar as etapas 1-4 do `setup-manual.md` junto com o usuário**

(Etapas 1-2 são do usuário; etapa 3 é validação conjunta; etapa 4 é feita
por Claude publicando o Artifact.)

- [ ] **Step 9: Executar as etapas 5-7 do `setup-manual.md`**

(Repositório no GitHub, criação da rotina via `schedule`/`RemoteTrigger`,
validação com uma execução manual.)

- [ ] **Step 10: Commit final**

```bash
git add docs/setup-manual.md
git commit -m "docs: manual de configuracao e implantacao"
```
