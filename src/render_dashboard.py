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
