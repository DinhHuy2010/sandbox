import json
from typing import Iterable

from upath import UPath

from eval2.io.path import PathExpression
from eval2.core import Value, evaluate, Context


def step1(ctx: Context):
    return ctx, PathExpression(Value(UPath("s3://openalex", anon=True)))


def step2(ctx: Context):
    from upath import UPath

    p = ctx.current_value.evaluate(ctx)
    assert isinstance(p, UPath)
    return ctx, PathExpression(Value(p / "data" / "jsonl" / "manifest.json"))


def step3(ctx: Context):
    p: UPath = ctx.current_value.evaluate(ctx)
    print(p.exists())
    with p.open("r") as f:
        return ctx, Value(json.load(f))

def step4(ctx: Context):
    data = ctx.current_value.evaluate(ctx)
    print(data)
    return ctx, Value(None)


evaluate(step1, step2, step3, step4)
