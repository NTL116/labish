"""Self-Correcting Bootstrapper Engine for the Labish monorepo.

Non-interactive-capable, cross-workspace provisioning script. It is the
code-managed source of truth for machine provisioning (see the "INSTALLER
SYNC & COMPLIANCE BOUNDARY" rule in the root ``AGENTS.md``). The top-level
``install.sh`` one-liner is a thin wrapper that clones the repository and
hands off to this script.

Provisioning steps (resumable -- a failing step is recorded and the
remaining independent steps still run; a final summary reports what needs
attention):

 1. System packages  -- verify core Debian host runtimes (python3,
                        PostgreSQL, Redis, nginx, openssl) and install any
                        missing ones via apt.
 2. Node toolchain   -- ensure Node.js >= NODE_VERSION_MIN (installing the
                        pinned NodeSource major when absent/too old) so the
                        frontend and the systemd unit share one runtime.
 3. Qdrant           -- download the pinned Qdrant release binary with
                        checksum verification into /usr/local/bin/qdrant.
 4. Python backend   -- create/use apps/api/venv and `pip install -e .[dev]`.
 5. OpenAPI export   -- generate openapi.json from the FastAPI app
                        in-process (no live server needed).
 6. Frontend         -- npm install, generate-client (against the offline
                        spec), and `npm run build`.
 7. Secrets          -- persistent RS256 JWT keypair under /etc/labish/keys.
 8. Database         -- create the PostgreSQL role + `labish` and
                        `labish_payload` databases, verify the cluster is
                        up, and run `alembic upgrade head`.
 9. Environment      -- populate /etc/labish/{api,web,qdrant}.env with every
                        required key (generated secrets included).
10. SAP ingestion    -- optional data-dictionary regeneration (never fatal).
11. Systemd + nginx  -- render deployment/ templates with the real user,
                        paths and server name, install them, enable and
                        start all services, then health-check the stack
                        end to end (nginx gateway, FastAPI, Next.js,
                        Qdrant, Dramatiq worker).

The summary records each step as OK, WARN (ran but did not complete),
SKIP or FAIL; the exit code is non-zero only when a step FAILed.

Usage::

    python3 apps/api/app/setup.py [--yes] [--skip-system] [--skip-node]
                                  [--skip-qdrant] [--skip-frontend]
                                  [--skip-db] [--skip-sap-ingest]
                                  [--skip-systemd] [--skip-nginx]
                                  [--server-name NAME] [--site-url URL]
                                  [--service-user USER]
                                  [--rotate-db-password]

Re-running on a provisioned host is a safe no-op/upgrade: every step is
idempotent (existing env values, keys, databases and units are preserved).
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import platform
import pwd
import re
import secrets
import shutil
import string
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# Resolved monorepo layout, anchored on this file's location:
# <repo>/apps/api/app/setup.py
APP_DIR = Path(__file__).resolve().parent
API_DIR = APP_DIR.parent
REPO_ROOT = API_DIR.parent.parent
WEB_DIR = REPO_ROOT / "apps" / "web"
VENV_DIR = API_DIR / "venv"
DEPLOYMENT_DIR = REPO_ROOT / "deployment"
SYSTEMD_SOURCE_DIR = DEPLOYMENT_DIR / "systemd"

SYSTEMD_TARGET_DIR = Path("/etc/systemd/system")
ENV_FILE_DIR = Path("/etc/labish")
KEYS_DIR = ENV_FILE_DIR / "keys"
JWT_PRIVATE_KEY_PATH = KEYS_DIR / "jwt-private.pem"
JWT_PUBLIC_KEY_PATH = KEYS_DIR / "jwt-public.pem"
QDRANT_DATA_DIR = Path("/var/lib/qdrant")

NGINX_SITES_AVAILABLE = Path("/etc/nginx/sites-available")
NGINX_SITES_ENABLED = Path("/etc/nginx/sites-enabled")
NGINX_SITE_NAME = "labish"
HTTP_PORT = 80
GATEWAY_URL = f"http://127.0.0.1:{HTTP_PORT}/"

# Environment files referenced by the systemd units (EnvironmentFile=...).
ENV_FILES = ("api.env", "web.env", "qdrant.env")

# Labish service units managed by this bootstrapper, in start order.
SERVICE_UNITS = ("qdrant", "fastapi", "worker", "nextjs")

# Pinned Node.js major installed from NodeSource when the host runtime is
# missing or older than NODE_VERSION_MIN. Keep in sync with the "engines"
# field in apps/web/package.json (the apps/web dependency tree, e.g.
# @hey-api/openapi-ts, requires node >= 22.18).
NODE_VERSION_MIN = (22, 18)
NODE_MAJOR_PINNED = 22

# Pinned Qdrant release installed to /usr/local/bin/qdrant, with SHA-256
# checksums of the official release tarballs per architecture.
QDRANT_VERSION = "1.13.4"
QDRANT_ASSETS: dict[str, tuple[str, str]] = {
    "x86_64": (
        "qdrant-x86_64-unknown-linux-gnu.tar.gz",
        "520665624999339a600f8c0f7869582b4408952d4f03173b4c65d2422c85e4ae",
    ),
    "aarch64": (
        "qdrant-aarch64-unknown-linux-musl.tar.gz",
        "a9557f598bfccdcf5a3c4991071a709ae9ddc668d480b3477a473545d729f6eb",
    ),
}
QDRANT_BINARY = Path("/usr/local/bin/qdrant")

# Core Debian host runtime requirements. Maps the binary probed on PATH to
# the apt package that provides it. Node.js is handled by its own pinned
# toolchain step (NodeSource), not by this table.
SYSTEM_REQUIREMENTS: dict[str, dict[str, object]] = {
    "python3": {"package": "python3", "extra_paths": ()},
    "pip3": {"package": "python3-pip", "extra_paths": ()},
    "openssl": {"package": "openssl", "extra_paths": ()},
    "postgresql": {
        "package": "postgresql",
        # The postgres server binary lives under /usr/lib/postgresql on
        # Debian; psql on PATH also proves the stack is installed.
        "extra_paths": ("psql", "postgres"),
    },
    "redis-server": {
        "package": "redis-server",
        "extra_paths": ("/usr/bin/redis-server",),
    },
    "nginx": {
        "package": "nginx",
        # nginx installs into /usr/sbin, which may be absent from a
        # non-root operator's PATH.
        "extra_paths": ("/usr/sbin/nginx",),
    },
}


class BootstrapError(RuntimeError):
    """Raised when a provisioning step fails irrecoverably."""


class StepSkipped(RuntimeError):
    """Raised when a step cannot run in this environment (not a failure)."""


class StepWarning(RuntimeError):
    """Raised when a non-fatal step ran but did not complete its work."""


def info(message: str) -> None:
    print(f"[setup] {message}", flush=True)


def warn(message: str) -> None:
    print(f"[setup][warn] {message}", file=sys.stderr, flush=True)


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


# Secret-bearing fragments masked before a command is echoed or embedded in
# an error message, so generated credentials never land in install logs.
_SECRET_PATTERNS = (
    re.compile(r"(PASSWORD\s+)'(?:[^']|'')*'", re.IGNORECASE),
    re.compile(r"(://[^:/@\s]+:)[^@\s]+(@)"),
)


def redact(text: str) -> str:
    """Mask secrets (SQL PASSWORD literals, DSN passwords) in ``text``."""
    text = _SECRET_PATTERNS[0].sub(r"\1'********'", text)
    return _SECRET_PATTERNS[1].sub(r"\1********\2", text)


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run a subprocess, surfacing a readable error on failure."""
    printable = redact(" ".join(command))
    info(f"$ {printable}  (cwd={cwd})")
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=capture,
        text=capture,
    )
    if result.returncode != 0:
        detail = ""
        if capture and result.stderr:
            detail = f"\n{redact(result.stderr.strip())}"
        raise BootstrapError(
            f"Command failed with exit code {result.returncode}: "
            f"{printable}{detail}"
        )
    return result


def root_prefix() -> list[str] | None:
    """Return the command prefix for privileged operations.

    Empty list when already root, ``[sudo]`` when sudo is available, and
    ``None`` when the step must be skipped for lack of privileges.
    """
    if os.geteuid() == 0:
        return []
    sudo = shutil.which("sudo")
    if sudo is not None:
        return [sudo]
    return None


def systemctl_available() -> bool:
    return (
        shutil.which("systemctl") is not None
        and Path("/run/systemd/system").is_dir()
    )


@dataclass
class Context:
    """Mutable install-time configuration shared between steps."""

    assume_yes: bool = False
    service_user: str = ""
    server_name: str = "_"
    site_url: str = ""
    api_database_url: str = ""
    payload_database_url: str = ""
    npm_path: str = ""
    node_path: str = ""
    rotate_db_password: bool = False
    check_gateway: bool = True
    db_password_rotated: bool = False
    results: list[tuple[str, str, str]] = field(default_factory=list)

    def record(self, step: str, status: str, detail: str = "") -> None:
        self.results.append((step, status, detail))


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


def _apt_install(packages: list[str]) -> None:
    apt_get = shutil.which("apt-get")
    if apt_get is None:
        raise StepSkipped(
            "apt-get not found; install manually: " + ", ".join(packages)
        )
    prefix = root_prefix()
    if prefix is None:
        raise StepSkipped(
            "Root privileges (or sudo) required to apt-install: "
            + ", ".join(packages)
        )
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    run(prefix + [apt_get, "update"], cwd=REPO_ROOT, env=env)
    run(prefix + [apt_get, "install", "-y", *packages], cwd=REPO_ROOT, env=env)


def check_system_packages(ctx: Context) -> None:
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
    if not confirm(
        f"The following system dependencies are missing on this host: "
        f"[{missing_list}]. Would you like this installer to invoke apt "
        "to install them now?",
        assume_yes=ctx.assume_yes,
    ):
        warn(
            "Continuing without installing system packages; later steps "
            f"may fail until these runtimes are present: {missing_list}"
        )
        return

    packages = sorted({package for _, package in missing})
    # postgresql-contrib ships cluster tooling alongside the server.
    if "postgresql" in packages:
        packages.append("postgresql-contrib")
    _apt_install(packages)

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
# 2. Node toolchain (pinned)
# ---------------------------------------------------------------------------

def _parse_node_version(output: str) -> tuple[int, int, int] | None:
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", output.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _node_version(node: str) -> tuple[int, int, int] | None:
    try:
        out = subprocess.run(
            [node, "--version"], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return _parse_node_version(out)


def _node_version_ok(version: tuple[int, int, int] | None) -> bool:
    return version is not None and version[:2] >= NODE_VERSION_MIN


def _format_version(version: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def check_node_toolchain(ctx: Context) -> None:
    info("--- Node toolchain check ---")
    node = shutil.which("node")
    version = _node_version(node) if node else None
    minimum = _format_version(NODE_VERSION_MIN)
    if node and _node_version_ok(version):
        info(f"Found Node.js v{_format_version(version)} at {node}")
    else:
        found = f"v{_format_version(version)}" if version else "none"
        warn(
            f"Node.js >= {minimum} required (found: {found}); "
            f"installing Node {NODE_MAJOR_PINNED}.x from NodeSource."
        )
        if not confirm(
            f"Install the pinned Node.js {NODE_MAJOR_PINNED}.x toolchain "
            "from NodeSource now?",
            assume_yes=ctx.assume_yes,
        ):
            raise StepSkipped("Pinned Node.js install declined by operator.")
        prefix = root_prefix()
        if prefix is None:
            raise StepSkipped(
                "Root privileges required to install the Node toolchain."
            )
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        run(
            prefix
            + [
                "bash",
                "-c",
                "curl -fsSL https://deb.nodesource.com/setup_"
                f"{NODE_MAJOR_PINNED}.x | bash -",
            ],
            cwd=REPO_ROOT,
            env=env,
        )
        _apt_install(["nodejs"])
        node = shutil.which("node")
        version = _node_version(node) if node else None
        if node is None or not _node_version_ok(version):
            raise BootstrapError(
                f"Node.js install did not yield node >= {minimum}."
            )
        info(f"Installed Node.js v{_format_version(version)} at {node}")

    npm = shutil.which("npm")
    if npm is None:
        raise BootstrapError("npm not found on PATH after Node provisioning.")
    ctx.node_path = str(Path(node).resolve())
    ctx.npm_path = str(Path(npm).resolve())
    info(f"Using node={ctx.node_path} npm={ctx.npm_path}")


# ---------------------------------------------------------------------------
# 3. Qdrant install (pinned release, checksum verified)
# ---------------------------------------------------------------------------

def check_qdrant(ctx: Context) -> None:
    info("--- Qdrant check ---")
    if QDRANT_BINARY.exists():
        info(f"Qdrant binary already present: {QDRANT_BINARY}")
        return
    arch = platform.machine()
    asset = QDRANT_ASSETS.get(arch)
    if asset is None:
        raise StepSkipped(
            f"No pinned Qdrant release for architecture '{arch}'. Install "
            f"Qdrant {QDRANT_VERSION} manually to {QDRANT_BINARY}."
        )
    prefix = root_prefix()
    if prefix is None:
        raise StepSkipped(
            f"Root privileges required to install Qdrant to {QDRANT_BINARY}."
        )
    if not confirm(
        f"Download and install Qdrant v{QDRANT_VERSION} to {QDRANT_BINARY}?",
        assume_yes=ctx.assume_yes,
    ):
        raise StepSkipped("Qdrant install declined by operator.")

    filename, expected_sha = asset
    url = (
        "https://github.com/qdrant/qdrant/releases/download/"
        f"v{QDRANT_VERSION}/{filename}"
    )
    info(f"Downloading {url}")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / filename
        try:
            urllib.request.urlretrieve(url, archive)  # noqa: S310
        except (urllib.error.URLError, OSError) as exc:
            raise BootstrapError(f"Qdrant download failed: {exc}") from exc
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != expected_sha:
            raise BootstrapError(
                f"Qdrant checksum mismatch for {filename}: "
                f"expected {expected_sha}, got {digest}."
            )
        info("Checksum verified.")
        with tarfile.open(archive) as tar:
            member = tar.getmember("qdrant")
            if hasattr(tarfile, "data_filter"):
                tar.extract(member, path=tmp, filter="data")
            else:  # Python without the PEP 706 extraction filters.
                tar.extract(member, path=tmp)
        extracted = Path(tmp) / "qdrant"
        extracted.chmod(0o755)
        run(
            prefix + ["install", "-m", "0755", str(extracted), str(QDRANT_BINARY)],
            cwd=REPO_ROOT,
        )
    info(f"Qdrant v{QDRANT_VERSION} installed at {QDRANT_BINARY}.")


# ---------------------------------------------------------------------------
# 4. Python / backend check
# ---------------------------------------------------------------------------

def in_virtualenv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def ensure_venv_and_reexec(argv: list[str]) -> None:
    """Create apps/api/venv when missing and re-exec this script inside it.

    Replaces the old hard abort ("no virtual environment is active") so the
    one-liner install needs no manual venv activation.
    """
    if in_virtualenv():
        return
    venv_python = VENV_DIR / "bin" / "python"
    if not venv_python.exists():
        info(f"Creating backend virtual environment: {VENV_DIR}")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)], cwd=API_DIR
        )
        if result.returncode != 0:
            # python3-venv may be missing on a fresh Debian host.
            info("venv creation failed; attempting to apt-install python3-venv.")
            _apt_install(["python3-venv", "python3-pip"])
            subprocess.run(
                [sys.executable, "-m", "venv", str(VENV_DIR)],
                cwd=API_DIR,
                check=True,
            )
    info(f"Re-executing bootstrapper inside {venv_python}")
    os.environ["LABISH_SETUP_REEXEC"] = "1"
    os.execv(
        str(venv_python),
        [str(venv_python), str(Path(__file__).resolve()), *argv, "--skip-system"],
    )


def check_python_backend(ctx: Context) -> None:
    info("--- Python backend check ---")
    if not in_virtualenv():
        raise BootstrapError(
            "Refusing to install backend dependencies globally; venv "
            "re-exec did not engage."
        )
    info(f"Virtual environment: {sys.prefix}")
    if sys.version_info < (3, 11):
        raise BootstrapError(
            f"Python >= 3.11 required, found {sys.version.split()[0]}."
        )
    run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        cwd=API_DIR,
    )
    run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], cwd=API_DIR)
    info("Backend dependencies are in sync.")


# ---------------------------------------------------------------------------
# 5. Offline OpenAPI schema export
# ---------------------------------------------------------------------------

OPENAPI_EXPORT_PATH = WEB_DIR / "openapi.json"

_OPENAPI_EXPORT_SNIPPET = (
    "import json, sys; from app.main import app; "
    "json.dump(app.openapi(), sys.stdout, indent=2)"
)


def export_openapi_schema(ctx: Context) -> None:
    """Generate openapi.json from the FastAPI app in-process.

    Breaks the chicken-and-egg dependency where `npm run generate-client`
    needed an already-running backend on a fresh install.
    """
    info("--- OpenAPI schema export (offline) ---")
    env = os.environ.copy()
    # Importing app.main must never touch a real database during export.
    env.setdefault("LABISH_ENVIRONMENT", "test")
    result = run(
        [sys.executable, "-c", _OPENAPI_EXPORT_SNIPPET],
        cwd=API_DIR,
        env=env,
        capture=True,
    )
    OPENAPI_EXPORT_PATH.write_text(result.stdout)
    info(f"OpenAPI schema exported to {OPENAPI_EXPORT_PATH}.")


# ---------------------------------------------------------------------------
# 6. Frontend check (install, generate-client, production build)
# ---------------------------------------------------------------------------

def check_frontend(ctx: Context) -> None:
    info("--- Frontend check ---")
    npm = ctx.npm_path or shutil.which("npm")
    if npm is None:
        raise BootstrapError(
            "npm not found on PATH. Install Node.js/npm before provisioning "
            "the frontend workspace."
        )
    info(f"npm found: {npm}")
    env = os.environ.copy()
    # CI=1 keeps npm/openapi-ts fully non-interactive (suppresses the
    # openapi-ts "Open a GitHub issue?" crash prompt among others).
    env["CI"] = "1"
    run([npm, "install", "--no-audit", "--no-fund"], cwd=WEB_DIR, env=env)

    if env.get("OPENAPI_INPUT"):
        info(f"Using OPENAPI_INPUT override: {env['OPENAPI_INPUT']}")
    elif OPENAPI_EXPORT_PATH.exists():
        # Default to the offline spec during provisioning; the live
        # http://127.0.0.1:8000/openapi.json URL remains the dev-workflow
        # fallback inside openapi-ts.config.ts.
        env["OPENAPI_INPUT"] = str(OPENAPI_EXPORT_PATH)
        info(f"Using offline OpenAPI spec: {OPENAPI_EXPORT_PATH}")
    run([npm, "run", "generate-client"], cwd=WEB_DIR, env=env)
    info("OpenAPI contract layer compiled into apps/web/src/lib/api.")

    if ctx.site_url:
        env["NEXT_PUBLIC_SITE_URL"] = ctx.site_url
    if ctx.payload_database_url:
        env.setdefault("DATABASE_URI", ctx.payload_database_url)
    run([npm, "run", "build"], cwd=WEB_DIR, env=env)
    info("Next.js production build complete (apps/web/.next).")


# ---------------------------------------------------------------------------
# 7. Persistent RS256 JWT keypair
# ---------------------------------------------------------------------------

def check_jwt_keys(ctx: Context) -> None:
    """Generate a persistent RS256 keypair so sessions survive restarts."""
    info("--- JWT key material check ---")
    if os.geteuid() != 0:
        raise StepSkipped(
            f"Root privileges required to manage {KEYS_DIR}. Generate the "
            "keypair manually (openssl genpkey) and set "
            "LABISH_JWT_PRIVATE_KEY_PATH/LABISH_JWT_PUBLIC_KEY_PATH."
        )
    if JWT_PRIVATE_KEY_PATH.exists() and JWT_PUBLIC_KEY_PATH.exists():
        info(f"Persistent JWT keypair already present in {KEYS_DIR}.")
        return
    openssl = shutil.which("openssl")
    if openssl is None:
        raise BootstrapError("openssl not found; cannot generate JWT keys.")
    ENV_FILE_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
    KEYS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    run(
        [
            openssl, "genpkey", "-algorithm", "RSA",
            "-pkeyopt", "rsa_keygen_bits:3072",
            "-out", str(JWT_PRIVATE_KEY_PATH),
        ],
        cwd=REPO_ROOT,
    )
    run(
        [
            openssl, "pkey", "-in", str(JWT_PRIVATE_KEY_PATH),
            "-pubout", "-out", str(JWT_PUBLIC_KEY_PATH),
        ],
        cwd=REPO_ROOT,
    )
    os.chmod(JWT_PRIVATE_KEY_PATH, 0o600)
    os.chmod(JWT_PUBLIC_KEY_PATH, 0o644)
    if ctx.service_user:
        shutil.chown(KEYS_DIR, user=ctx.service_user)
        shutil.chown(JWT_PRIVATE_KEY_PATH, user=ctx.service_user)
        shutil.chown(JWT_PUBLIC_KEY_PATH, user=ctx.service_user)
    info(f"Persistent RS256 keypair generated in {KEYS_DIR}.")


# ---------------------------------------------------------------------------
# 8. Database provisioning + migrations
# ---------------------------------------------------------------------------

DB_NAME = "labish"
PAYLOAD_DB_NAME = "labish_payload"
DB_ROLE = "labish"


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _run_psql(sql: str, *, capture: bool = False) -> str:
    """Run a statement as the postgres superuser via peer auth."""
    prefix = root_prefix()
    if prefix is None:
        raise StepSkipped("Root privileges required for PostgreSQL admin.")
    command = prefix + [
        "runuser", "-u", "postgres", "--",
        "psql", "-v", "ON_ERROR_STOP=1", "-qAt", "-c", sql,
    ]
    if shutil.which("runuser") is None:
        command = prefix + [
            "su", "-s", "/bin/sh", "postgres", "-c",
            "psql -v ON_ERROR_STOP=1 -qAt -c " + _shell_quote(sql),
        ]
    result = run(command, cwd=Path("/tmp"), capture=capture)
    return (result.stdout or "").strip() if capture else ""


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _ensure_postgres_running() -> None:
    """Verify the PostgreSQL cluster is initialized and accepting connections."""
    pg_isready = shutil.which("pg_isready") or "/usr/bin/pg_isready"
    def ready() -> bool:
        return (
            subprocess.run(
                [pg_isready, "-h", "127.0.0.1", "-p", "5432"],
                capture_output=True,
            ).returncode
            == 0
        )

    if ready():
        info("PostgreSQL is accepting connections.")
        return
    warn("PostgreSQL is not accepting connections; attempting to start it.")
    prefix = root_prefix()
    if prefix is None:
        raise StepSkipped("PostgreSQL is down and root is required to start it.")
    if systemctl_available():
        run(prefix + ["systemctl", "start", "postgresql"], cwd=REPO_ROOT)
    elif shutil.which("service"):
        run(prefix + ["service", "postgresql", "start"], cwd=REPO_ROOT)
    elif shutil.which("pg_ctlcluster"):
        clusters = subprocess.run(
            ["pg_lsclusters", "-h"], capture_output=True, text=True
        )
        first = (clusters.stdout or "").splitlines()
        if first:
            version, name = first[0].split()[:2]
            run(
                prefix + ["pg_ctlcluster", version, name, "start"],
                cwd=REPO_ROOT,
            )
    for _ in range(15):
        if ready():
            info("PostgreSQL is accepting connections.")
            return
        time.sleep(1)
    raise BootstrapError(
        "PostgreSQL cluster did not come up. Check 'pg_lsclusters' / "
        "'systemctl status postgresql' and re-run the bootstrapper."
    )


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def check_database(ctx: Context) -> None:
    info("--- Database provisioning check ---")
    if not confirm(
        "Provision the PostgreSQL role/databases and run migrations now?",
        assume_yes=ctx.assume_yes,
    ):
        info("Skipping database provisioning.")
        return

    _ensure_postgres_running()

    # Reuse the already-provisioned DSNs on re-runs; otherwise generate a
    # fresh credential and (re)set the role password to match.
    api_env = _read_env_file(ENV_FILE_DIR / "api.env")
    web_env = _read_env_file(ENV_FILE_DIR / "web.env")
    existing_dsn = api_env.get("LABISH_DATABASE_URL", "")
    match = re.match(
        rf"postgresql\+asyncpg://{DB_ROLE}:([^@]+)@", existing_dsn
    )
    if match and not ctx.rotate_db_password:
        password = match.group(1)
        info("Reusing database credentials from /etc/labish/api.env.")
        role_sql = None
    else:
        if match:
            info(f"Rotating the PostgreSQL '{DB_ROLE}' role password "
                 "(--rotate-db-password).")
        password = _generate_password()
        role_sql = password

    prefix = root_prefix()
    if prefix is None:
        raise StepSkipped(
            "Root privileges required to create the PostgreSQL role/databases."
        )

    exists = _run_psql(
        f"SELECT 1 FROM pg_roles WHERE rolname = '{DB_ROLE}'", capture=True
    )
    if not exists:
        _run_psql(
            f"CREATE ROLE {DB_ROLE} LOGIN PASSWORD '{password}'"
        )
        info(f"Created PostgreSQL role '{DB_ROLE}'.")
    elif role_sql is not None:
        # Role exists but no recorded credential (or rotation requested):
        # rotate to a known one.
        _run_psql(f"ALTER ROLE {DB_ROLE} LOGIN PASSWORD '{password}'")
        info(f"Reset password for existing PostgreSQL role '{DB_ROLE}'.")
    ctx.db_password_rotated = role_sql is not None and bool(match)

    for db_name in (DB_NAME, PAYLOAD_DB_NAME):
        db_exists = _run_psql(
            f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'",
            capture=True,
        )
        if not db_exists:
            _run_psql(f'CREATE DATABASE "{db_name}" OWNER {DB_ROLE}')
            info(f"Created database '{db_name}' (owner: {DB_ROLE}).")
        else:
            info(f"Database '{db_name}' already exists.")

    ctx.api_database_url = (
        f"postgresql+asyncpg://{DB_ROLE}:{password}@127.0.0.1:5432/{DB_NAME}"
    )
    payload_dsn = (
        f"postgresql://{DB_ROLE}:{password}@127.0.0.1:5432/{PAYLOAD_DB_NAME}"
    )
    ctx.payload_database_url = (
        payload_dsn
        if ctx.db_password_rotated
        else web_env.get("DATABASE_URI") or payload_dsn
    )

    env = os.environ.copy()
    env["LABISH_DATABASE_URL"] = ctx.api_database_url
    run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_DIR,
        env=env,
    )
    info("Database schema is at head.")


# ---------------------------------------------------------------------------
# 9. Environment files (/etc/labish/*.env)
# ---------------------------------------------------------------------------

ENV_FILE_HEADER = """\
# Labish environment file ({name}) -- managed by apps/api/app/setup.py.
# Existing values are preserved on re-runs; never commit this file or its
# secrets to the repository.
"""


def _merge_env_file(
    name: str,
    defaults: dict[str, str],
    overrides: dict[str, str] | None = None,
) -> None:
    """Write defaults for missing keys only, preserving operator edits.

    ``overrides`` are always written (e.g. a freshly rotated credential).
    """
    path = ENV_FILE_DIR / name
    existing = _read_env_file(path)
    merged = {**defaults, **existing, **(overrides or {})}
    lines = [ENV_FILE_HEADER.format(name=name)]
    for key, value in merged.items():
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o640)
    added = [key for key in defaults if key not in existing]
    changed = [
        key for key, value in (overrides or {}).items()
        if existing.get(key) != value
    ]
    if changed:
        info(f"Updated {path} (rewrote: {', '.join(changed)}).")
    if added:
        info(f"Populated {path} (added: {', '.join(added)}).")
    elif not changed:
        info(f"Environment file up to date: {path}")


def check_env_files(ctx: Context) -> None:
    info("--- Environment file check (/etc/labish) ---")
    if os.geteuid() != 0:
        raise StepSkipped(
            f"Root privileges required to manage {ENV_FILE_DIR}. Required "
            "keys are documented in the README ('Environment files')."
        )
    ENV_FILE_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)

    web_env = _read_env_file(ENV_FILE_DIR / "web.env")
    payload_secret = web_env.get("PAYLOAD_SECRET") or secrets.token_hex(32)

    _merge_env_file(
        "api.env",
        {
            "LABISH_ENVIRONMENT": "production",
            "LABISH_DATABASE_URL": ctx.api_database_url
            or f"postgresql+asyncpg://127.0.0.1:5432/{DB_NAME}",
            "LABISH_REDIS_URL": "redis://127.0.0.1:6379/0",
            "LABISH_JWT_PRIVATE_KEY_PATH": str(JWT_PRIVATE_KEY_PATH),
            "LABISH_JWT_PUBLIC_KEY_PATH": str(JWT_PUBLIC_KEY_PATH),
        },
        overrides=(
            {"LABISH_DATABASE_URL": ctx.api_database_url}
            if ctx.db_password_rotated
            else None
        ),
    )
    _merge_env_file(
        "web.env",
        {
            "NODE_ENV": "production",
            "PORT": "3000",
            "NEXT_PUBLIC_SITE_URL": ctx.site_url or "http://localhost",
            "DATABASE_URI": ctx.payload_database_url
            or f"postgresql://127.0.0.1:5432/{PAYLOAD_DB_NAME}",
            "PAYLOAD_SECRET": payload_secret,
        },
        overrides=(
            {"DATABASE_URI": ctx.payload_database_url}
            if ctx.db_password_rotated
            else None
        ),
    )
    _merge_env_file(
        "qdrant.env",
        {
            "QDRANT__SERVICE__HTTP_PORT": "6333",
            "QDRANT__STORAGE__STORAGE_PATH": str(QDRANT_DATA_DIR / "storage"),
            "QDRANT__STORAGE__SNAPSHOTS_PATH": str(QDRANT_DATA_DIR / "snapshots"),
        },
    )


# ---------------------------------------------------------------------------
# 10. SAP metadata ingestion check
# ---------------------------------------------------------------------------

def check_sap_ingestion(ctx: Context) -> None:
    """Offer to run the SAP metadata ingestion engine.

    Regenerates the JSON data dictionary (app/shared/sap_dictionary/)
    and the frontend type definitions (apps/web/src/types/sap.d.ts)
    from the live SAP $metadata document. Degrades gracefully when no
    validated SAP configuration is saved yet.
    """
    info("--- SAP metadata ingestion check ---")
    if not confirm(
        "Ingest the SAP schema now (data dictionary + sap.d.ts "
        "regeneration via app/shared/ingest_sap_metadata.py)?",
        assume_yes=ctx.assume_yes,
    ):
        raise StepSkipped(
            "SAP metadata ingestion declined. Run it later via "
            "POST /settings/sap/ingest or "
            "'python -m app.shared.ingest_sap_metadata'."
        )
    env = os.environ.copy()
    if ctx.api_database_url:
        env.setdefault("LABISH_DATABASE_URL", ctx.api_database_url)
    result = subprocess.run(
        [sys.executable, "-m", "app.shared.ingest_sap_metadata"],
        cwd=API_DIR,
        env=env,
    )
    if result.returncode != 0:
        # Fresh installs typically have no validated SAP gateway yet;
        # ingestion is re-runnable, so never fail the bootstrap on it --
        # but never report it as OK either.
        raise StepWarning(
            "ingestion did not complete (no validated SAP configuration, "
            "or the Service Layer is unreachable); re-run it from the "
            "admin setup page once SAP is connected"
        )
    info("SAP data dictionary and TypeScript definitions regenerated.")


# ---------------------------------------------------------------------------
# 11. Systemd units + nginx (templated), service enablement, health check
# ---------------------------------------------------------------------------

def _resolve_service_user(ctx: Context) -> str:
    """Pick the account that owns the services and the repository files."""
    if ctx.service_user:
        return ctx.service_user
    sudo_user = os.environ.get("SUDO_USER", "")
    if sudo_user and sudo_user != "root":
        return sudo_user
    user = getpass.getuser()
    if user != "root":
        return user
    # Running as plain root (curl | sudo bash): use a dedicated system user.
    try:
        pwd.getpwnam("labish")
    except KeyError:
        if shutil.which("useradd"):
            run(
                [
                    "useradd", "--system", "--user-group",
                    "--home-dir", str(REPO_ROOT), "--shell", "/usr/sbin/nologin",
                    "labish",
                ],
                cwd=REPO_ROOT,
            )
            info("Created dedicated 'labish' system user for the services.")
        else:
            return "root"
    return "labish"


def _needs_chown(path: Path, user: str) -> bool:
    """True when anything under ``path`` is not owned by ``user:user``.

    Stops at the first mismatch, so re-runs on an already-owned tree are
    cheap compared to an unconditional ``chown -R``.
    """
    find = shutil.which("find")
    if find is None:
        return True
    result = subprocess.run(
        [
            find, str(path), "(", "!", "-user", user, "-o", "!", "-group",
            user, ")", "-print", "-quit",
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode != 0 or bool(result.stdout.strip())


def _ensure_owner(path: Path, user: str) -> None:
    if _needs_chown(path, user):
        run(["chown", "-R", f"{user}:{user}", str(path)], cwd=REPO_ROOT)
    else:
        info(f"Ownership already correct ({user}): {path}")


def _render_template(source: Path, substitutions: dict[str, str]) -> str:
    from string import Template

    # safe_substitute leaves nginx runtime variables ($host, $scheme, ...)
    # untouched while replacing the ${...} install-time placeholders.
    return Template(source.read_text()).safe_substitute(substitutions)


def check_systemd(ctx: Context) -> None:
    info("--- Systemd check ---")
    if not systemctl_available() or not SYSTEMD_TARGET_DIR.is_dir():
        raise StepSkipped(
            "systemd is not managing this host; skipping unit installation."
        )
    templates = sorted(SYSTEMD_SOURCE_DIR.glob("*.service.template"))
    if not templates:
        raise BootstrapError(
            f"No unit templates found in {SYSTEMD_SOURCE_DIR}; nothing to render."
        )
    unit_names = ", ".join(t.name.removesuffix(".template") for t in templates)
    if not confirm(
        f"Render and install systemd units ({unit_names}) into "
        f"{SYSTEMD_TARGET_DIR}, then enable and start the services?",
        assume_yes=ctx.assume_yes,
    ):
        info("Skipping systemd provisioning.")
        return
    if os.geteuid() != 0:
        raise StepSkipped(
            "Root privileges are required to manage systemd units. "
            "Re-run this script with sudo."
        )

    service_user = _resolve_service_user(ctx)
    ctx.service_user = service_user
    node_bin_dir = str(Path(ctx.node_path or "/usr/bin/node").parent)
    substitutions = {
        "LABISH_USER": service_user,
        "LABISH_GROUP": service_user,
        "REPO_ROOT": str(REPO_ROOT),
        "VENV_BIN": str(VENV_DIR / "bin"),
        "NPM_BIN": ctx.npm_path or "/usr/bin/npm",
        "NODE_BIN_DIR": node_bin_dir,
        "QDRANT_BINARY": str(QDRANT_BINARY),
        "QDRANT_DATA_DIR": str(QDRANT_DATA_DIR),
    }

    # The services read/write inside the repo (Next.js cache, logs) and
    # Qdrant persists under /var/lib/qdrant.
    QDRANT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if service_user != "root":
        _ensure_owner(REPO_ROOT, service_user)
        _ensure_owner(QDRANT_DATA_DIR, service_user)
        if ENV_FILE_DIR.is_dir():
            run(
                ["chgrp", "-R", service_user, str(ENV_FILE_DIR)],
                cwd=REPO_ROOT,
            )

    for template in templates:
        unit_name = template.name.removesuffix(".template")
        target = SYSTEMD_TARGET_DIR / unit_name
        rendered = _render_template(template, substitutions)
        if target.is_symlink():
            # Migrate away from the legacy verbatim symlinks.
            target.unlink()
        if target.exists() and target.read_text() == rendered:
            info(f"Unit already up to date: {target}")
            continue
        target.write_text(rendered)
        info(f"Installed rendered unit: {target}")

    run(["systemctl", "daemon-reload"], cwd=REPO_ROOT)
    failed_units: list[str] = []
    for unit in SERVICE_UNITS:
        result = subprocess.run(
            ["systemctl", "enable", "--now", f"{unit}.service"], cwd=REPO_ROOT
        )
        if result.returncode != 0:
            warn(f"Failed to enable/start {unit}.service; check journalctl.")
            failed_units.append(unit)
        else:
            info(f"Enabled and started {unit}.service.")
    if ctx.db_password_rotated:
        # Already-running services still hold the old DSN.
        restart = [
            unit for unit in ("fastapi", "worker", "nextjs")
            if unit not in failed_units
        ]
        if restart:
            if _systemctl_ok("restart", *restart):
                info("Restarted services to pick up the rotated DB password.")
            else:
                failed_units.extend(restart)
    if failed_units:
        raise BootstrapError(
            "Failed to enable/start: "
            + ", ".join(f"{unit}.service" for unit in failed_units)
            + ". Inspect 'journalctl -u "
            + " -u ".join(failed_units)
            + "' for details."
        )


def check_nginx(ctx: Context) -> None:
    info("--- nginx check ---")
    if os.geteuid() != 0:
        raise StepSkipped("Root privileges required to provision nginx.")
    if not NGINX_SITES_AVAILABLE.is_dir():
        raise StepSkipped(
            "nginx sites-available directory not found; is nginx installed?"
        )
    template = DEPLOYMENT_DIR / "nginx.conf.template"
    if not template.exists():
        raise BootstrapError(f"Missing nginx template: {template}")
    if not confirm(
        f"Install the rendered nginx site (server_name {ctx.server_name}) "
        "and start/reload nginx?",
        assume_yes=ctx.assume_yes,
    ):
        info("Skipping nginx provisioning.")
        return

    rendered = _render_template(template, {"SERVER_NAME": ctx.server_name})
    site_path = NGINX_SITES_AVAILABLE / NGINX_SITE_NAME
    site_path.write_text(rendered)
    enabled = NGINX_SITES_ENABLED / NGINX_SITE_NAME
    if not enabled.exists():
        enabled.symlink_to(site_path)
    default_site = NGINX_SITES_ENABLED / "default"
    if ctx.server_name == "_" and default_site.exists():
        default_site.unlink()
        info("Disabled the stock nginx default site (catch-all conflict).")

    nginx = shutil.which("nginx") or "/usr/sbin/nginx"
    run([nginx, "-t"], cwd=REPO_ROOT)

    conflicts = _foreign_port_listeners(HTTP_PORT)
    if conflicts:
        raise BootstrapError(
            f"Port {HTTP_PORT} is already held by another process, so nginx "
            "cannot bind it. Stop/disable that service and re-run:\n"
            + "\n".join(conflicts)
        )

    if systemctl_available():
        _start_nginx_systemd()
    else:
        _start_nginx_direct(nginx)

    if _http_status(GATEWAY_URL, host=_gateway_host(ctx)) is None:
        _nginx_diagnostics()
        raise BootstrapError(
            f"nginx reports running but {GATEWAY_URL} does not answer; see "
            "the diagnostics above."
        )
    info(f"nginx site '{NGINX_SITE_NAME}' installed; gateway answering on "
         f"port {HTTP_PORT}.")


def _port_listeners(port: int) -> list[str]:
    """Return ``ss`` lines for TCP listeners on ``port`` (empty if unknown)."""
    ss = shutil.which("ss")
    if ss is None:
        return []
    result = subprocess.run(
        [ss, "-H", "-ltnp", f"sport = :{port}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _foreign_port_listeners(port: int) -> list[str]:
    """Listeners on ``port`` that belong to something other than nginx."""
    return [
        line for line in _port_listeners(port)
        if 'users:' in line and '"nginx"' not in line
    ]


def _capture(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"(could not run {' '.join(command)}: {exc})"
    return (result.stdout + result.stderr).strip()


def _nginx_diagnostics() -> None:
    """Print the evidence needed to triage an nginx start failure."""
    commands: list[list[str]] = []
    if shutil.which("systemctl"):
        commands.append(["systemctl", "status", "nginx", "--no-pager", "-l"])
    if shutil.which("journalctl"):
        commands.append(
            ["journalctl", "-xeu", "nginx", "-n", "50", "--no-pager"]
        )
    if shutil.which("ss"):
        commands.append(["ss", "-ltnp", f"sport = :{HTTP_PORT}"])
    for command in commands:
        warn(f"--- diagnostics: {' '.join(command)} ---")
        print(redact(_capture(command)), file=sys.stderr, flush=True)


def _systemctl_ok(*args: str) -> bool:
    return (
        subprocess.run(["systemctl", *args], cwd=REPO_ROOT).returncode == 0
    )


def _nginx_active() -> bool:
    return subprocess.run(
        ["systemctl", "is-active", "--quiet", "nginx"], cwd=REPO_ROOT
    ).returncode == 0


def _start_nginx_systemd() -> None:
    """Enable and (re)start nginx, recovering from a wedged apt-time daemon."""
    state = _capture(["systemctl", "is-enabled", "nginx"])
    if state.startswith("masked"):
        warn("nginx.service is masked; unmasking it.")
        run(["systemctl", "unmask", "nginx"], cwd=REPO_ROOT)
    if not _systemctl_ok("enable", "nginx"):
        warn("'systemctl enable nginx' failed; continuing to start it.")

    if _nginx_active():
        if _systemctl_ok("reload", "nginx"):
            info("Reloaded the running nginx.")
        else:
            warn("nginx reload failed; falling back to a restart.")
            _systemctl_ok("restart", "nginx")
    elif not _systemctl_ok("start", "nginx"):
        warn(
            "'systemctl start nginx' failed; clearing the failed state and "
            "falling back to 'systemctl restart nginx'."
        )
        _systemctl_ok("reset-failed", "nginx")
        _systemctl_ok("restart", "nginx")

    for _ in range(5):
        if _nginx_active():
            info("nginx.service is active.")
            return
        time.sleep(1)
    _nginx_diagnostics()
    raise BootstrapError(
        "nginx.service is not active after start/restart; see the "
        "diagnostics above (systemctl status, journalctl, port listeners)."
    )


def _nginx_pid_alive(pidfile: Path = Path("/run/nginx.pid")) -> bool:
    try:
        pid = int(pidfile.read_text().strip())
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def _start_nginx_direct(nginx: str) -> None:
    """Start/reload nginx on hosts without systemd (e.g. containers)."""
    if _nginx_pid_alive() or any(
        '"nginx"' in line for line in _port_listeners(HTTP_PORT)
    ):
        result = subprocess.run([nginx, "-s", "reload"], cwd=REPO_ROOT)
        if result.returncode == 0:
            info("Reloaded the running nginx.")
            return
        warn("nginx reload failed; attempting a fresh start.")
    if shutil.which("service"):
        subprocess.run(["service", "nginx", "start"], cwd=REPO_ROOT)
    if _http_status(GATEWAY_URL) is None:
        subprocess.run([nginx], cwd=REPO_ROOT)


def _http_status(
    url: str, *, host: str | None = None, timeout: float = 5
) -> int | None:
    """HTTP status for ``url`` (including 4xx/5xx), or None if unreachable.

    ``host`` overrides the Host header so the rendered nginx server block
    (not a stock default site) answers gateway probes.
    """
    request = urllib.request.Request(url)
    if host:
        request.add_header("Host", host)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, OSError):
        return None


def _unit_active(unit: str) -> bool:
    return subprocess.run(
        ["systemctl", "is-active", "--quiet", f"{unit}.service"],
        cwd=REPO_ROOT,
    ).returncode == 0


def _gateway_host(ctx: Context) -> str | None:
    return None if ctx.server_name == "_" else ctx.server_name


def check_health(ctx: Context) -> None:
    """Verify the provisioned stack actually answers, end to end."""
    info("--- Post-install health check ---")
    if not systemctl_available():
        raise StepSkipped("No systemd-managed services to health-check.")
    http_checks = {
        "backend /health": "http://127.0.0.1:8000/health",
        "frontend root": "http://127.0.0.1:3000/",
        "qdrant /readyz": "http://127.0.0.1:6333/readyz",
    }
    if ctx.check_gateway:
        # The path users actually hit: nginx -> Next.js / FastAPI.
        http_checks["gateway root"] = GATEWAY_URL
        http_checks["gateway /api/health"] = f"{GATEWAY_URL}api/health"

    pending = dict(http_checks)
    for attempt in range(15):
        for label, url in list(pending.items()):
            host = _gateway_host(ctx) if url.startswith(GATEWAY_URL) else None
            status = _http_status(url, host=host)
            if status is not None and status < 500:
                info(f"Healthy: {label} ({url})")
                del pending[label]
        if not pending:
            break
        if attempt < 14:
            time.sleep(2)
    failures = [f"{label} ({url})" for label, url in pending.items()]

    if _unit_active("worker"):
        info("Healthy: worker.service is active")
    else:
        failures.append("worker.service (not active)")

    if failures:
        raise BootstrapError(
            "Health check failed for: " + "; ".join(failures)
            + ". Inspect 'journalctl -u nginx -u fastapi -u nextjs -u qdrant "
            "-u worker' for details."
        )
    info("All health checks passed: " + ", ".join(
        [*http_checks, "worker.service"]
    ) + ".")


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
        "--skip-node", action="store_true",
        help="Skip the pinned Node.js toolchain step.",
    )
    parser.add_argument(
        "--skip-qdrant", action="store_true",
        help="Skip the Qdrant binary install step.",
    )
    parser.add_argument(
        "--skip-frontend", action="store_true",
        help="Skip the npm install / generate-client / build step.",
    )
    parser.add_argument(
        "--skip-db", action="store_true",
        help="Skip database provisioning and migrations.",
    )
    parser.add_argument(
        "--skip-sap-ingest", action="store_true",
        help="Skip the SAP metadata ingestion (data dictionary) prompt.",
    )
    parser.add_argument(
        "--skip-systemd", action="store_true",
        help="Skip systemd unit rendering, service start and health check.",
    )
    parser.add_argument(
        "--skip-nginx", action="store_true",
        help="Skip nginx site provisioning.",
    )
    parser.add_argument(
        "--rotate-db-password", action="store_true",
        help="Generate a new password for the PostgreSQL 'labish' role and "
        "rewrite the DSNs in /etc/labish/{api,web}.env (restart the "
        "services afterwards).",
    )
    parser.add_argument(
        "--server-name",
        default=os.environ.get("LABISH_SERVER_NAME", "_"),
        help="nginx server_name for the rendered site (default: '_').",
    )
    parser.add_argument(
        "--site-url",
        default=os.environ.get("LABISH_SITE_URL", ""),
        help="Public site origin written to NEXT_PUBLIC_SITE_URL.",
    )
    parser.add_argument(
        "--service-user",
        default=os.environ.get("LABISH_SERVICE_USER", ""),
        help="Account the systemd services run as (default: auto-detect).",
    )
    return parser.parse_args(argv)


def _execute(ctx: Context, name: str, func, *, skip: bool = False) -> None:
    """Run one provisioning step, recording its outcome instead of aborting."""
    if skip:
        info(f"Skipping step: {name} (flag).")
        ctx.record(name, "skipped", "disabled via flag")
        return
    try:
        func(ctx)
    except StepSkipped as exc:
        warn(f"{name}: {exc}")
        ctx.record(name, "skipped", str(exc))
    except StepWarning as exc:
        warn(f"{name}: {exc}")
        ctx.record(name, "warning", str(exc))
    except BootstrapError as exc:
        warn(f"{name} failed: {exc}")
        ctx.record(name, "failed", str(exc))
    else:
        ctx.record(name, "ok")


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(raw_argv)
    info(f"Repository root: {REPO_ROOT}")

    ctx = Context(
        assume_yes=args.yes,
        service_user=args.service_user,
        server_name=args.server_name,
        rotate_db_password=args.rotate_db_password,
        check_gateway=not args.skip_nginx,
        site_url=args.site_url
        or (f"http://{args.server_name}" if args.server_name != "_" else ""),
    )

    try:
        if args.skip_system:
            if os.environ.get("LABISH_SETUP_REEXEC"):
                ctx.record(
                    "System packages", "ok", "verified before venv re-exec"
                )
            else:
                info("Skipping system package check (--skip-system).")
                ctx.record("System packages", "skipped", "disabled via flag")
        else:
            _execute(ctx, "System packages", check_system_packages)
        # Everything after this point runs inside apps/api/venv.
        ensure_venv_and_reexec(raw_argv)

        _execute(ctx, "Node toolchain", check_node_toolchain, skip=args.skip_node)
        _execute(ctx, "Qdrant", check_qdrant, skip=args.skip_qdrant)
        _execute(ctx, "Python backend", check_python_backend)
        _execute(
            ctx, "OpenAPI export", export_openapi_schema,
            skip=args.skip_frontend,
        )
        _execute(ctx, "JWT keys", check_jwt_keys)
        _execute(ctx, "Database", check_database, skip=args.skip_db)
        _execute(ctx, "Frontend", check_frontend, skip=args.skip_frontend)
        _execute(ctx, "Environment files", check_env_files)
        _execute(
            ctx, "SAP ingestion", check_sap_ingestion,
            skip=args.skip_sap_ingest,
        )
        _execute(ctx, "Systemd services", check_systemd, skip=args.skip_systemd)
        _execute(ctx, "nginx", check_nginx, skip=args.skip_nginx)
        _execute(ctx, "Health check", check_health, skip=args.skip_systemd)
    except KeyboardInterrupt:
        warn("Interrupted by operator.")
        return 130

    return report_summary(ctx)


SUMMARY_MARKERS = {
    "ok": "OK  ",
    "warning": "WARN",
    "skipped": "SKIP",
    "failed": "FAIL",
}


def report_summary(ctx: Context) -> int:
    """Print the per-step summary; the exit code mirrors the aggregate state."""
    info("--- Bootstrap summary ---")
    failed: list[str] = []
    for name, status, detail in ctx.results:
        suffix = f" -- {redact(detail)}" if detail else ""
        info(f"[{SUMMARY_MARKERS[status]}] {name}{suffix}")
        if status == "failed":
            failed.append(name)
    if failed:
        warn(
            "Step(s) failed: " + ", ".join(failed) + ". The stack is NOT "
            "fully up. Fix the issues above and re-run the bootstrapper; "
            "completed steps are idempotent and will no-op."
        )
        return 1
    health = [status for name, status, _ in ctx.results if name == "Health check"]
    if health == ["ok"]:
        info("Bootstrap complete; every service passed its health check and "
             "the stack is up.")
    else:
        info("Bootstrap complete. The running stack was not health-checked "
             "end to end (see SKIP entries above).")
    systemd_ok = any(
        name == "Systemd services" and status == "ok"
        for name, status, _ in ctx.results
    )
    if ctx.db_password_rotated and not systemd_ok:
        warn("The database password was rotated; restart the services "
             "('systemctl restart fastapi worker nextjs') if they were "
             "already running.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
