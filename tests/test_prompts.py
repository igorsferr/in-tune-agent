import re

from in_tune.policies import Policies
from in_tune.prompts import build_system_prompt


def test_prompt_lists_every_policy_section():
    policies = Policies()
    prompt = build_system_prompt(policies)
    for number in policies.sections:
        assert f"\n{number} — " in prompt


def test_prompt_carries_no_prices_or_stock():
    # Facts come from tools; the only R$ amounts allowed are format examples.
    prompt = build_system_prompt(Policies())
    assert re.findall(r"R\$ ?[\d.,]+", prompt) == ["R$ 1.299,00"]


def test_prompt_is_deterministic():
    assert build_system_prompt(Policies()) == build_system_prompt(Policies())
