import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from myjsonvalidator import SchemaRegistry, ValidationError, validate_json

SCHEMA_VERSION_SUITE = "draft2020-12"
BASE_TESTSUITE_DIR = Path("jsonschema-official-testsuite").resolve()


def load_official_remote(uri):
    parsed = urlparse(uri)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "localhost:1234":
        return None

    path = BASE_TESTSUITE_DIR / "remotes" / parsed.path.lstrip("/")
    if not path.is_file():
        return None

    return json.loads(path.read_text())


def load_test_cases_for(version):
    directory = BASE_TESTSUITE_DIR / "tests" / version
    for test_file in directory.glob("*.json"):
        p = json.loads(test_file.read_text())
        for suite in p:
            schema = suite["schema"]
            for test in suite["tests"]:
                yield pytest.param(
                    suite["description"],
                    test["description"],
                    schema,
                    test["data"],
                    test["valid"],
                    id=f"{suite['description']} - {test['description']}",
                )


cases = list(load_test_cases_for(SCHEMA_VERSION_SUITE))


@pytest.mark.parametrize(
    "suite_description, test_description, schema, data, expected_validity", cases
)
def test_json_validation(
    suite_description, test_description, schema, data, expected_validity
):
    try:
        schema_registry = SchemaRegistry(loaders=[load_official_remote])
        validate_json(data, schema, registry=schema_registry)
        is_valid = True
    except ValidationError:
        is_valid = False
    assert is_valid == expected_validity, (
        f"Test failed for suite '{suite_description}', test '{test_description}'. "
        f"Expected validity: {expected_validity}, but got: {is_valid}."
    )
