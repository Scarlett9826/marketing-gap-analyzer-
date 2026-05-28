"""Tests for CLI entry point."""

from __future__ import annotations

from pathlib import Path

import pytest

from marketing_gap.cli import main


def test_cli_help(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "marketing-gap-analyzer" in out
    assert "analyze" in out
    assert "check-model" in out


def test_cli_version(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    out = capsys.readouterr().out
    assert "mgap" in out


def test_cli_missing_config_file(tmp_path: Path, capsys) -> None:
    rc = main(["-c", str(tmp_path / "nope.yaml"), "analyze"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "config file not found" in err


def test_cli_full_analyze(sample_project: Path) -> None:
    rc = main(["-c", str(sample_project), "analyze"])
    assert rc == 0
    output_dir = sample_project.parent / "output"
    assert (output_dir / "official_selling_points.json").exists()
    assert (output_dir / "user_voice.json").exists()
    assert (output_dir / "gap_matrix.json").exists()
    assert (output_dir / "report.md").exists()


def test_cli_default_subcommand_is_analyze(sample_project: Path) -> None:
    rc = main(["-c", str(sample_project)])
    assert rc == 0
    assert (sample_project.parent / "output" / "report.md").exists()


def test_cli_extract_user_with_output(sample_project: Path, tmp_path: Path) -> None:
    out = tmp_path / "voice.json"
    rc = main(["-c", str(sample_project), "extract-user", "-o", str(out)])
    assert rc == 0
    assert out.exists()


def test_cli_check_model_no_key(tmp_path: Path, capsys) -> None:
    """check-model exits 1 when no API key is configured."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("project:\n  name: x\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["-c", str(cfg_file), "check-model"])
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "UNAVAILABLE" in captured.out or "No API key" in captured.out


def test_cli_check_model_bad_endpoint(tmp_path: Path, capsys) -> None:
    """check-model exits 1 when LLM endpoint is unreachable."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("project:\n  name: x\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=sk-test\nLLM_BASE_URL=http://localhost:99999\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["-c", str(cfg_file), "check-model"])
    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "UNAVAILABLE" in out


def test_cli_extract_official_with_output(sample_project: Path, tmp_path: Path) -> None:
    out = tmp_path / "official.json"
    rc = main(["-c", str(sample_project), "extract-official", "-o", str(out)])
    assert rc == 0
    assert out.exists()


def test_cli_gap_matrix_with_output(sample_project: Path, tmp_path: Path) -> None:
    """gap-matrix reads from default output paths when no -o given."""
    # Run full pipeline first to produce the input files
    rc = main(["-c", str(sample_project), "analyze"])
    assert rc == 0
    # Now run just gap-matrix
    out = tmp_path / "matrix.json"
    rc = main(["-c", str(sample_project), "gap-matrix", "-o", str(out)])
    assert rc == 0
    assert out.exists()
