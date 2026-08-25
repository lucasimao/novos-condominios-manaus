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
