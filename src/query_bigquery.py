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
        info, scopes=["https://www.googleapis.com/auth/bigquery"]
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
