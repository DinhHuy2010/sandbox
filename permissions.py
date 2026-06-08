from datetime import datetime
import secrets

import jwt
from dataclasses import dataclass
from typing import Callable, Concatenate


@dataclass
class Permission:
    permission: str


@dataclass
class APIKey:
    created_at: datetime
    permissions: list[Permission]


SECRET = secrets.token_bytes(32)


def encode_api_key(api_key: APIKey) -> tuple[str]:
    payload = {
        "created_at": api_key.created_at.isoformat(),
        "permissions": [p.permission for p in api_key.permissions],
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def decode_api_key(token: str) -> APIKey:
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    created_at = datetime.fromisoformat(payload["created_at"])
    permissions = [Permission(p) for p in payload["permissions"]]
    return APIKey(created_at, permissions)


def has_permission(api_key: APIKey, permission: Permission) -> bool:
    permissions = {p.permission for p in api_key.permissions}
    return permission.permission in permissions


def require_permission(*permissions: str | Permission):
    permissions: list[str] = [
        p.permission if isinstance(p, Permission) else p for p in permissions
    ]

    def decorator[**P, T](func: Callable[P, T]) -> Callable[Concatenate[APIKey, P], T]:
        def wrapper(key: str | APIKey, *args: P.args, **kwargs: P.kwargs) -> T:
            if isinstance(key, str):
                key = decode_api_key(key)
            if not all(has_permission(key, Permission(p)) for p in permissions):
                raise PermissionError("You do not have the required permissions.")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def create_api_key(permissions: list[Permission]) -> str:
    return encode_api_key(APIKey(datetime.now(), permissions))


ADD = Permission("add")


@require_permission(ADD)
def add_numbers(a: int, b: int) -> int:
    return a + b


p = create_api_key([ADD])
print("API Key:", p)
print(p)
x = add_numbers(p, 2, 3)
print(x)
