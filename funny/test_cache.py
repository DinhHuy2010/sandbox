from eval2 import use
from eval2.builtins import Expression, cache_expression, cache_evaluatable_function
from eval2.core import evaluate


def some_expr():
    def expr(ctx):
        print("Evaluating expression")
        return 42

    return Expression(expr)


x = cache_expression(some_expr())
print(evaluate(use(x + x)))
