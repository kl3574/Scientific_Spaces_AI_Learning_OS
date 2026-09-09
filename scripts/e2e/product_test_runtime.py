"""Test-only frontend runtime ownership; no work occurs at import time.

All rejected inputs and subprocess failures use fixed ValueError codes, never
child output. The public root argument is the repository root, not a data root.
CI prevents Next's automatic TypeScript install and lockfile patch; incomplete
installed locks still fail preflight. Native SWC is required and preloaded, with
WASM fallback disabled to prevent fallback downloads. No lock checks are waived.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
import errno
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import selectors
import shutil
import signal
import socket
import stat
import subprocess
import tempfile
import time
from typing import Iterator


DEFAULT_BACKEND_PORT = 8000
FRONTEND_PORT = 3000
PORT_ENV = "SCIENTIFIC_SPACES_E2E_BACKEND_PORT"
BUILD_TIMEOUT_SECONDS = 180
BUILD_OUTPUT_LIMIT = 256 * 1024


def validate_backend_port(value: int) -> int:
    if type(value) is not int or not 1024 <= value <= 65535 or value == FRONTEND_PORT:
        raise ValueError("invalid_backend_port")
    return value


def get_backend_port() -> int:
    value = os.environ.get(PORT_ENV)
    if value is None:
        return DEFAULT_BACKEND_PORT
    if not re.fullmatch(r"[1-9][0-9]{3,4}", value):
        raise ValueError("invalid_backend_port")
    return validate_backend_port(int(value))


def _playwright_browsers_path() -> str:
    # Installed driver registry rules, without loading the driver or downloading.
    def driver_value(name: str) -> str | None:
        for key in (name, "npm_config_" + name.lower(), "npm_package_config_" + name.lower()):
            if key in os.environ:
                return os.environ[key]
        return None

    path = driver_value("PLAYWRIGHT_BROWSERS_PATH")
    if path == "0":
        return path  # Driver-package-local hermetic browsers, not a relative path.
    if not path:
        home = os.environ.get("HOME")
        if home is None:
            home = str(Path.home())
        system = platform.system()
        if system == "Linux":
            cache = os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache")
        elif system == "Darwin":
            cache = os.path.join(home, "Library", "Caches")
        else:
            raise ValueError("unsupported_browser_platform")
        path = os.path.join(cache, "ms-playwright")
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(driver_value("INIT_CWD") or os.getcwd(), path))
    return path


def sanitized_environment() -> dict[str, str]:
    allowed = {"PATH", "HOME", "LANG", "TZ", "TMPDIR", "XDG_CACHE_HOME", "PLAYWRIGHT_BROWSERS_PATH"}
    result = {key: value for key, value in os.environ.items()
              if key in allowed or re.fullmatch(r"LC_[A-Z_]+", key)}
    result.setdefault("PATH", os.defpath)
    result["PLAYWRIGHT_BROWSERS_PATH"] = _playwright_browsers_path()
    result.update({"CI": "1", "NEXT_TELEMETRY_DISABLED": "1", "DO_NOT_TRACK": "1",
                   "NEXT_DISABLE_SWC_WASM": "1",
                   "npm_config_offline": "true", "npm_config_ignore_scripts": "true",
                   "npm_config_audit": "false", "npm_config_fund": "false",
                   "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1"})
    return result


@contextmanager
def process_environment(environment: dict[str, str]) -> Iterator[None]:
    """CLI-only process-global scope spanning driver/browser startup and teardown.

    Pass the sanitized/configured map; do not run concurrent suites in this
    process. Neither caller mutations nor body mutations alter the saved maps.
    """
    configured = dict(environment)
    previous = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(configured)
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


@dataclass(frozen=True)
class FrontendRuntime:
    frontend_root: Path
    backend_port: int
    environment: dict[str, str]
    evidence: dict[str, str | int | bool] = field(default_factory=dict)

    @property
    def api_url(self) -> str:
        return f"http://127.0.0.1:{self.backend_port}"

    @property
    def browser_api_url(self) -> str:
        return f"http://localhost:{self.backend_port}"


def require_port_free(port: int) -> None:
    """Bind only; never connect to, inspect, or signal an existing service."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("invalid_port")
    try:
        for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
            try:
                with socket.socket(family, socket.SOCK_STREAM) as probe:
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    if family == socket.AF_INET6:
                        probe.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                    probe.bind((address, port))
            except OSError as error:
                if family == socket.AF_INET6 and error.errno in (errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL):
                    continue
                raise
    except OSError:
        raise ValueError("port_unavailable") from None


def _regular_file(root: Path, relative: str) -> Path:
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("unsafe_source_path")
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("unsafe_source_path")
    return path


def _tracked_inputs(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "frontend/"],
            env=sanitized_environment(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=10, check=False,
        )
        if result.returncode or not result.stdout.endswith(b"\0"):
            raise ValueError("input_inventory_failed")
        paths = result.stdout[:-1].decode("utf-8").split("\0")
    except (OSError, UnicodeError, subprocess.SubprocessError):
        raise ValueError("input_inventory_failed") from None
    excluded = {"node_modules", ".next", ".git", ".local_data", ".cache", "cache", "runtime",
                "coverage", "dist", "build", "out", ".turbo", ".npmrc", ".yarnrc", ".yarnrc.yml"}
    root_inputs = {"package.json", "package-lock.json", "next-env.d.ts", "next.config.mjs",
                   "next.config.js", "next.config.ts", "tsconfig.json", "postcss.config.mjs",
                   "postcss.config.js", "tailwind.config.js", "tailwind.config.ts"}
    selected = []
    for name in paths:
        parts = name.split("/")
        if len(parts) < 2 or parts[0] != "frontend" or any(part in ("", ".", "..") for part in parts):
            raise ValueError("unsafe_source_path")
        relative = "/".join(parts[1:])
        if any(part in excluded or part.startswith(".env") or part.endswith(".tsbuildinfo") for part in parts[1:]):
            continue
        if parts[1] not in {"src", "public", "tests", "scripts"} and relative not in root_inputs:
            continue
        _regular_file(root / "frontend", relative)
        selected.append(relative)
    if len(selected) != len(set(selected)) or not {"package.json", "package-lock.json", "tsconfig.json"} <= set(selected):
        raise ValueError("input_inventory_failed")
    if not any(path.startswith("src/") for path in selected):
        raise ValueError("input_inventory_failed")
    return sorted(selected)


def _file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _inputs_hash(frontend: Path, inputs: list[str]) -> str:
    digest = hashlib.sha256()
    for relative in inputs:
        path = _regular_file(frontend, relative)
        digest.update(json.dumps([relative, stat.S_IMODE(path.stat().st_mode), _file_hash(path)]).encode())
    return digest.hexdigest()


def _tree_hash(root: Path) -> str:
    """Hash contents, including internal link targets, without following links."""
    digest = hashlib.sha256()
    if not root.exists() and not root.is_symlink():
        return hashlib.sha256(b"absent").hexdigest()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("unsafe_shared_tree")
    def unreadable(_error: OSError) -> None:
        raise ValueError("shared_tree_unreadable") from None

    for directory, directories, files in os.walk(root, followlinks=False, onerror=unreadable):
        directories.sort()
        for name in sorted(directories + files):
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                try:
                    contained = path.resolve(strict=True).is_relative_to(root.resolve())
                except (OSError, RuntimeError):
                    raise ValueError("unsafe_shared_tree") from None
                if not contained:
                    raise ValueError("unsafe_shared_tree")
                content = os.readlink(path)
            elif stat.S_ISREG(mode):
                content = _file_hash(path)
            elif stat.S_ISDIR(mode):
                content = "directory"
            else:
                raise ValueError("unsafe_shared_tree")
            digest.update(json.dumps([path.relative_to(root).as_posix(), mode, content]).encode())
    return digest.hexdigest()


def _native_package() -> str:
    architecture = {"x86_64": "x64", "AMD64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine())
    system = platform.system()
    if not architecture or system not in {"Linux", "Darwin"}:
        raise ValueError("native_dependency_unavailable")
    if system == "Darwin":
        return f"@next/swc-darwin-{architecture}"
    libc = platform.libc_ver()[0]
    if libc not in {"glibc", "musl"}:
        raise ValueError("native_dependency_unavailable")
    return f"@next/swc-linux-{architecture}-{'gnu' if libc == 'glibc' else 'musl'}"


def _verify_dependencies(frontend: Path) -> None:
    dependencies = frontend / "node_modules"
    if dependencies.is_symlink() or not dependencies.is_dir():
        raise ValueError("invalid_dependencies")
    try:
        manifest = json.loads(_regular_file(frontend, "package.json").read_bytes())
        lock = json.loads(_regular_file(frontend, "package-lock.json").read_bytes())
        installed = json.loads(_regular_file(dependencies, ".package-lock.json").read_bytes())
        if lock["lockfileVersion"] != 3 or installed["lockfileVersion"] != 3:
            raise ValueError
        packages = lock["packages"]
        installed_packages = installed["packages"]
        for kind in ("dependencies", "devDependencies", "optionalDependencies"):
            if manifest.get(kind, {}) != packages[""].get(kind, {}):
                raise ValueError
        for relative, entry in installed_packages.items():
            parts = relative.split("/")
            if parts[0] != "node_modules" or any(part in ("", ".", "..") for part in parts) or entry.get("link"):
                raise ValueError
            expected = packages[relative]
            if any(entry.get(key) != expected.get(key) for key in ("version", "integrity", "resolved")):
                raise ValueError
            package = json.loads(_regular_file(frontend, relative + "/package.json").read_bytes())
            if package["version"] != entry["version"]:
                raise ValueError
        for name in {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}:
            if "node_modules/" + name not in installed_packages:
                raise ValueError
        native = _native_package()
        if "node_modules/" + native not in installed_packages:
            raise ValueError
        next_package = json.loads(_regular_file(dependencies, "next/package.json").read_bytes())
        swc_packages = {name: version for name, version in next_package.get("optionalDependencies", {}).items()
                        if name.startswith("@next/swc-")}
        if native not in swc_packages:
            raise ValueError
        for name, version in swc_packages.items():
            if packages["node_modules/" + name]["version"] != version:
                raise ValueError
        for relative in ("next/dist/bin/next", "typescript/lib/typescript.js", "@types/react/index.d.ts", "@types/node/index.d.ts"):
            _regular_file(dependencies, relative)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("invalid_dependencies") from None


def _stop_owned_process(process: subprocess.Popen) -> None:
    try:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        # Also retire children left in the owned session after the leader exits.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)
    except (OSError, subprocess.SubprocessError):
        raise ValueError("build_cleanup_failed") from None
    finally:
        if process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:
                raise ValueError("build_cleanup_failed") from None


def _run_owned(command: list[str], frontend: Path, environment: dict[str, str], *, timeout: float) -> int:
    try:
        process = subprocess.Popen(command, cwd=frontend, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    except (OSError, ValueError):
        raise ValueError("build_start_failed") from None
    count = 0
    try:
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError("build_timeout")
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    count += len(chunk)
                    if count > BUILD_OUTPUT_LIMIT:
                        raise ValueError("build_output_limit")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("build_timeout")
            if process.wait(timeout=remaining) != 0:
                raise ValueError("build_failed")
    except subprocess.TimeoutExpired:
        raise ValueError("build_timeout") from None
    except OSError:
        raise ValueError("build_io_failed") from None
    finally:
        _stop_owned_process(process)
    return count


def _build_frontend(frontend_root: Path, environment: dict[str, str]) -> int:
    node = shutil.which("node", path=environment["PATH"])
    if node is None:
        raise ValueError("node_unavailable")
    native = frontend_root / "node_modules" / _native_package()
    # Preload the installed native binary before Next can attempt a fallback download.
    count = _run_owned([node, "-e", "require(process.argv[1])", str(native)], frontend_root, environment, timeout=10)
    return count + _run_owned([node, str(frontend_root / "node_modules/next/dist/bin/next"), "build"],
                              frontend_root, environment, timeout=BUILD_TIMEOUT_SECONDS)


@contextmanager
def frontend_runtime(root: Path, *, backend_port: int | None = None,
                     frontend_mode: str = "start") -> Iterator[FrontendRuntime]:
    """Caller owns server groups; exit only after stopping every start/restart.

    Custom-port evidence hashes bind copied inputs, shared dependencies/build,
    and the actual temporary production build. This is verification, not a
    filesystem or network sandbox. Default 8000 retains the shared CI runtime.
    """
    port = get_backend_port() if backend_port is None else validate_backend_port(backend_port)
    if frontend_mode not in ("start", "dev"):
        raise ValueError("invalid_frontend_mode")
    if port != DEFAULT_BACKEND_PORT and frontend_mode != "start":
        raise ValueError("custom_port_requires_start")
    frontend = root.absolute() / "frontend"
    if frontend.is_symlink() or not frontend.is_dir() or frontend.resolve() != frontend:
        raise ValueError("unsafe_source_path")
    require_port_free(port)
    require_port_free(FRONTEND_PORT)
    environment = sanitized_environment()
    environment.update({PORT_ENV: str(port), "NEXT_PUBLIC_API_BASE_URL": f"http://localhost:{port}",
                        "NODE_ENV": "production" if frontend_mode == "start" else "development"})
    if port == DEFAULT_BACKEND_PORT:
        yield FrontendRuntime(frontend, port, environment, {"isolated": False})
        return
    evidence: dict[str, str | int | bool] = {"isolated": True, "copy_verified": False,
        "bindings_stable": False, "cleanup_complete": False}
    try:
        inputs = _tracked_inputs(root)
        _verify_dependencies(frontend)
        initial = (_inputs_hash(frontend, inputs), _tree_hash(frontend / ".next"), _tree_hash(frontend / "node_modules"))
        evidence.update({"inputs_sha256": initial[0], "shared_build_sha256": initial[1], "dependencies_sha256": initial[2]})

        def verify_shared() -> None:
            current = (_inputs_hash(frontend, inputs), _tree_hash(frontend / ".next"), _tree_hash(frontend / "node_modules"))
            if current != initial or _tracked_inputs(root) != inputs:
                raise ValueError("shared_state_changed")

        temporary = tempfile.TemporaryDirectory(prefix="scientific-spaces-e2e-frontend-")
        try:
            owned = Path(temporary.name) / "frontend"
            owned.mkdir()
            for key, name in (("HOME", "home"), ("TMPDIR", "tmp"), ("XDG_CACHE_HOME", "cache")):
                directory = Path(temporary.name) / name
                directory.mkdir()
                environment[key] = str(directory)
            for relative in inputs:
                destination = owned / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(_regular_file(frontend, relative), destination)
            if _inputs_hash(owned, inputs) != initial[0]:
                raise ValueError("copy_verification_failed")
            evidence["copy_verified"] = True
            (owned / "node_modules").symlink_to(frontend / "node_modules", target_is_directory=True)
            evidence["build_output_bytes"] = _build_frontend(owned, environment)
            if _inputs_hash(owned, inputs) != initial[0]:
                raise ValueError("copy_verification_failed")
            try:
                build_id = _regular_file(owned, ".next/BUILD_ID")
                if not 0 < build_id.stat().st_size <= 1024:
                    raise ValueError
            except (OSError, ValueError):
                raise ValueError("invalid_build") from None
            evidence["build_sha256"] = _tree_hash(owned / ".next")
            verify_shared()
            yield FrontendRuntime(owned, port, environment, evidence)
        finally:
            try:
                verify_shared()
                evidence["bindings_stable"] = True
            finally:
                try:
                    temporary.cleanup()
                except OSError:
                    raise ValueError("runtime_cleanup_failed") from None
                evidence["cleanup_complete"] = not Path(temporary.name).exists()
                if not evidence["cleanup_complete"]:
                    raise ValueError("runtime_cleanup_failed")
    except (OSError, UnicodeError, shutil.Error):
        raise ValueError("runtime_io_failed") from None
