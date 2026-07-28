# pyright: standard

from datetime import date, timedelta
from typing import Iterable

import faker
from openapi_pydantic import (
    Info,
    OpenAPI,
    Operation,
    Parameter,
    ParameterLocation,
    PathItem,
    Paths,
    Server,
)

fake = faker.Faker()


def daterange(start: date, stop: date, delta: timedelta) -> Iterable[date]:
    d = start
    while d <= stop:
        yield d
        d += delta


def generate_operation() -> Operation:
    return Operation(
        operationId=fake.uuid4(),
        description=fake.text(),
        parameters=[
            Parameter(
                name=fake.word(),
                description=fake.text(),
                required=fake.boolean(),
                **{"in": fake.random_element(ParameterLocation)},  # type: ignore
            )
            for _ in range(fake.random_int(min=0, max=5))
        ],
    )


def build_path_item() -> PathItem:
    methods = fake.random_elements(
        ["get", "post", "put", "delete", "patch", "options", "head"],
        length=3,
        unique=True,
    )
    return PathItem(
        summary=fake.text(),
        description=fake.paragraph(),
        **{method: generate_operation() for method in methods},  # type: ignore
    )


def fake_api_path() -> str:
    return f"/{'/'.join(fake.words(nb=fake.random_int(min=1, max=5), unique=True, ext_word_list=None))}"


def build_path_ops() -> Paths:
    paths: Paths = {}
    for _ in range(10):
        path = fake_api_path()
        paths[path] = build_path_item()
    return dict(sorted(dict(paths).items(), key=lambda item: item[0]))


def build_server_paths() -> list[Server]:
    # local
    servers: list[Server] = []
    for v in range(1, 5 + 1):
        path = f"/api/v{v}"
        servers.append(Server(url=path, description=fake.text()))
    # next
    d = fake.past_date("-1y")
    s = fake.future_date()
    for d in daterange(d, s, timedelta(days=7)):
        path = f"/next/{d.isoformat()}/api/"
        servers.append(Server(url=path, description=fake.text()))
    # mirrors
    for _ in range(5):
        url = f"https://{fake.hostname()}{fake_api_path()}/api/"
        servers.append(Server(url=url, description=fake.text()))
    return servers


def build_gibberish_openapi() -> OpenAPI:
    api = OpenAPI(
        info=Info(
            title=fake.name(),
            version="0.1.0",
            description="\n\n".join(fake.paragraphs(nb=20)),
        ),
        paths=build_path_ops(),
        servers=build_server_paths(),
    )
    return api
