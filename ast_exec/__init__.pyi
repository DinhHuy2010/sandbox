import ast
from typing import Any

def pyast_exec(
    module: ast.Module, ns: dict[str, Any] | None = None
) -> dict[str, Any]: ...
def raise_exception(exc: BaseException, cause: BaseException | None = None) -> None: ...
