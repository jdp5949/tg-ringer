"""Offline smoke tests — no network, no Telegram credentials required."""

import pytest

import tg_caller
from tg_caller import TgCaller, cli


def test_version():
    assert isinstance(tg_caller.__version__, str)
    assert tg_caller.__version__.count(".") >= 2


def test_exports_client():
    assert TgCaller is tg_caller.TgCaller


def test_client_constructs(tmp_path):
    # Building the client must not connect or require valid creds.
    tg = TgCaller(12345, "0" * 32, session=str(tmp_path / "s"))
    assert tg.client is not None


def test_cli_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "tg-caller" in capsys.readouterr().out


def test_cli_requires_subcommand():
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code != 0


@pytest.mark.parametrize("sub", ["login", "call", "msg", "whoami"])
def test_subcommand_help(sub, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main([sub, "--help"])
    assert exc.value.code == 0
