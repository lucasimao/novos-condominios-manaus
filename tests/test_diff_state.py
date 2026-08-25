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
