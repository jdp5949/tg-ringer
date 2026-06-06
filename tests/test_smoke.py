"""Offline smoke tests — no network, no Telegram credentials required."""

import importlib

import pytest

import tg_ringer
from tg_ringer import TgCaller, cli


def test_version():
    assert isinstance(tg_ringer.__version__, str)
    assert tg_ringer.__version__.count(".") >= 2


def test_exports_client():
    assert TgCaller is tg_ringer.TgCaller


def test_client_constructs(tmp_path):
    # Building the client must not connect or require valid creds.
    tg = TgCaller(12345, "0" * 32, session=str(tmp_path / "s"))
    assert tg.client is not None


def test_cli_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "tg-ringer" in capsys.readouterr().out


def test_cli_requires_subcommand():
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code != 0


@pytest.mark.parametrize("sub", ["init", "login", "call", "msg", "whoami", "config"])
def test_subcommand_help(sub, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main([sub, "--help"])
    assert exc.value.code == 0


def _cli_with_home(tmp_path, monkeypatch):
    # Point config at a temp dir and reload the module so paths pick it up.
    monkeypatch.setenv("TG_RINGER_HOME", str(tmp_path))
    for var in ("TG_API_ID", "TG_API_HASH", "TG_TARGET", "TG_SESSION", "RING_SECONDS"):
        monkeypatch.delenv(var, raising=False)
    return importlib.reload(cli)


def test_config_save_load_roundtrip(tmp_path, monkeypatch):
    c = _cli_with_home(tmp_path, monkeypatch)
    c._save_config({"TG_API_ID": "111", "TG_API_HASH": "abc123", "TG_TARGET": "+1"})
    # New process env: only the file should provide values.
    for var in ("TG_API_ID", "TG_API_HASH", "TG_TARGET"):
        monkeypatch.delenv(var, raising=False)
    assert c._is_configured() is True
    assert c.CONFIG_FILE.exists()
    # config file must not be world-readable (chmod 600)
    assert (c.CONFIG_FILE.stat().st_mode & 0o077) == 0


def test_not_configured_without_file(tmp_path, monkeypatch):
    c = _cli_with_home(tmp_path, monkeypatch)
    assert c._is_configured() is False


def test_config_command_masks_hash(tmp_path, monkeypatch, capsys):
    c = _cli_with_home(tmp_path, monkeypatch)
    c._save_config({"TG_API_ID": "111", "TG_API_HASH": "0123456789abcdef"})
    for var in ("TG_API_ID", "TG_API_HASH"):
        monkeypatch.delenv(var, raising=False)
    c.main(["config"])
    out = capsys.readouterr().out
    assert "0123456789abcdef" not in out  # full hash never printed
    assert "0123" in out and "…" in out
    importlib.reload(cli)  # restore module state for other tests
