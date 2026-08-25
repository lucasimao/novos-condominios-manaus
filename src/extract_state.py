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
