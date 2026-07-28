from eval2 import (
    Value,
    current_value,
    evaluate,
    use,
    input as input_value,
)
from eval2.builtins import call, conditional_statement, sequence
from eval2.core import Context, evaluate_value, execute_function

prog = sequence(
    use(input_value("Enter a number: ")),
    use(call(int, current_value())),
    conditional_statement(
        current_value() % call(int, input_value("Enter remainder: ")) == 0,
        use(Value("Divisible")),
        use(Value("Not divisible")),
    ),
)
ctx = Context(Value(None))
ctx = execute_function(prog, ctx)
print(ctx.current_value)
print(ctx.variables)
# print(evaluate_value(ctx.current_value, ctx))


# output = evaluate(prog)
# print(output)
