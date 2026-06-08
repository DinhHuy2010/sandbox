from dataclasses import dataclass
from functools import cache
import subprocess
from typing import Any, Iterator, Mapping

from attrs import define, field
import attrs
import httpx
from github_models import SimpleUser


@cache
def get_github_token() -> str:
    """Get the GitHub token from the environment variable."""
    import os

    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token
    # try use gh auth token
    try:
        out = subprocess.run(["gh", "auth", "token"], check=True, capture_output=True)
        return out.stdout.decode().strip()
    except subprocess.CalledProcessError:
        raise ValueError(
            "GITHUB_TOKEN environment variable is not set and gh auth token failed."
        )


# -- Source - https://stackoverflow.com/a/47503662
# -- Posted by Bertrand Martel, modified by community. See post 'Timeline' for change history
# -- Retrieved 2026-06-01, License - CC BY-SA 3.0
GH_GRAPHQL_TOTAL_USERS = """
{
  user: search(type: USER, query: "type:user") {
    userCount
  }
}
"""


@define
class Context:
    """Context for the application."""

    token: str = field(
        default_factory=get_github_token,
        repr=False,
        on_setattr=attrs.setters.frozen,
        hash=True,
    )
    _client: httpx.Client | None = field(default=None, init=False, repr=False)

    @property
    def client(self) -> httpx.Client:
        """Get the HTTP client with the authorization header."""
        if self._client is None:
            self._client = httpx.Client(
                headers={"Authorization": f"Bearer {self.token}"}
            )
        return self._client

    def call_github_api(
        self, endpoint: str, method: str = "GET", **kwargs
    ) -> dict[str, Any]:
        """Call the GitHub API."""
        url = f"https://api.github.com{endpoint}"
        response = self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def call_graphql(self, query: str, variables: dict = None):
        """Call the GitHub GraphQL API."""
        url = "/graphql"
        response = self.call_github_api(
            url, "POST", json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        return response.json()


@cache
def _get_number_of_users(context: Context) -> int:
    result = context.call_graphql(GH_GRAPHQL_TOTAL_USERS)
    return result["data"]["user"]["userCount"]


@define
class UserResources(Mapping[str, SimpleUser]):
    """Resources related to GitHub users."""

    context: Context

    def _iterate_logins(self):
        """Iterate over user logins."""
        url = "https://api.github.com/users"
        params = {"per_page": 100, "since": 0}
        while True:
            response = self.context.client.get(url, params=params)
            response.raise_for_status()
            users = response.json()
            if not users:
                break
            for user in users:
                yield user["login"]
            params["since"] = users[-1]["id"]

    def __getitem__(self, key: str) -> SimpleUser:
        """Get a user by login."""
        if key == "":
            # get the authenticated user
            o = self.context.call_github_api("/user")
        else:
            o = self.context.call_github_api(f"/users/{key}")
        return SimpleUser.model_validate(o)

    def __contains__(self, key: object) -> bool:
        if key == "":
            # authenticated user always exists
            return True
        return super().__contains__(key)

    def __iter__(self) -> Iterator[str]:
        """Iterate over the user logins."""
        # this is not a real implementation, just for demonstration
        # return iter(["octocat", "defunkt"])
        return iter(self._iterate_logins())

    def __len__(self):
        """Get the number of users."""
        return _get_number_of_users(self.context)


@define
class RepositoryResources:
    """Resources related to GitHub repositories."""

    context: Context

    def __getitem__(self, key):
        """Get a repository by name."""
        # this is just a placeholder, implement as needed
        raise NotImplementedError("RepositoryResources is not implemented yet.")


@dataclass
class GitHub:
    context: Context

    @property
    def users(self) -> UserResources:
        """Get the user resources."""
        return UserResources(self.context)


ctx = Context()
github = GitHub(ctx)

if __name__ == "__main__":
    octocat = github.users["octocat"]
    app = octocat.login
