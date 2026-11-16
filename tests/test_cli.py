import pytest

from interview_prep import __main__ as cli


def _run(monkeypatch, argv, typed=None):
    monkeypatch.setattr("sys.argv", ["interview_prep", *argv])
    if typed is not None:
        monkeypatch.setattr("builtins.input", lambda _prompt: typed)
    cli.main()


@pytest.mark.parametrize("typed", ["", "   \n\t"])
def test_blank_prompt_answer_prints_help(monkeypatch, capsys, typed):
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, [], typed=typed)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage:" in err
    assert "--answer" in err
    assert "No answer given" in err


def test_blank_answer_flag_prints_help(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, ["--answer", ""])
    assert exc.value.code == 2
    assert "No answer given" in capsys.readouterr().err


def test_eof_at_prompt_prints_help(monkeypatch, capsys):
    def raise_eof(_prompt):
        raise EOFError

    monkeypatch.setattr("sys.argv", ["interview_prep"])
    monkeypatch.setattr("builtins.input", raise_eof)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "No answer given" in capsys.readouterr().err


def test_answer_runs_pipeline(monkeypatch, capsys):
    _run(monkeypatch, ["--answer", "The situation was tense; my action was to listen; the result shipped."])
    out = capsys.readouterr().out
    assert "Q:" in out
    assert "No answer given" not in out


def test_weak_answer_prints_improvements(monkeypatch, capsys):
    _run(monkeypatch, ["--answer", "I listened to the team."])
    out = capsys.readouterr().out
    assert "  - Try to address" in out


def test_ctrl_c_at_prompt_exits_quietly(monkeypatch, capsys):
    def raise_interrupt(_prompt):
        raise KeyboardInterrupt

    monkeypatch.setattr("sys.argv", ["interview_prep"])
    monkeypatch.setattr("builtins.input", raise_interrupt)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 130
    captured = capsys.readouterr()
    assert "Cancelled." in captured.err
    assert "Traceback" not in captured.err
    assert "usage:" not in captured.err
