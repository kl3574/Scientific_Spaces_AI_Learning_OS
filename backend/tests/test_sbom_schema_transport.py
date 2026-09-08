"""Offline production-loader contracts, collected by the ordinary CI pytest job."""

import hashlib
import http.client
import importlib.util
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch
import urllib.error

import pytest


SECURITY_DIR = Path(__file__).resolve().parents[2] / "scripts" / "security"
SCHEMA = b'{"$schema":"http://json-schema.org/draft-07/schema#","type":"object"}'
PRIVATE_SENTINEL = "synthetic-sensitive-transport-detail"


@pytest.fixture
def security(monkeypatch):
    # Restore imports as well as sys.path; no global common/lockfiles collision.
    with patch.dict(sys.modules), monkeypatch.context() as imports:
        imports.syspath_prepend(str(SECURITY_DIR))
        spec = importlib.util.spec_from_file_location(
            "_sbom_transport_contract", SECURITY_DIR / "validate_sbom.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


@pytest.fixture
def policy():
    value = json.loads(
        (SECURITY_DIR.parents[1] / ".github/security/sbom-policy.json").read_text()
    )
    value["schema_sha256"] = hashlib.sha256(SCHEMA).hexdigest()
    return value


@pytest.fixture
def calls(security, monkeypatch):
    opener = Mock()
    sleeper = Mock()
    validator = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(security.urllib.request, "urlopen", opener)
    monkeypatch.setattr(security.time, "sleep", sleeper)
    monkeypatch.setattr(security, "subprocess", SimpleNamespace(
        run=validator, PIPE=subprocess.PIPE, SubprocessError=subprocess.SubprocessError
    ))
    return opener, sleeper, validator


@pytest.fixture
def sbom_dir(security):
    builder = runpy.run_path(str(SECURITY_DIR / "build_sbom.py"))
    with tempfile.TemporaryDirectory(prefix="p3-0052-sbom-test-") as name:
        directory = Path(name)
        builder["build_all"](directory)
        yield directory
    assert not directory.exists()


def http_error(code):
    return urllib.error.HTTPError(
        "https://example.invalid/" + PRIVATE_SENTINEL,
        code, PRIVATE_SENTINEL, {"X-Fixture": PRIVATE_SENTINEL}, None,
    )


def urls(opener):
    return [call.args[0].full_url for call in opener.call_args_list]


def test_primary_success_uses_exact_validator_and_cleans_schema(security, policy, calls):
    opener, sleeper, validator = calls
    opener.return_value = io.BytesIO(SCHEMA)
    schema_paths = []
    inputs = [Path("backend.cdx.json"), Path("frontend.cdx.json"), Path("combined.cdx.json")]

    def validate(command, **kwargs):
        assert command[:4] == [
            "uvx", "--from", policy["schema_validator"], "check-jsonschema"
        ]
        assert command[4] == "--schemafile"
        schema_path = Path(command[5])
        assert schema_path.read_bytes() == SCHEMA
        schema_paths.append(schema_path)
        assert command[6:] == [str(path) for path in inputs]
        assert kwargs["timeout"] == 300
        return subprocess.CompletedProcess(command, 0, "", "")

    validator.side_effect = validate
    security._schema_validate(inputs, policy)
    assert urls(opener) == [policy["schema_api_url"]]
    assert opener.call_args.kwargs == {"timeout": 30}
    assert opener.call_args.args[0].get_header("Accept") == "application/vnd.github.raw+json"
    sleeper.assert_not_called()
    validator.assert_called_once()
    assert schema_paths and not schema_paths[0].parent.exists()


@pytest.mark.parametrize("error", [
    http_error(code) for code in (401, 403, 404, 408, 429, 500, 503)
] + [urllib.error.URLError(PRIVATE_SENTINEL), TimeoutError(PRIVATE_SENTINEL),
     OSError(PRIVATE_SENTINEL)])
def test_api_failure_uses_digest_pinned_alternate(security, policy, calls, error):
    opener, sleeper, validator = calls
    opener.side_effect = [error, io.BytesIO(SCHEMA)]
    security._schema_validate([], policy)
    assert urls(opener) == [policy["schema_api_url"], policy["schema_url"]]
    assert opener.call_args.args[0].get_header("Accept") == "application/json"
    assert [call.kwargs for call in opener.call_args_list] == [{"timeout": 30}] * 2
    sleeper.assert_called_once_with(1)
    validator.assert_called_once()


@pytest.mark.parametrize("error", [
    http_error(code) for code in (408, 429, 500, 503)
] + [urllib.error.URLError(PRIVATE_SENTINEL), TimeoutError(PRIVATE_SENTINEL)])
def test_transient_alternate_failure_has_one_retry(security, policy, calls, error):
    opener, sleeper, validator = calls
    opener.side_effect = [http_error(503), error, io.BytesIO(SCHEMA)]
    security._schema_validate([], policy)
    assert urls(opener) == [policy["schema_api_url"], policy["schema_url"], policy["schema_url"]]
    assert [call.args for call in sleeper.call_args_list] == [(1,), (2,)]
    validator.assert_called_once()


@pytest.mark.parametrize("code", [400, 401, 403, 404, 410])
def test_permanent_alternate_failure_stops_early(security, policy, calls, code):
    opener, sleeper, validator = calls
    opener.side_effect = [http_error(503), http_error(code), io.BytesIO(SCHEMA)]
    with pytest.raises(security.SecurityToolError, match="CycloneDX schema unavailable"):
        security._schema_validate([], policy)
    assert opener.call_count == 2
    sleeper.assert_called_once_with(1)
    validator.assert_not_called()


def test_exhaustion_is_bounded_and_diagnostics_are_sanitized(security, policy, calls, capsys):
    opener, sleeper, validator = calls
    opener.side_effect = http_error(503)
    with pytest.raises(security.SecurityToolError) as error:
        security._schema_validate([], policy)
    output = str(error.value) + capsys.readouterr().err
    assert "HTTPError" in output and "503" in output
    assert "api" in output and "raw" in output
    assert PRIVATE_SENTINEL not in output
    assert "https://" not in output and "X-Fixture" not in output
    assert opener.call_count == 3
    assert [call.args for call in sleeper.call_args_list] == [(1,), (2,)]
    validator.assert_not_called()


@pytest.mark.parametrize("error", [
    OSError(PRIVATE_SENTINEL), http.client.IncompleteRead(PRIVATE_SENTINEL.encode(), 100)
])
def test_interrupted_response_is_closed_before_fallback(security, policy, calls, error, capsys):
    class InterruptedResponse(io.BytesIO):
        def read(self, *args):
            raise error

    opener, _, validator = calls
    interrupted = InterruptedResponse()
    opener.side_effect = [interrupted, io.BytesIO(SCHEMA)]
    security._schema_validate([], policy)
    assert interrupted.closed
    assert urls(opener) == [policy["schema_api_url"], policy["schema_url"]]
    validator.assert_called_once()
    assert PRIVATE_SENTINEL not in capsys.readouterr().err


def test_invalid_http_status_is_not_logged(security, policy, calls, capsys):
    calls[0].side_effect = http_error(PRIVATE_SENTINEL)
    with pytest.raises(security.SecurityToolError) as error:
        security._schema_validate([], policy)
    output = str(error.value) + capsys.readouterr().err
    assert "status=unknown" in output
    assert PRIVATE_SENTINEL not in output
    assert calls[0].call_count == 2


def test_error_response_bodies_are_closed_without_reading(security, policy, calls, capsys):
    class UnreadBody(io.BytesIO):
        def read(self, *args):
            raise AssertionError("Transport diagnostics must not read error bodies")

    bodies = [UnreadBody(PRIVATE_SENTINEL.encode()) for _ in range(3)]
    calls[0].side_effect = [
        urllib.error.HTTPError("https://example.invalid", 503, PRIVATE_SENTINEL, {}, body)
        for body in bodies
    ]
    with pytest.raises(security.SecurityToolError, match="schema unavailable"):
        security._schema_validate([], policy)
    assert all(body.closed for body in bodies)
    assert PRIVATE_SENTINEL not in capsys.readouterr().err
    calls[2].assert_not_called()


def test_response_close_failure_cannot_leave_success_bytes(security, policy, calls):
    class CloseFailure(io.BytesIO):
        def __exit__(self, *args):
            super().__exit__(*args)
            raise OSError(PRIVATE_SENTINEL)

    response = CloseFailure(SCHEMA)
    calls[0].side_effect = [response, http_error(503), http_error(503)]
    with pytest.raises(security.SecurityToolError, match="schema unavailable"):
        security._schema_validate([], policy)
    assert response.closed
    assert calls[0].call_count == 3
    calls[2].assert_not_called()


def test_bad_digest_cannot_be_hidden_by_context_close_failure(security, policy, calls):
    class CloseFailure(io.BytesIO):
        def __exit__(self, *args):
            super().__exit__(*args)
            raise OSError(PRIVATE_SENTINEL)

    calls[0].side_effect = [CloseFailure(b"wrong digest"), io.BytesIO(SCHEMA)]
    with pytest.raises(security.SecurityToolError, match="schema digest mismatch"):
        security._schema_validate([], policy)
    assert calls[0].call_count == 1
    calls[1].assert_not_called()
    calls[2].assert_not_called()


def test_error_body_cleanup_failure_is_terminal_and_sanitized(security, calls, sbom_dir, monkeypatch, capsys):
    class CloseFailure(io.BytesIO):
        def close(self):
            super().close()
            raise OSError(PRIVATE_SENTINEL)

    body = CloseFailure(PRIVATE_SENTINEL.encode())
    calls[0].side_effect = urllib.error.HTTPError(
        "https://example.invalid/" + PRIVATE_SENTINEL, 503, PRIVATE_SENTINEL, {}, body
    )
    monkeypatch.setattr(sys, "argv", ["validate_sbom.py", str(sbom_dir)])
    assert security.main() == 2
    output = capsys.readouterr()
    assert "schema response cleanup failed: attempt=1 endpoint=api" in output.err
    assert PRIVATE_SENTINEL not in output.err
    assert body.closed
    assert calls[0].call_count == 1
    calls[1].assert_not_called()
    calls[2].assert_not_called()


@pytest.mark.parametrize("position", [0, 1, 2])
def test_bad_digest_stops_without_trying_available_later_source(security, policy, calls, position):
    opener, _, validator = calls
    opener.side_effect = [http_error(503)] * position + [
        io.BytesIO(b"invalid schema"), io.BytesIO(SCHEMA)
    ]
    with pytest.raises(security.SecurityToolError, match="schema digest mismatch"):
        security._schema_validate([], policy)
    assert opener.call_count == position + 1
    validator.assert_not_called()


@pytest.mark.parametrize("failure", ["rejected", "timeout", "local-write"])
def test_validator_and_file_failures_never_trigger_fallback(security, policy, calls, monkeypatch, failure):
    opener, sleeper, validator = calls
    opener.return_value = io.BytesIO(SCHEMA)
    schema_paths = []

    def fail(command, **kwargs):
        schema_paths.append(Path(command[5]))
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 300)
        return subprocess.CompletedProcess(command, 1, "", "fixture schema rejected")

    validator.side_effect = fail
    if failure == "local-write":
        monkeypatch.setattr(security.Path, "write_bytes", Mock(side_effect=OSError("fixture write")))
    with pytest.raises((security.SecurityToolError, subprocess.TimeoutExpired, OSError)):
        security._schema_validate([], policy)
    assert opener.call_count == 1
    sleeper.assert_not_called()
    assert all(not path.parent.exists() for path in schema_paths)
    if failure == "local-write":
        validator.assert_not_called()


def test_unpinned_validator_stops_before_network(security, policy, calls):
    policy["schema_validator"] = "check-jsonschema"
    with pytest.raises(security.SecurityToolError, match="exactly pinned"):
        security._schema_validate([], policy)
    calls[0].assert_not_called()


@pytest.mark.parametrize("failure", ["transport", "digest", "validator", "timeout"])
def test_full_validation_and_cli_propagate_failure(security, calls, sbom_dir, monkeypatch, failure, capsys):
    opener, _, validator = calls
    if failure == "transport":
        opener.side_effect = http_error(503)
    else:
        opener.side_effect = lambda *args, **kwargs: io.BytesIO(SCHEMA)
        if failure != "digest":
            real_load = security.load_json

            def load_fixture_policy(path):
                value = real_load(path)
                if path.name == "sbom-policy.json":
                    value["schema_sha256"] = hashlib.sha256(SCHEMA).hexdigest()
                return value

            monkeypatch.setattr(security, "load_json", load_fixture_policy)
            if failure == "timeout":
                validator.side_effect = subprocess.TimeoutExpired(["fixture-validator"], 300)
            else:
                validator.return_value = subprocess.CompletedProcess([], 1, "", "fixture rejected")
    with pytest.raises((security.SecurityToolError, subprocess.TimeoutExpired)):
        security.validate_all(sbom_dir)
    monkeypatch.setattr(sys, "argv", ["validate_sbom.py", str(sbom_dir)])
    assert security.main() == 2
    output = capsys.readouterr()
    assert "sbom_validation=BLOCKED" in output.err
    assert "sbom_validation=PASS" not in output.out
    assert PRIVATE_SENTINEL not in output.err


def test_structural_only_is_explicit_not_full_schema_evidence(security, calls, sbom_dir):
    result = security.validate_all(sbom_dir, structural_only=True)
    assert result["schema_validation"] == "NOT_RUN"
    calls[0].assert_not_called()
    calls[2].assert_not_called()
