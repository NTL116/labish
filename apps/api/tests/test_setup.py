"""Unit tests for the bootstrapper's pure helpers (no host mutation)."""

import subprocess

import pytest

from app import setup


def test_redact_masks_sql_password_literal():
    sql = "CREATE ROLE labish LOGIN PASSWORD 'doiCE4secret'"
    assert setup.redact(sql) == "CREATE ROLE labish LOGIN PASSWORD '********'"


def test_redact_masks_dsn_password():
    scheme = "postgresql+asyncpg://"
    dsn = scheme + "labish:" + "s3cr3t" + "@127.0.0.1:5432/labish"
    redacted = setup.redact(dsn)
    assert "s3cr3t" not in redacted
    assert redacted == scheme + "labish:********@127.0.0.1:5432/labish"


def test_run_echo_never_prints_password(capsys):
    with pytest.raises(setup.BootstrapError) as excinfo:
        setup.run(
            ["false", "ALTER ROLE labish LOGIN PASSWORD 'topsecret'"],
            cwd=setup.REPO_ROOT,
        )
    out = capsys.readouterr().out
    assert "topsecret" not in out
    assert "topsecret" not in str(excinfo.value)
    assert "PASSWORD '********'" in out


@pytest.mark.parametrize(
    ("output", "ok"),
    [
        ("v20.19.2\n", False),
        ("v22.12.0", False),
        ("v22.18.0", True),
        ("v24.1.0", True),
        ("garbage", False),
    ],
)
def test_node_version_floor(output, ok):
    assert setup._node_version_ok(setup._parse_node_version(output)) is ok


def test_sap_ingestion_failure_is_recorded_as_warning(monkeypatch):
    monkeypatch.setattr(
        setup.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1),
    )
    ctx = setup.Context(assume_yes=True)
    setup._execute(ctx, "SAP ingestion", setup.check_sap_ingestion)
    assert ctx.results[0][:2] == ("SAP ingestion", "warning")


def test_summary_reports_warn_and_exit_code(capsys):
    ctx = setup.Context()
    ctx.record("SAP ingestion", "warning", "no SAP config")
    ctx.record("Health check", "ok")
    assert setup.report_summary(ctx) == 0
    out = capsys.readouterr().out
    assert "[WARN] SAP ingestion" in out
    assert "the stack is up" in out


def test_summary_never_claims_stack_up_on_failure(capsys):
    ctx = setup.Context()
    ctx.record("nginx", "failed", "nginx.service is not active")
    ctx.record("Health check", "failed", "gateway root")
    assert setup.report_summary(ctx) == 1
    captured = capsys.readouterr()
    assert "[FAIL] nginx" in captured.out
    assert "the stack is up" not in captured.out
    assert "NOT fully up" in captured.err


def test_summary_without_health_check_is_not_reported_up(capsys):
    ctx = setup.Context()
    ctx.record("Health check", "skipped", "disabled via flag")
    assert setup.report_summary(ctx) == 0
    assert "the stack is up" not in capsys.readouterr().out


def test_foreign_port_listeners(monkeypatch):
    monkeypatch.setattr(
        setup,
        "_port_listeners",
        lambda port: [
            'LISTEN 0 511 0.0.0.0:80 0.0.0.0:* users:(("nginx",pid=1,fd=6))',
            'LISTEN 0 511 [::]:80 [::]:* users:(("apache2",pid=2,fd=4))',
        ],
    )
    conflicts = setup._foreign_port_listeners(80)
    assert len(conflicts) == 1
    assert "apache2" in conflicts[0]


def test_needs_chown_detects_ownership(tmp_path):
    import getpass
    import grp
    import os

    user = getpass.getuser()
    (tmp_path / "file").write_text("x")
    same_group = grp.getgrgid(os.getgid()).gr_name == user
    assert setup._needs_chown(tmp_path, user) is (not same_group)
    assert setup._needs_chown(tmp_path, "root") is (user != "root")
