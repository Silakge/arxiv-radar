import argparse

import arxiv_radar.cli as cli


def _args(config, force=False):
    return argparse.Namespace(config=config, force=force)


def test_init_writes_template_when_not_a_tty(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", type("FakeStdin", (), {"isatty": lambda self: False})())
    target = tmp_path / "radar.yaml"
    assert cli.cmd_init(_args(str(target))) == 0
    text = target.read_text(encoding="utf-8")
    assert "arxiv-radar configuration" in text
    assert "keywords" in text


def test_init_survives_eof_on_input(tmp_path, monkeypatch, capsys):
    """CI shells can report a tty yet deliver EOF on the first prompt."""
    monkeypatch.setattr(cli.sys, "stdin", type("FakeStdin", (), {"isatty": lambda self: True})())

    def fake_input(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)
    target = tmp_path / "radar.yaml"
    assert cli.cmd_init(_args(str(target))) == 0
    assert "arxiv-radar configuration" in target.read_text(encoding="utf-8")
    assert "interactive terminal" in capsys.readouterr().out


def test_init_refuses_overwrite_without_force(tmp_path, capsys):
    target = tmp_path / "radar.yaml"
    target.write_text("existing: true\n", encoding="utf-8")
    assert cli.cmd_init(_args(str(target))) == 1
    assert target.read_text(encoding="utf-8") == "existing: true\n"


def test_init_force_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", type("FakeStdin", (), {"isatty": lambda self: False})())
    target = tmp_path / "radar.yaml"
    target.write_text("existing: true\n", encoding="utf-8")
    assert cli.cmd_init(_args(str(target), force=True)) == 0
    assert "arxiv-radar configuration" in target.read_text(encoding="utf-8")


def test_main_reports_config_errors(capsys):
    assert cli.main(["run", "--config", "no-such-file.yaml"]) == 2
    assert "Configuration problem" in capsys.readouterr().err
