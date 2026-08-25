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
