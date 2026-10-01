"""Self-Correcting Bootstrapper Engine for the Labish monorepo.

Interactive, cross-workspace provisioning script. It is the code-managed
source of truth for machine provisioning (see the "INSTALLER SYNC &
COMPLIANCE BOUNDARY" rule in the root ``AGENTS.md``).

Responsibilities:

1. System check   -- verify the core Debian host runtime binaries
                     (``python3``, ``node``, ``npm``, PostgreSQL, Redis,
                     nginx) and interactively offer to install any missing
                     packages via ``apt``.
2. Python check   -- validate the active virtual environment and install
                     backend dependencies via ``pip install -e '.[dev]'``
                     inside ``apps/api/``.
3. Frontend check -- locate ``npm``, install the ``apps/web/`` package set,
                     and run ``npm run generate-client`` so the OpenAPI
                     contract layer is compiled.
4. Database check -- interactively offer to run ``alembic upgrade head``.
5. Systemd check  -- on hosts with ``/etc/systemd/system``, offer to link
                     the ``deployment/systemd/*.service`` units, reload the
                     systemd daemon, and scaffold the ``/etc/labish/*.env``
                     environment files with secure permissions.

Usage::

    python apps/api/app/setup.py [--yes] [--skip-system] [--skip-frontend]
                                 [--skip-db] [--skip-systemd]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Resolved monorepo layout, anchored on this file's location:
# <repo>/apps/api/app/setup.py
APP_DIR = Path(__file__).resolve().parent
API_DIR = APP_DIR.parent
REPO_ROOT = API_DIR.parent.parent
WEB_DIR = REPO_ROOT / "apps" / "web"
SYSTEMD_SOURCE_DIR = REPO_ROOT / "deployment" / "systemd"

SYSTEMD_TARGET_DIR = Path("/etc/systemd/system")
ENV_FILE_DIR = Path("/etc/labish")
# Environment files referenced by the systemd units (EnvironmentFile=...).
ENV_FILES = ("api.env", "web.env", "qdrant.env")

ENV_FILE_TEMPLATE = """\
# Labish environment file ({name}) -- managed by apps/api/app/setup.py.
# Populate LABISH_* settings here (database URL, JWT key paths, redis URL,
# ...). Never commit secrets to the repository; this file is the only
# place credentials should live.
"""

# Core Debian host runtime requirements. Maps the binary probed on PATH to
# the apt package that provides it. PostgreSQL and Redis also expose their
# server daemons outside PATH on Debian, so secondary probe paths are
# listed for them.
SYSTEM_REQUIREMENTS: dict[str, dict[str, object]] = {
    "python3": {"package": "python3", "extra_paths": ()},
    "node": {"package": "nodejs", "extra_paths": ()},
    "npm": {"package": "npm", "extra_paths": ()},
    "postgresql": {
        "package": "postgresql",
        # The postgres server binary lives under /usr/lib/postgresql on
        # Debian; psql on PATH also proves the stack is installed.
        "extra_paths": ("psql", "postgres"),
    },
    "redis-server": {"package": "redis-server", "extra_paths": ()},
    "nginx": {
        "package": "nginx",
        # nginx installs into /usr/sbin, which may be absent from a
        # non-root operator's PATH.
        "extra_paths": ("/usr/sbin/nginx",),
    },
}


class BootstrapError(RuntimeError):
    """Raised when a provisioning step fails irrecoverably."""


def info(message: str) -> None:
    print(f"[setup] {message}")


def warn(message: str) -> None:
    print(f"[setup][warn] {message}", file=sys.stderr)


def confirm(question: str, *, assume_yes: bool) -> bool:
    """Interactive yes/no prompt; honours --yes and non-TTY environments."""
    if assume_yes:
        info(f"{question} -> auto-confirmed (--yes)")
        return True
    if not sys.stdin.isatty():
        warn(f"{question} -> skipped (non-interactive session, use --yes)")
        return False
    while True:
        answer = input(f"{question} [y/N]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    """Run a subprocess, surfacing a readable error on failure."""
    info(f"$ {' '.join(command)}  (cwd={cwd})")
    result = subprocess.run(command, cwd=cwd, env=env)
    if result.returncode != 0:
        raise BootstrapError(
            f"Command failed with exit code {result.returncode}: {' '.join(command)}"
        )


# ---------------------------------------------------------------------------
# 1. System package check (apt)
# ---------------------------------------------------------------------------

def _binary_present(name: str, extra_paths: tuple[str, ...]) -> bool:
    """Probe PATH for the binary, plus any alternate names/absolute paths."""
    if shutil.which(name) is not None:
        return True
    for candidate in extra_paths:
        if candidate.startswith("/"):
            if Path(candidate).exists():
                return True
        elif shutil.which(candidate) is not None:
            return True
    return False


def check_system_packages(*, assume_yes: bool) -> None:
    info("--- System package check (apt) ---")
    missing: list[tuple[str, str]] = []
    for binary, spec in SYSTEM_REQUIREMENTS.items():
        extra_paths: tuple[str, ...] = spec["extra_paths"]  # type: ignore[assignment]
        package: str = spec["package"]  # type: ignore[assignment]
        if _binary_present(binary, extra_paths):
            info(f"Found host runtime: {binary}")
        else:
            warn(f"Missing host runtime: {binary} (apt package: {package})")
            missing.append((binary, package))

    if not missing:
        info("All core host runtimes are present.")
        return

    missing_list = ", ".join(binary for binary, _ in missing)
    apt_get = shutil.which("apt-get")
    if apt_get is None:
        warn(
            "apt-get was not found; this does not look like a Debian host. "
            "Install the missing runtimes with your platform's package "
            f"manager, then re-run this script: {missing_list}"
        )
        return

    if not confirm(
        f"The following system dependencies are missing on this host: "
        f"[{missing_list}]. Would you like this installer to invoke apt "
        "to install them now?",
        assume_yes=assume_yes,
    ):
        warn(
            "Continuing without installing system packages; later steps "
            f"may fail until these runtimes are present: {missing_list}"
        )
        return

    packages = [package for _, package in missing]
    if os.geteuid() == 0:
        prefix: list[str] = []
    else:
        sudo = shutil.which("sudo")
        if sudo is None:
            warn(
                "Root privileges are required to install system packages, "
                "but neither root nor sudo is available. Re-run this "
                "script as root or install sudo first."
            )
            raise BootstrapError(
                "Insufficient privileges to install: " + missing_list
            )
        warn(
            "Not running as root; apt will be invoked through sudo and "
            "may prompt for your password."
        )
        prefix = [sudo]

    run(prefix + [apt_get, "update"], cwd=REPO_ROOT)
    run(prefix + [apt_get, "install", "-y", *packages], cwd=REPO_ROOT)

    still_missing = [
        binary
        for binary, spec in SYSTEM_REQUIREMENTS.items()
        if not _binary_present(binary, spec["extra_paths"])  # type: ignore[arg-type]
    ]
    if still_missing:
        raise BootstrapError(
            "System runtimes still missing after apt install: "
            + ", ".join(still_missing)
        )
    info("All core host runtimes are now installed.")


# ---------------------------------------------------------------------------
# 2. Python / backend check
# ---------------------------------------------------------------------------

def check_python_backend() -> None:
    info("--- Python backend check ---")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if in_venv:
        info(f"Virtual environment detected: {sys.prefix}")
    else:
        warn(
            "No virtual environment is active. Create one with "
            "'python3 -m venv venv && source venv/bin/activate' inside "
            "apps/api/ before installing dependencies."
        )
        raise BootstrapError("Refusing to install backend dependencies globally.")
    if sys.version_info < (3, 11):
        raise BootstrapError(
            f"Python >= 3.11 required, found {sys.version.split()[0]}."
        )
    run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], cwd=API_DIR)
    info("Backend dependencies are in sync.")


# ---------------------------------------------------------------------------
# 3. Frontend check
# ---------------------------------------------------------------------------

def check_frontend() -> None:
    info("--- Frontend check ---")
    npm = shutil.which("npm")
    if npm is None:
        raise BootstrapError(
            "npm not found on PATH. Install Node.js/npm before provisioning "
            "the frontend workspace."
        )
    info(f"npm found: {npm}")
    run([npm, "install"], cwd=WEB_DIR)

    env = os.environ.copy()
    # Allow offline/contract-file generation; openapi-ts.config.ts falls back
    # to the live backend at http://127.0.0.1:8000/openapi.json otherwise.
    if env.get("OPENAPI_INPUT"):
        info(f"Using OPENAPI_INPUT override: {env['OPENAPI_INPUT']}")
    run([npm, "run", "generate-client"], cwd=WEB_DIR, env=env)
    info("OpenAPI contract layer compiled into apps/web/src/lib/api.")


# ---------------------------------------------------------------------------
# 4. Database check
# ---------------------------------------------------------------------------

def check_database(*, assume_yes: bool) -> None:
    info("--- Database check ---")
    if not confirm(
        "Run database schema evolution now (alembic upgrade head)?",
        assume_yes=assume_yes,
    ):
        info("Skipping database migrations.")
        return
    run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=API_DIR)
    info("Database schema is at head.")


# ---------------------------------------------------------------------------
# 5. Systemd check
# ---------------------------------------------------------------------------

def _ensure_env_files() -> None:
    """Scaffold /etc/labish/*.env placeholders with secure permissions."""
    ENV_FILE_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
    for name in ENV_FILES:
        env_path = ENV_FILE_DIR / name
        if env_path.exists():
            info(f"Environment file already present (left untouched): {env_path}")
        else:
            env_path.write_text(ENV_FILE_TEMPLATE.format(name=name))
            info(f"Created placeholder environment file: {env_path}")
        # Secrets live here: restrict to owner/group, never world-readable.
        os.chmod(env_path, 0o640)


def check_systemd(*, assume_yes: bool) -> None:
    info("--- Systemd check ---")
    if not SYSTEMD_TARGET_DIR.is_dir():
        info("/etc/systemd/system not found; skipping systemd provisioning.")
        return
    units = sorted(SYSTEMD_SOURCE_DIR.glob("*.service"))
    if not units:
        warn(f"No service units found in {SYSTEMD_SOURCE_DIR}; nothing to link.")
        return
    unit_names = ", ".join(unit.name for unit in units)
    if not confirm(
        f"Link systemd units ({unit_names}) into {SYSTEMD_TARGET_DIR} and "
        "reload the daemon?",
        assume_yes=assume_yes,
    ):
        info("Skipping systemd provisioning.")
        return
    if os.geteuid() != 0:
        warn(
            "Root privileges are required to manage systemd units and "
            "/etc/labish environment files. Re-run this script with sudo."
        )
        return

    _ensure_env_files()

    for unit in units:
        target = SYSTEMD_TARGET_DIR / unit.name
        if target.is_symlink() or target.exists():
            if target.is_symlink() and target.resolve() == unit.resolve():
                info(f"Unit already linked: {target}")
                continue
            warn(f"Refusing to overwrite existing unit: {target}")
            continue
        target.symlink_to(unit.resolve())
        info(f"Linked {unit.name} -> {target}")

    run(["systemctl", "daemon-reload"], cwd=REPO_ROOT)
    info(
        "Systemd units linked and daemon reloaded. Enable services with "
        "'systemctl enable --now <unit>' once the /etc/labish/*.env files "
        "are populated."
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Labish self-correcting bootstrapper engine."
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Assume 'yes' for all interactive prompts.",
    )
    parser.add_argument(
        "--skip-system", action="store_true",
        help="Skip the host-level system package (apt) verification step.",
    )
    parser.add_argument(
        "--skip-frontend", action="store_true",
        help="Skip the npm install / generate-client step.",
    )
    parser.add_argument(
        "--skip-db", action="store_true",
        help="Skip the alembic migration prompt.",
    )
    parser.add_argument(
        "--skip-systemd", action="store_true",
        help="Skip systemd unit linking and environment file handling.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    info(f"Repository root: {REPO_ROOT}")
    try:
        if args.skip_system:
            info("Skipping system package check (--skip-system).")
        else:
            check_system_packages(assume_yes=args.yes)
        check_python_backend()
        if args.skip_frontend:
            info("Skipping frontend check (--skip-frontend).")
        else:
            check_frontend()
        if args.skip_db:
            info("Skipping database check (--skip-db).")
        else:
            check_database(assume_yes=args.yes)
        if args.skip_systemd:
            info("Skipping systemd check (--skip-systemd).")
        else:
            check_systemd(assume_yes=args.yes)
    except BootstrapError as exc:
        warn(str(exc))
        return 1
    except KeyboardInterrupt:
        warn("Interrupted by operator.")
        return 130
    info("Bootstrap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
