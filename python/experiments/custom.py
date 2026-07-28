# pyright: standard

from inspect import (
    Parameter,
    Signature,
    currentframe,
    getmodule,
    getouterframes,
    signature,
)
from typing import TYPE_CHECKING, Any, Callable, overload


class FieldInfo:
    if TYPE_CHECKING:

        def __getattr__(self, name: str) -> Any: ...


@overload
def Field(*, required: bool = True, **info: Any) -> Any: ...
@overload
def Field(**info: Any) -> Any: ...
def Field(*, required=True, **info):
    info = {"required": required, **info}

    class _Field(FieldInfo):
        def __getattr__(self, name):
            try:
                return info[name]
            except KeyError:
                raise AttributeError(
                    f"{self.__class__.__name__!r} object has no attribute {name!r}"
                )

        def __repr__(self):
            return f"Field({', '.join(f'{k}={v!r}' for k, v in info.items())})"

    return _Field()


def get_fields(sig: Signature) -> dict[str, FieldInfo]:
    fields = {}
    for name, param in sig.parameters.items():
        if param.default is not Parameter.empty and isinstance(
            param.default, FieldInfo
        ):
            fields[name] = param.default
        else:
            fields[name] = Field()
    return fields


def generate_signature(fields: dict[str, FieldInfo]) -> Signature:
    parameters = [
        Parameter("cls", kind=Parameter.POSITIONAL_OR_KEYWORD, default=Parameter.empty)
    ]
    for name, field in fields.items():
        try:
            default = field.default if field.required is False else Parameter.empty
        except AttributeError:
            default = Parameter.empty
        parameters.append(
            Parameter(name, kind=Parameter.POSITIONAL_OR_KEYWORD, default=default)
        )
    return Signature(parameters)


def custom(f: Callable[..., Any]) -> type[Any]:
    sig = signature(f)
    name = getattr(f, "__name__", "object")
    module = getmodule(f)
    if module is None:
        mname = f.__module__
    else:
        mname = module.__name__
    doc = getattr(f, "__doc__", None)
    fields = get_fields(sig)

    def modclass(cls):
        transformer = f(**fields)
        if transformer is None:
            return cls
        return transformer(cls)

    class _wrapper:
        if TYPE_CHECKING:

            def __getattr__(self, name: str) -> Any: ...

        def __new__(cls, *args: Any, **kwargs: Any) -> Any:
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            self = super().__new__(cls)
            self.__dict__.update(bound_args.arguments)
            return self

        def __repr__(self):
            return f"{name}({', '.join(f'{k}={v!r}' for k, v in vars(self).items())})"

    _wrapper.__name__ = name
    _wrapper.__module__ = mname
    _wrapper.__new__.__signature__ = generate_signature(fields)  # type: ignore
    _wrapper.__doc__ = doc
    _wrapper.__fdef__ = f  # type: ignore

    return modclass(_wrapper)


def meth[_F: Callable[..., Any]](f: _F) -> _F:
    setattr(f, "__ismethodforcustom__", True)
    return f


def autocomplete[T](v: T, /, **more: Any) -> T:
    locals = getouterframes(currentframe())[1].frame.f_locals
    for name, value in locals.items():
        if getattr(value, "__ismethodforcustom__", False):
            setattr(v, name, value)
    for name, value in more.items():
        setattr(v, name, value)
    return v


@custom
def Person(name: str = Field(), age: int | None = Field(required=False, default=None)):
    """A simple data class for a person."""

    def transformer(cls):
        @meth
        def say(self):
            return f"My name is {self.name} and I am {self.age} years old."

        return autocomplete(cls, some_value=0)

    return transformer


# Person.__doc__ = "A simple data class for a person."
# Person.say = lambda self: f"My name is {self.name} and I am {self.age} years old."
# Person.say.__doc__ = "Returns a string introducing the person."

person = Person(name="Alice", age=30)
print(person)  # Output: Person(name='Alice', age=30)
print(person.say())  # Output: My name is Alice and I am 30 years old
help(Person)
