import faker

fa = faker.Faker()


def generate_function(args: int, decorators: list[str] | None = None):
    a = ["".join(fa.random_letters()) for _ in range(args)]
    template = "def {func_name}({args}):\n    pass"
    template = template.format(
        func_name="".join(fa.random_letters()), args=", ".join(a)
    )
    if decorators:
        template = "\n".join([f"@{d}" for d in decorators]) + "\n" + template

    return template


def generate_call_syntax(args: int):
    a = ["".join(fa.random_letters()) for _ in range(args)]
    return f"{''.join(fa.random_letters())}({', '.join(a)})"


def generate_variable_syntax(_: int):
    return "".join(fa.random_letters())


def generate_decorator_syntax(n: int, nargs: int = 3):
    d = []
    choices = {
        1: generate_variable_syntax,
        2: generate_call_syntax,
        3: generate_lambda,
    }
    for _ in range(n):
        choice = fa.random_int(min=1, max=len(choices))
        d.append(choices[choice](fa.random_int(min=1, max=5)))

    return d


def generate_lambda(args: int):
    a = ["".join(fa.random_letters()) for _ in range(args)]
    return f"(lambda {', '.join(a)}: None)"


print(generate_function(30, decorators=generate_decorator_syntax(1000, 3)))
