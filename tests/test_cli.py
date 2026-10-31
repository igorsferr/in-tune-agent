from types import SimpleNamespace

from in_tune import cli

AUTH_ERROR = TypeError(
    "Could not resolve authentication method. Expected one of api_key, auth_token, "
    "or credentials to be set."
)


def _client_raising(error):
    def create(**_):
        raise error

    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))


def test_exits_cleanly_on_sair(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "sair")
    assert cli.main(["--now", "2026-11-03T10:00"]) == 0
    assert "Empório da Música" in capsys.readouterr().out


def test_missing_credentials_give_a_clear_message(monkeypatch, capsys):
    # The client is replaced, so this test can never make a real (billed) call,
    # whatever credentials exist on the machine.
    monkeypatch.setattr("in_tune.agent.anthropic.Anthropic", lambda: _client_raising(AUTH_ERROR))
    monkeypatch.setattr("builtins.input", lambda _: "oi")
    assert cli.main([]) == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().out


def test_ctrl_c_while_waiting_exits_cleanly(monkeypatch):
    monkeypatch.setattr(
        "in_tune.agent.anthropic.Anthropic", lambda: _client_raising(KeyboardInterrupt())
    )
    monkeypatch.setattr("builtins.input", lambda _: "oi")
    assert cli.main([]) == 0
