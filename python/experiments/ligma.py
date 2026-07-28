from inspect import Parameter, getmodule, signature
from typing import Annotated, Any, Callable

from pydantic import BaseModel, Field, create_model

type Factory = Callable[..., Any]


def get_info(f: Factory) -> tuple[str, str, str | None]:
    name = f.__name__
    module = getmodule(f)
    if module is not None:
        mname = module.__name__
    else:
        mname = f.__module__
    doc = f.__doc__
    return name, mname, doc


def create_model_from_function(f: Factory) -> type[BaseModel]:
    sig = signature(f)
    model_name, module_name, doc = get_info(f)
    fields: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if param.annotation is Parameter.empty:
            anno = Any
        else:
            anno = param.annotation
        default = param.default if param.default is not Parameter.empty else ...
        fields[name] = (anno, default)
    return create_model(model_name, __module__=module_name, __doc__=doc, **fields)


def model(f: Factory) -> type[BaseModel]:
    model = create_model_from_function(f)
    return model


@model
def Person(name: str, age: Annotated[int, Field(gt=0)]):
    """A person."""


print(Person(name="Alice", age=30).model_dump_json())
help(Person)
