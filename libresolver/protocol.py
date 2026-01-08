import importlib.util
import sys
import os
from typing import Any

# {scheme: {endpoint_metadata}}
known: dict[str, Any] = {}


def get_protocol_metadata(obj: Any) -> Any:
    # {
    # "scheme": "python",
    # "endpoints": {
    #     <endpoint>: <function(path_args: tuple[str, ...], query_params: URLSearchParams, fragment: str) -> Any>
    # }
    return obj.__protocol_metadata__()


def load_protocol_from_module(module: Any) -> None:
    metadata = get_protocol_metadata(module)
    scheme = metadata["scheme"]
    if scheme in known:
        raise ValueError(f"Protocol '{scheme}' is already registered.")
    known[scheme] = metadata["endpoints"]


def load_protocol_from_path(module_path: str) -> None:
    module = __import__(module_path, fromlist=["__protocol_metadata__"])
    load_protocol_from_module(module)


def load_protocol_from_filepath(filepath: str) -> None:
    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from path: {filepath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    load_protocol_from_module(module)


def get_protocol_endpoint(scheme: str, endpoint: str) -> Any:
    if scheme not in known:
        raise ValueError(f"Protocol '{scheme}' is not registered.")
    endpoints = known[scheme]
    if endpoint not in endpoints:
        raise ValueError(
            f"Endpoint '{endpoint}' is not registered for protocol '{scheme}'."
        )
    return endpoints[endpoint]


def protocol_resolve(
    scheme: str,
    endpoint: str,
    path_args: tuple[str, ...],
    query_params: Any,
    fragment: str,
) -> Any:
    endpoint_func = get_protocol_endpoint(scheme, endpoint)
    return endpoint_func(path_args, query_params, fragment)


def is_protocol_registered(scheme: str) -> bool:
    return scheme in known
