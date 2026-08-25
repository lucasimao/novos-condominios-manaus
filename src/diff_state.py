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
