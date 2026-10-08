"""The running app must match docs/openapi.yaml: same paths, same methods,
and the success status code each route returns is the one documented.

We compare against app.openapi(), the spec FastAPI generates from the real
routes, so this works however the routers are wired together."""

from pathlib import Path

import yaml

from app.main import app

SPEC = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "docs" / "openapi.yaml").read_text()
)
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def contract_operations() -> dict:
    ops = {}
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if method in HTTP_METHODS:
                success = [int(c) for c in op["responses"] if str(c).startswith("2")]
                ops[(method.upper(), path)] = success
    return ops


def app_operations() -> dict:
    ops = {}
    for path, item in app.openapi()["paths"].items():
        for method, op in item.items():
            success = [int(c) for c in op["responses"] if str(c).startswith("2")]
            ops[(method.upper(), path)] = success[0]
    return ops


def test_routes_and_methods_match_contract():
    assert set(app_operations()) == set(contract_operations())


def test_success_status_codes_match_contract():
    contract = contract_operations()
    for key, status in app_operations().items():
        assert status in contract[key], f"{key}: app returns {status}, contract says {contract[key]}"
