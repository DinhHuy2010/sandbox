from __future__ import annotations

import gzip
import json
from typing import TYPE_CHECKING, Any, Generator
from attrs import define, field

from breader import BReader
import github_rest_api_models

if TYPE_CHECKING:
    from httpx import Client


@define(kw_only=True)
class Context:
    _state: dict[str, Any] = field(factory=dict[str, Any], init=False)

    def get_client(self) -> Client:
        from httpx import Client

        if "client" in self._state:
            return self._state["client"]  # type: ignore
        client = Client()
        self._state["client"] = client
        return client

def fetch_gharchive_records(ctx: Context, fn: str) -> Generator[github_rest_api_models.GitHubRestAPIEvent, None, None]:
    c = ctx.get_client()
    with c.stream("GET", f"https://data.gharchive.org/{fn}") as r:
        r.raise_for_status()
        br = BReader(r.iter_bytes())
        with gzip.GzipFile(fileobj=br, mode="rb") as gf:
            for line in gf:
                record = json.loads(line)
                obj = github_rest_api_models.GitHubRestAPIEvent.model_validate(record)
                yield obj

ctx = Context()
for event in fetch_gharchive_records(ctx, "2024-01-01-0.json.gz"):
    if isinstance(event.payload, github_rest_api_models.GitHubRestAPIPushEvent):
        print(f"Push #{event.payload.push_id} by {event.actor.login} to {event.repo.name}, sha: {event.payload.head}")
