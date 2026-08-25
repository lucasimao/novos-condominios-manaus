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
