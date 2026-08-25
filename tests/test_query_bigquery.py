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
