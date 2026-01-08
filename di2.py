import httpx
from libdi import AbstractDependency, dependency, inject, Dependency


def _get_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": "MyApp/1.0"})


client_depenency: Dependency[httpx.Client] = dependency(_get_client, cached=True)


def f(dep: AbstractDependency[httpx.Client] | None = None) -> None:
    client = (dep if dep is not None else client_depenency).get()
    response = client.get("https://example.com")
    print(response.status_code)


class Example:
    value = inject(dependency(lambda: 42, cached=True))
    another_value = inject(dependency(lambda: "hello", cached=False))
    itself = inject(dependency(lambda: Example(), cached=False))


ex = Example()
print(ex.value)  # Outputs: 42
print(ex.another_value)  # Outputs: hello
print(ex.itself.value)  # Outputs: 42
