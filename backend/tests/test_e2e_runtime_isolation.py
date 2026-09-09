"""Synthetic-only contracts; never build the shared project or contact a service."""

import importlib.util
import errno
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/e2e/product_test_runtime.py"


@pytest.fixture
def runtime_module():
    spec = importlib.util.spec_from_file_location("product_runtime_contract", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def test_backend_port_defaults_and_strict_override(runtime_module, monkeypatch):
    monkeypatch.delenv("SCIENTIFIC_SPACES_E2E_BACKEND_PORT", raising=False)
    assert runtime_module.get_backend_port() == 8000
    monkeypatch.setenv("SCIENTIFIC_SPACES_E2E_BACKEND_PORT", "18000")
    assert runtime_module.get_backend_port() == 18000


@pytest.mark.parametrize("value", ["", " 18000", "+18000", "018000", "18000.0", "1e4", "0",
                                   "1023", "3000", "65536", "PRIVATE_SENTINEL", "１８０００"])
def test_invalid_port_never_falls_back_or_echoes_input(runtime_module, monkeypatch, value):
    monkeypatch.setenv("SCIENTIFIC_SPACES_E2E_BACKEND_PORT", value)
    with pytest.raises(ValueError, match="^invalid_backend_port$"):
        runtime_module.get_backend_port()


def test_environment_is_allowlisted_without_secrets_or_runtime_injection(runtime_module, monkeypatch):
    monkeypatch.setattr(runtime_module.os, "environ", {
        "PATH": "/usr/bin", "HOME": "/synthetic/home", "LANG": "C.UTF-8", "LC_ALL": "C",
        "TZ": "UTC", "TMPDIR": "/synthetic/tmp", "XDG_CACHE_HOME": "/synthetic/cache",
        "PLAYWRIGHT_BROWSERS_PATH": "/synthetic/browsers", "NODE_OPTIONS": "PRIVATE_SENTINEL",
        "PYTHONPATH": "PRIVATE_SENTINEL", "OPENAI_API_KEY": "PRIVATE_SENTINEL",
        "SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER": "PRIVATE_SENTINEL", "npm_config_registry": "PRIVATE_SENTINEL",
        "HTTP_PROXY": "PRIVATE_SENTINEL", "NEXT_PUBLIC_API_BASE_URL": "PRIVATE_SENTINEL",
    })
    environment = runtime_module.sanitized_environment()
    assert environment["PATH"] == "/usr/bin" and environment["HOME"] == "/synthetic/home"
    assert environment["LC_ALL"] == "C" and environment["PLAYWRIGHT_BROWSERS_PATH"] == "/synthetic/browsers"
    assert environment["NEXT_TELEMETRY_DISABLED"] == "1"
    assert environment["CI"] == "1"
    assert environment["npm_config_offline"] == "true"
    assert "NEXT_IGNORE_INCORRECT_LOCKFILE" not in environment
    assert "PRIVATE_SENTINEL" not in repr(environment)
    assert "NODE_OPTIONS" not in environment and "PYTHONPATH" not in environment


@pytest.mark.parametrize("outcome", ["normal", "error", "interrupt"])
def test_process_environment_replaces_defensively_and_restores_exactly(runtime_module, monkeypatch, tmp_path, capsys, outcome):
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_SENTINEL")
    monkeypatch.setenv("NODE_OPTIONS", "PRIVATE_SENTINEL")
    monkeypatch.setenv("PYTHONPATH", "PRIVATE_SENTINEL")
    previous = dict(runtime_module.os.environ)
    configured = {"PATH": runtime_module.os.defpath, "HOME": str(tmp_path),
                  "PLAYWRIGHT_BROWSERS_PATH": str(tmp_path / "cached-browsers"),
                  "SCIENTIFIC_SPACES_E2E_BACKEND_PORT": "18000"}
    expected = dict(configured)
    failure = {"normal": None, "error": RuntimeError("caller_failure"), "interrupt": KeyboardInterrupt()}[outcome]

    def execute():
        with runtime_module.process_environment(configured):
            assert dict(runtime_module.os.environ) == expected
            assert "PRIVATE_SENTINEL" not in repr(dict(runtime_module.os.environ))
            configured["NODE_OPTIONS"] = "PRIVATE_SENTINEL"
            assert "NODE_OPTIONS" not in runtime_module.os.environ
            runtime_module.os.environ["BODY_MUTATION"] = "temporary"
            assert "BODY_MUTATION" not in configured
            if failure is not None:
                raise failure

    if failure is None:
        execute()
    else:
        with pytest.raises(type(failure)) as caught:
            execute()
        assert caught.value is failure
    assert dict(runtime_module.os.environ) == previous
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("system,xdg,expected", [
    ("Linux", None, "/source/home/.cache/ms-playwright"),
    ("Linux", "", "/source/home/.cache/ms-playwright"),
    ("Linux", "/source/cache", "/source/cache/ms-playwright"),
    ("Darwin", "/ignored/cache", "/source/home/Library/Caches/ms-playwright"),
])
def test_default_browser_cache_is_pinned_before_home_changes(runtime_module, monkeypatch, system, xdg, expected):
    original = {"HOME": "/source/home", "PATH": "/usr/bin", "NODE_OPTIONS": "PRIVATE_SENTINEL"}
    if xdg is not None:
        original["XDG_CACHE_HOME"] = xdg
    monkeypatch.setattr(runtime_module.os, "environ", original)
    monkeypatch.setattr(runtime_module.platform, "system", lambda: system)
    environment = runtime_module.sanitized_environment()
    assert environment["PLAYWRIGHT_BROWSERS_PATH"] == expected
    environment.update({"HOME": "/owned/home", "XDG_CACHE_HOME": "/owned/cache"})
    with runtime_module.process_environment(environment):
        assert runtime_module.sanitized_environment()["PLAYWRIGHT_BROWSERS_PATH"] == expected
        assert "NODE_OPTIONS" not in runtime_module.os.environ


@pytest.mark.parametrize("explicit,initial,expected", [
    ("0", "/initial", "0"),
    ("/cached/browsers", "/initial", "/cached/browsers"),
    ("cached/../browsers", "/initial", "/initial/browsers"),
    ("cached/browsers", None, "/working/cached/browsers"),
    ("", None, "/source/home/.cache/ms-playwright"),
])
def test_explicit_browser_path_matches_driver_resolution(runtime_module, monkeypatch, explicit, initial, expected):
    original = {"HOME": "/source/home", "PLAYWRIGHT_BROWSERS_PATH": explicit}
    if initial is not None:
        original["INIT_CWD"] = initial
    monkeypatch.setattr(runtime_module.os, "environ", original)
    monkeypatch.setattr(runtime_module.os, "getcwd", lambda: "/working")
    monkeypatch.setattr(runtime_module.platform, "system", lambda: "Linux")
    environment = runtime_module.sanitized_environment()
    assert environment["PLAYWRIGHT_BROWSERS_PATH"] == expected
    assert "INIT_CWD" not in environment
    monkeypatch.setattr(runtime_module.os, "getcwd", lambda: "/owned/frontend")
    with runtime_module.process_environment(environment):
        assert runtime_module.sanitized_environment()["PLAYWRIGHT_BROWSERS_PATH"] == expected


@pytest.mark.parametrize("prefix", ["npm_config_", "npm_package_config_"])
def test_browser_cache_alias_is_resolved_without_retaining_npm_environment(runtime_module, monkeypatch, prefix):
    monkeypatch.setattr(runtime_module.os, "environ", {
        "HOME": "/source/home", prefix + "playwright_browsers_path": "cached",
        prefix + "init_cwd": "/initial", "npm_config_registry": "PRIVATE_SENTINEL",
    })
    environment = runtime_module.sanitized_environment()
    assert environment["PLAYWRIGHT_BROWSERS_PATH"] == "/initial/cached"
    assert "PRIVATE_SENTINEL" not in repr(environment)
    assert prefix + "init_cwd" not in environment
    assert prefix + "playwright_browsers_path" not in environment


@pytest.fixture
def synthetic_repo(runtime_module, tmp_path, monkeypatch):
    root = tmp_path / "repo"
    frontend = root / "frontend"
    frontend.mkdir(parents=True)
    packages = {"next": "15.5.24", "typescript": "5.7.3", "@types/node": "22.10.10",
                "@types/react": "19.0.3", "@next/swc-linux-x64-gnu": "15.5.24"}
    manifest = {"name": "synthetic", "version": "1", "dependencies": packages}
    locked = {"": manifest, **{"node_modules/" + name: {"version": version, "integrity": "fixed"}
                               for name, version in packages.items()}}
    inputs = {"package.json": json.dumps(manifest),
              "package-lock.json": json.dumps({"lockfileVersion": 3, "packages": locked}),
              "next.config.mjs": "export default {};", "tsconfig.json": "{}", "next-env.d.ts": "// fixed\n",
              "src/app/page.tsx": "export default function Page() { return null; }"}
    for relative, content in inputs.items():
        path = frontend / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    dependencies = frontend / "node_modules"
    for name, version in packages.items():
        path = dependencies / name / "package.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        package = {"name": name, "version": version}
        if name == "next":
            package["optionalDependencies"] = {"@next/swc-linux-x64-gnu": version}
        path.write_text(json.dumps(package), encoding="utf-8")
    (dependencies / ".package-lock.json").write_text(json.dumps({"lockfileVersion": 3,
        "packages": {key: value for key, value in locked.items() if key}}), encoding="utf-8")
    for relative in ("next/dist/bin/next", "typescript/lib/typescript.js", "@types/node/index.d.ts",
                     "@types/react/index.d.ts", "@next/swc-linux-x64-gnu/next-swc.linux-x64-gnu.node"):
        path = dependencies / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic dependency", encoding="utf-8")
    (dependencies / ".bin").mkdir()
    (dependencies / ".bin/next").symlink_to("../next/dist/bin/next")
    (frontend / ".next").mkdir()
    (frontend / ".next/BUILD_ID").write_text("shared-build", encoding="utf-8")
    for relative in (".env", ".env.production.local", ".npmrc", ".next/cache/private", ".local_data/private", "src/.env.local"):
        path = frontend / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("PRIVATE_SENTINEL", encoding="utf-8")
    tracked = ["frontend/" + path for path in inputs]
    tracked += ["frontend/.env", "frontend/.next/cache/private", "frontend/.local_data/private", "frontend/src/.env.local"]
    git = Mock(return_value=SimpleNamespace(returncode=0, stdout=("\0".join(tracked) + "\0").encode()))
    monkeypatch.setattr(runtime_module.subprocess, "run", git)
    monkeypatch.setattr(runtime_module, "require_port_free", Mock())
    monkeypatch.setattr(runtime_module, "_native_package", lambda: "@next/swc-linux-x64-gnu")
    monkeypatch.setattr(runtime_module.shutil, "which", lambda *args, **kwargs: "/usr/bin/node")
    built = []

    def build(frontend_root, environment):
        built.append((frontend_root, dict(environment)))
        assert frontend_root != frontend
        assert environment["NEXT_PUBLIC_API_BASE_URL"] == "http://localhost:18000"
        assert (frontend_root / "node_modules").is_symlink()
        assert (frontend_root / "node_modules").resolve() == dependencies
        for relative, content in inputs.items():
            assert (frontend_root / relative).read_text(encoding="utf-8") == content
        for relative in (".env", ".env.production.local", ".npmrc", ".local_data", "src/.env.local", ".next"):
            assert not (frontend_root / relative).exists()
        (frontend_root / ".next").mkdir()
        (frontend_root / ".next/BUILD_ID").write_text("owned-build", encoding="utf-8")
        return 123

    monkeypatch.setattr(runtime_module, "_build_frontend", build)
    return SimpleNamespace(root=root, frontend=frontend, dependencies=dependencies, inputs=inputs,
                           built=built, git=git, build=build)


def test_default_reuses_frontend_without_copy_or_build(runtime_module, synthetic_repo):
    with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=8000) as runtime:
        assert runtime.frontend_root == synthetic_repo.frontend
        assert runtime.backend_port == 8000
        assert runtime.api_url == "http://127.0.0.1:8000"
        assert runtime.browser_api_url == "http://localhost:8000"
        assert runtime.evidence["isolated"] is False
    assert synthetic_repo.built == []
    assert synthetic_repo.frontend.exists()


def test_custom_port_builds_owned_copy_and_removes_only_owned_runtime(runtime_module, synthetic_repo):
    with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000) as runtime:
        owned = runtime.frontend_root
        assert runtime.api_url == "http://127.0.0.1:18000"
        assert runtime.browser_api_url == "http://localhost:18000"
        assert runtime.environment["NEXT_PUBLIC_API_BASE_URL"] == runtime.browser_api_url
        assert runtime.evidence["copy_verified"] is True
        assert runtime.evidence["build_sha256"]
        assert len(synthetic_repo.built) == 1
    assert not owned.exists()
    assert runtime.evidence["cleanup_complete"] and runtime.evidence["bindings_stable"]
    assert (synthetic_repo.frontend / ".next/BUILD_ID").read_text() == "shared-build"
    assert synthetic_repo.dependencies.is_dir()


@pytest.mark.parametrize("port,mode,error", [(True, "start", "invalid_backend_port"),
    (18000.0, "start", "invalid_backend_port"), (3000, "start", "invalid_backend_port"),
    (18000, "dev", "custom_port_requires_start"), (8000, "PRIVATE_SENTINEL", "invalid_frontend_mode")])
def test_invalid_configuration_never_builds(runtime_module, synthetic_repo, port, mode, error):
    with pytest.raises(ValueError, match="^" + error + "$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=port, frontend_mode=mode):
            pytest.fail("invalid runtime admitted")
    assert not synthetic_repo.built


def test_selected_ports_only_and_default_dev_compatibility(runtime_module, synthetic_repo):
    with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
        pass
    assert [call.args[0] for call in runtime_module.require_port_free.call_args_list] == [18000, 3000]
    with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=8000, frontend_mode="dev") as runtime:
        assert runtime.environment["NODE_ENV"] == "development"
    assert runtime_module.validate_backend_port(1024) == 1024
    assert runtime_module.validate_backend_port(65535) == 65535


@pytest.mark.parametrize("occupied", [18000, 3000])
def test_occupied_port_stops_before_copy_or_build(runtime_module, synthetic_repo, monkeypatch, occupied):
    def check(port):
        if port == occupied:
            raise ValueError("port_unavailable")
    monkeypatch.setattr(runtime_module, "require_port_free", check)
    with pytest.raises(ValueError, match="^port_unavailable$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("occupied port admitted")
    assert not synthetic_repo.built
    synthetic_repo.git.assert_not_called()


def test_port_probe_only_binds_and_closes_on_error(runtime_module, monkeypatch):
    probe = MagicMock()
    probe.__enter__.return_value = probe
    monkeypatch.setattr(runtime_module.socket, "socket", Mock(return_value=probe))
    runtime_module.require_port_free(18000)
    assert [call.args[0] for call in probe.bind.call_args_list] == [("127.0.0.1", 18000), ("::1", 18000)]
    probe.connect.assert_not_called()
    probe.connect_ex.assert_not_called()
    assert sum(call.args == (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
               for call in probe.setsockopt.call_args_list) == 2
    assert not any(call.args[1] == socket.SO_REUSEPORT for call in probe.setsockopt.call_args_list)
    probe.bind.side_effect = OSError(errno.EADDRINUSE, "PRIVATE_SENTINEL")
    with pytest.raises(ValueError, match="^port_unavailable$"):
        runtime_module.require_port_free(18000)
    assert probe.__exit__.call_count == 3


@pytest.mark.parametrize("extra", ["backend/private", "frontend/../private", "/frontend/src/private",
                                   "frontend/src//private", "frontend/src/./private"])
def test_cross_source_inventory_rejected(runtime_module, synthetic_repo, extra):
    synthetic_repo.git.return_value.stdout += extra.encode() + b"\0"
    with pytest.raises(ValueError, match="^unsafe_source_path$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("unsafe path admitted")
    assert not synthetic_repo.built


@pytest.mark.parametrize("ancestor", [False, True])
def test_source_symlink_rejected_even_when_target_is_inside_repo(runtime_module, synthetic_repo, ancestor):
    if ancestor:
        source = synthetic_repo.frontend / "src"
        target = synthetic_repo.frontend / "src-real"
    else:
        source = synthetic_repo.frontend / "src/app/page.tsx"
        target = synthetic_repo.frontend / "src/app/page-real.tsx"
    source.rename(target)
    source.symlink_to(target, target_is_directory=ancestor)
    with pytest.raises(ValueError, match="^unsafe_source_path$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("source symlink admitted")


@pytest.mark.parametrize("broken", ["lock", "installed_version", "missing_native", "missing_types", "escaping_link"])
def test_dependency_preflight_rejects_unlocked_or_missing_inputs(runtime_module, synthetic_repo, broken):
    dependencies = synthetic_repo.dependencies
    if broken == "lock":
        path = dependencies / ".package-lock.json"
        value = json.loads(path.read_text())
        value["packages"]["node_modules/next"]["integrity"] = "PRIVATE_SENTINEL"
        path.write_text(json.dumps(value))
    elif broken == "installed_version":
        (dependencies / "next/package.json").write_text('{"version":"PRIVATE_SENTINEL"}')
    elif broken == "missing_native":
        (dependencies / "@next/swc-linux-x64-gnu/package.json").unlink()
    elif broken == "missing_types":
        (dependencies / "@types/node/index.d.ts").unlink()
    else:
        (dependencies / "escape").symlink_to(synthetic_repo.frontend / "package.json")
    with pytest.raises(ValueError, match="^(invalid_dependencies|unsafe_shared_tree)$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("invalid dependencies admitted")
    assert not synthetic_repo.built


@pytest.mark.parametrize("relative", ["src/app/page.tsx", ".next/BUILD_ID", "node_modules/next/dist/bin/next"])
@pytest.mark.parametrize("phase", ["build", "use"])
def test_shared_content_drift_fails_and_cleans_without_reverting(runtime_module, synthetic_repo, monkeypatch, relative, phase):
    changed = synthetic_repo.frontend / relative
    def build(owned, environment):
        count = synthetic_repo.build(owned, environment)
        if phase == "build":
            changed.write_text("changed-by-other-owner")
        return count
    monkeypatch.setattr(runtime_module, "_build_frontend", build)
    with pytest.raises(ValueError, match="^shared_state_changed$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            changed.write_text("changed-by-other-owner")
    assert changed.read_text() == "changed-by-other-owner"
    assert not synthetic_repo.built[0][0].exists()


def test_copy_corruption_fails_before_build_and_removes_temp(runtime_module, synthetic_repo, monkeypatch):
    original = runtime_module.shutil.copy2
    copied = []
    def corrupt(source, destination):
        copied.append(destination)
        original(source, destination)
        destination.write_text("PRIVATE_SENTINEL")
    monkeypatch.setattr(runtime_module.shutil, "copy2", corrupt)
    with pytest.raises(ValueError, match="^copy_verification_failed$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("corrupt copy admitted")
    assert not synthetic_repo.built
    assert copied and not any(path.exists() for path in copied)


def test_build_may_not_rewrite_copied_inputs(runtime_module, synthetic_repo, monkeypatch):
    def rewrite(owned, environment):
        count = synthetic_repo.build(owned, environment)
        (owned / "next-env.d.ts").write_text("PRIVATE_SENTINEL")
        return count
    monkeypatch.setattr(runtime_module, "_build_frontend", rewrite)
    with pytest.raises(ValueError, match="^copy_verification_failed$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("modified build inputs admitted")
    assert not synthetic_repo.built[0][0].exists()


@pytest.mark.parametrize("failure", ["build_start_failed", "build_failed", "build_timeout", "build_output_limit"])
def test_build_failure_removes_owned_directory(runtime_module, synthetic_repo, monkeypatch, failure):
    owned_paths = []
    def fail(owned, environment):
        owned_paths.append(owned)
        raise ValueError(failure)
    monkeypatch.setattr(runtime_module, "_build_frontend", fail)
    with pytest.raises(ValueError, match="^" + failure + "$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("failed build admitted")
    assert owned_paths and not owned_paths[0].exists()
    assert (synthetic_repo.frontend / ".next/BUILD_ID").read_text() == "shared-build"


def test_caller_failure_preserved_after_cleanup(runtime_module, synthetic_repo):
    with pytest.raises(RuntimeError, match="^caller_failure$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000) as runtime:
            raise RuntimeError("caller_failure")
    assert not runtime.frontend_root.exists()
    assert runtime.evidence["cleanup_complete"] and runtime.evidence["bindings_stable"]


@pytest.mark.parametrize("kind", ["missing", "empty", "oversized", "symlink"])
def test_build_id_required_from_actual_owned_build(runtime_module, synthetic_repo, monkeypatch, kind):
    def invalid(owned, environment):
        count = synthetic_repo.build(owned, environment)
        path = owned / ".next/BUILD_ID"
        if kind in {"missing", "symlink"}:
            path.unlink()
            if kind == "symlink":
                path.symlink_to(synthetic_repo.frontend / ".next/BUILD_ID")
        else:
            path.write_text("" if kind == "empty" else "x" * 1025)
        return count
    monkeypatch.setattr(runtime_module, "_build_frontend", invalid)
    with pytest.raises(ValueError, match="^invalid_build$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("invalid build admitted")
    assert not synthetic_repo.built[0][0].exists()


def test_missing_other_platform_swc_lock_is_not_waived(runtime_module, synthetic_repo):
    path = synthetic_repo.dependencies / "next/package.json"
    value = json.loads(path.read_text())
    value["optionalDependencies"]["@next/swc-darwin-arm64"] = "15.5.24"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="^invalid_dependencies$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000):
            pytest.fail("incomplete lock admitted")


@pytest.mark.parametrize("explicit_cache", [False, True])
def test_owned_home_tmp_and_cache_propagate_to_build_and_runtime(runtime_module, synthetic_repo, monkeypatch, explicit_cache):
    monkeypatch.setenv("HOME", str(synthetic_repo.root / "private-home"))
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_SENTINEL")
    monkeypatch.setattr(runtime_module.platform, "system", lambda: "Linux")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    for key in ("PLAYWRIGHT_BROWSERS_PATH", "npm_config_playwright_browsers_path", "npm_package_config_playwright_browsers_path"):
        monkeypatch.delenv(key, raising=False)
    expected_cache = synthetic_repo.root / "private-home/.cache/ms-playwright"
    if explicit_cache:
        expected_cache = synthetic_repo.root / "cached-browsers"
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(expected_cache))
    with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000) as runtime:
        for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME"):
            directory = Path(runtime.environment[key])
            assert directory.is_dir() and directory.is_relative_to(runtime.frontend_root.parent)
        assert synthetic_repo.built[0][1] == runtime.environment
        assert runtime.environment["PLAYWRIGHT_BROWSERS_PATH"] == str(expected_cache)
        assert "PRIVATE_SENTINEL" not in repr(runtime.environment) + repr(runtime.evidence)
    assert not any(Path(runtime.environment[key]).exists() for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME"))


@pytest.fixture
def owned_process(runtime_module, monkeypatch):
    process = Mock(pid=456789)
    process.stdout.fileno.return_value = 99
    process.wait.return_value = 0
    popen = Mock(return_value=process)
    kill = Mock()
    monkeypatch.setattr(runtime_module.subprocess, "Popen", popen)
    monkeypatch.setattr(runtime_module.os, "killpg", kill)
    monkeypatch.setattr(runtime_module.os, "read", Mock(side_effect=[b"PRIVATE_SENTINEL", b""]))
    key = SimpleNamespace(fileobj=process.stdout)
    selector = MagicMock()
    selector.__enter__.return_value = selector
    selector.get_map.return_value = {99: key}
    selector.select.return_value = [(key, 1)]
    selector.unregister.side_effect = lambda _: setattr(selector.get_map, "return_value", {})
    monkeypatch.setattr(runtime_module.selectors, "DefaultSelector", Mock(return_value=selector))
    return SimpleNamespace(process=process, popen=popen, kill=kill, selector=selector)


@pytest.mark.parametrize("outcome", ["success", "nonzero", "timeout", "output_limit", "io_error"])
def test_owned_process_bounds_output_and_cleans_every_exit(runtime_module, owned_process, tmp_path, monkeypatch, capsys, outcome):
    expected = {"nonzero": "build_failed", "timeout": "build_timeout", "output_limit": "build_output_limit", "io_error": "build_io_failed"}
    if outcome == "nonzero":
        owned_process.process.wait.return_value = 1
    elif outcome == "timeout":
        monkeypatch.setattr(runtime_module.time, "monotonic", Mock(side_effect=[0, 2]))
    elif outcome == "output_limit":
        monkeypatch.setattr(runtime_module, "BUILD_OUTPUT_LIMIT", 4)
    elif outcome == "io_error":
        runtime_module.os.read.side_effect = OSError("PRIVATE_SENTINEL")
    if outcome == "success":
        assert runtime_module._run_owned(["synthetic-node"], tmp_path, {"HOME": str(tmp_path)}, timeout=1) == len(b"PRIVATE_SENTINEL")
    else:
        with pytest.raises(ValueError, match="^" + expected[outcome] + "$"):
            runtime_module._run_owned(["synthetic-node"], tmp_path, {}, timeout=1)
    assert owned_process.popen.call_args.kwargs["start_new_session"] is True
    assert owned_process.popen.call_args.kwargs["cwd"] == tmp_path
    assert [call.args for call in owned_process.kill.call_args_list] == [
        (456789, runtime_module.signal.SIGTERM), (456789, runtime_module.signal.SIGKILL)]
    assert owned_process.process.stdout.close.call_count == 1
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("error", [OSError("PRIVATE_SENTINEL"), ValueError("PRIVATE_SENTINEL")])
def test_build_start_failure_never_signals_unowned_process(runtime_module, owned_process, tmp_path, error):
    owned_process.popen.side_effect = error
    with pytest.raises(ValueError, match="^build_start_failed$"):
        runtime_module._run_owned(["synthetic-node"], tmp_path, {}, timeout=1)
    owned_process.kill.assert_not_called()


def test_owned_process_cleanup_failure_is_not_suppressed(runtime_module, owned_process, tmp_path):
    owned_process.kill.side_effect = PermissionError("PRIVATE_SENTINEL")
    with pytest.raises(ValueError, match="^build_cleanup_failed$"):
        runtime_module._run_owned(["synthetic-node"], tmp_path, {}, timeout=1)
    owned_process.process.stdout.close.assert_called_once()


def test_next_build_uses_existing_node_native_preflight_then_cli(runtime_module, tmp_path, monkeypatch):
    run = Mock(return_value=8)
    monkeypatch.setattr(runtime_module, "_run_owned", run)
    monkeypatch.setattr(runtime_module, "_native_package", lambda: "@next/swc-linux-x64-gnu")
    monkeypatch.setattr(runtime_module.shutil, "which", lambda *args, **kwargs: "/existing/node")
    environment = runtime_module.sanitized_environment()
    assert runtime_module._build_frontend(tmp_path, environment) == 16
    preflight, build = run.call_args_list
    assert preflight.args[0] == ["/existing/node", "-e", "require(process.argv[1])", str(tmp_path / "node_modules/@next/swc-linux-x64-gnu")]
    assert build.args[0] == ["/existing/node", str(tmp_path / "node_modules/next/dist/bin/next"), "build"]
    assert build.args[2] is environment and build.kwargs["timeout"] == runtime_module.BUILD_TIMEOUT_SECONDS
    run.reset_mock(side_effect=True)
    run.side_effect = ValueError("build_failed")
    with pytest.raises(ValueError, match="^build_failed$"):
        runtime_module._build_frontend(tmp_path, environment)
    assert run.call_count == 1


def test_owned_listener_is_busy_even_with_address_reuse(runtime_module):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        with pytest.raises(ValueError, match="^port_unavailable$"):
            runtime_module.require_port_free(port)


def test_owned_recent_connection_close_does_not_block_server_reuse(runtime_module):
    # The only connection is to this test's ephemeral listener, never a service.
    with socket.socket() as listener, socket.socket() as client:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.settimeout(1)
        client.settimeout(1)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen(1)
        client.connect(("127.0.0.1", port))
        connection, _ = listener.accept()
        with connection:
            connection.settimeout(1)
            connection.shutdown(socket.SHUT_WR)
            assert client.recv(1) == b""
            client.shutdown(socket.SHUT_WR)
            assert connection.recv(1) == b""
    runtime_module.require_port_free(port)


def test_incomplete_tree_walk_fails_closed(runtime_module, tmp_path, monkeypatch):
    def unreadable(root, *, followlinks, onerror=None):
        if onerror:
            onerror(PermissionError("PRIVATE_SENTINEL"))
        return iter(())
    monkeypatch.setattr(runtime_module.os, "walk", unreadable)
    with pytest.raises(ValueError, match="^shared_tree_unreadable$"):
        runtime_module._tree_hash(tmp_path)


def test_temporary_cleanup_failure_is_fixed_and_not_suppressed(runtime_module, synthetic_repo, monkeypatch):
    original = runtime_module.tempfile.TemporaryDirectory
    def temporary(*args, **kwargs):
        result = original(*args, **kwargs)
        clean = result.cleanup
        def failed_cleanup():
            clean()
            raise OSError("PRIVATE_SENTINEL")
        result.cleanup = failed_cleanup
        return result
    monkeypatch.setattr(runtime_module.tempfile, "TemporaryDirectory", temporary)
    with pytest.raises(ValueError, match="^runtime_cleanup_failed$"):
        with runtime_module.frontend_runtime(synthetic_repo.root, backend_port=18000) as runtime:
            pass
    assert not runtime.evidence["cleanup_complete"]
    assert not runtime.frontend_root.exists()


def test_tree_hash_binds_added_files_and_internal_link_targets(runtime_module, tmp_path):
    (tmp_path / "a").write_text("a")
    (tmp_path / "b").write_text("b")
    link = tmp_path / "link"
    link.symlink_to("a")
    before = runtime_module._tree_hash(tmp_path)
    link.unlink()
    link.symlink_to("b")
    assert runtime_module._tree_hash(tmp_path) != before
    before = runtime_module._tree_hash(tmp_path)
    (tmp_path / "added").write_text("added")
    assert runtime_module._tree_hash(tmp_path) != before
