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
