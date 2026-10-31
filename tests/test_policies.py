import pytest

from in_tune.policies import Policies


@pytest.fixture(scope="module")
def policies():
    return Policies()


def test_every_manual_heading_is_a_section(policies):
    assert len(policies.sections) == 29
    assert list(policies.sections)[:4] == ["capa", "1", "1.1", "1.2"]
    assert "10" in policies.sections


def test_numbered_list_items_are_not_sections(policies):
    # §7.2 is a numbered list ("1. Saudação", "2. Entendimento", ...).
    title, text = policies.sections["7.2"]
    assert title == "Fluxo de Atendimento Padrão"
    assert "1. Saudação" in text


def test_section_text_is_verbatim(policies):
    _, text = policies.sections["4.1"]
    assert "7 (sete) dias corridos após o recebimento" in text


def test_parent_section_includes_its_subsections(policies):
    found = policies.get("4")
    assert [s["section"] for s in found["sections"]] == ["4", "4.1", "4.2", "4.3", "4.4"]


@pytest.mark.parametrize("requested", ["5.2", "§5.2", " 5.2. "])
def test_section_ids_are_forgiving(policies, requested):
    assert policies.get(requested)["sections"][0]["title"] == "Entregas para Outras Cidades"


def test_unknown_section_lists_what_exists(policies):
    missing = policies.get("11")
    assert missing["found"] is False
    assert "7.3" in missing["available_sections"]


def test_index_has_one_line_per_section(policies):
    lines = policies.index().splitlines()
    assert len(lines) == 29
    assert "7.3 — Situações Especiais" in lines
