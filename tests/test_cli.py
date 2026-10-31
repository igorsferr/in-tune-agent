from in_tune import cli


def test_exits_cleanly_on_sair(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "sair")
    assert cli.main(["--now", "2026-11-03T10:00"]) == 0
    assert "Empório da Música" in capsys.readouterr().out


def test_missing_credentials_give_a_clear_message(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    answers = iter(["oi"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert cli.main([]) == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().out
