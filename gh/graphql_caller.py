from __future__ import annotations

from typing import TYPE_CHECKING

from gql import Client as GQLClient
from gql import gql
from gql.transport.httpx import HTTPXTransport
from hishel import FilterPolicy, SyncSqliteStorage
from hishel.httpx import SyncCacheTransport
from httpx import HTTPTransport

if TYPE_CHECKING:
    from app import SettingsDependency


class MyPolicy(FilterPolicy):
    use_body_key = True


storage = SyncSqliteStorage(database_path="cache.db", default_ttl=3600)
transport = SyncCacheTransport(
    HTTPTransport(),
    storage=storage,
    policy=MyPolicy(),
)


def create_client(settings: SettingsDependency) -> GQLClient:
    client = HTTPXTransport(
        url="https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {settings.github_token}"},
        transport=transport,
    )
    gql_client = GQLClient(transport=client, fetch_schema_from_transport=False)
    return gql_client


def caller(settings: SettingsDependency, repo_owner: str, repo_name: str):
    gql_client = create_client(settings)
    query = gql("""
    query Query($owner: String!, $repo: String!) {
    viewer {
        login
        url
        avatarUrl
    }
    repository(owner: $owner, name: $repo) {
        name
        nameWithOwner
        description
        url
        owner {
        login
        avatarUrl
        url
        }
        stargazerCount
        stargazers(first: 50) {
        edges {
            node {
            id
            login
            followers {
                totalCount
            }
            url
            avatarUrl
            createdAt
            bio
            }
            starredAt
        }
        }
    }
    }""")
    out = gql_client.execute(
        query, variable_values={"owner": repo_owner, "repo": repo_name}
    )
    return out
