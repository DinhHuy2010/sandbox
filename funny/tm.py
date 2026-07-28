# pyright: standard

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
import sys
from typing import IO, Any, cast

from pydantic import JsonValue


class Context:
    def __init__(self):
        self.variables = {}

    def set_variable(self, name: str, value: Any):
        self.variables[name] = value

    def get_variable(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        raise NameError(f"Variable '{name}' is not defined.")


@dataclass
class BaseResult:
    context: Context

    @property
    def is_ok(self):
        raise NotImplementedError("Subclasses must implement the is_ok method.")

    @property
    def is_error(self):
        raise NotImplementedError("Subclasses must implement the is_error method.")

    def error(self) -> None:
        raise NotImplementedError("Subclasses must implement the error method.")


class BaseResultOK(BaseResult):
    @property
    def is_ok(self):
        return True

    @property
    def is_error(self):
        return False

    def error(self) -> None:
        pass


@dataclass
class BaseResultError(BaseResult):
    error_code: str
    error_message: str
    context_error: BaseResultError | None = None

    @property
    def is_ok(self):
        return False

    @property
    def is_error(self):
        return True

    def error(self):
        raise Exception(f"Error {self.error_code}: {self.error_message}")


@dataclass
class ExpressionResultOK[EvaluatedPythonValue](BaseResultOK):
    value: EvaluatedPythonValue


@dataclass
class ExpressionResultError(BaseResultError):
    pass


class ExpressionForm[EvaluatedPythonValue](ABC):
    @abstractmethod
    def evaluate(
        self, context: Context
    ) -> ExpressionResultOK[EvaluatedPythonValue] | ExpressionResultError: ...


class VariableReference(ExpressionForm[Any]):
    def __init__(self, name: str):
        self.name = name

    def evaluate(
        self, context: Context
    ) -> ExpressionResultOK[Any] | ExpressionResultError:
        try:
            value = context.get_variable(self.name)
            return ExpressionResultOK(context=context, value=value)
        except NameError as e:
            return ExpressionResultError(
                context=context, error_code="VariableNotFound", error_message=str(e)
            )


class Value[ValueType: (int, str, float, bool)](ExpressionForm[ValueType]):
    def __init__(self, value: ValueType):
        self.value = value

    def evaluate(self, context: Context) -> ExpressionResultOK[ValueType]:
        return ExpressionResultOK(context=context, value=self.value)


class DefineVariable(ExpressionForm[Any]):
    def __init__(self, variable: str, value: ExpressionForm[Any]):
        self.variable = variable
        self.value = value

    def evaluate(
        self, context: Context
    ) -> ExpressionResultOK[Any] | ExpressionResultError:
        value_result = self.value.evaluate(context)
        if value_result.is_error:
            return ExpressionResultError(
                context=context,
                error_code="ValueEvaluationError",
                error_message=f"Error evaluating value for variable '{self.variable}': {value_result.error_code} - {value_result.error_message}",  # type: ignore
                context_error=value_result
                if isinstance(value_result, BaseResultError)
                else None,
            )
        context.set_variable(self.variable, value_result.value)  # type: ignore
        return ExpressionResultOK(context=context, value=value_result.value)  # type: ignore


class BinaryOperation(ExpressionForm[Any]):
    def __init__(
        self,
        left: ExpressionForm[Any],
        operator: str,
        right: ExpressionForm[Any],
    ):
        self.left = left
        self.operator = operator
        self.right = right

    def evaluate(
        self, context: Context
    ) -> ExpressionResultOK[Any] | ExpressionResultError:
        left_result = self.left.evaluate(context)
        if left_result.is_error:
            return ExpressionResultError(
                context=context,
                error_code="LeftOperandEvaluationError",
                error_message=f"Error evaluating left operand: {left_result.error_code} - {left_result.error_message}",  # type: ignore
                context_error=left_result
                if isinstance(left_result, BaseResultError)
                else None,
            )

        right_result = self.right.evaluate(context)
        if right_result.is_error:
            return ExpressionResultError(
                context=context,
                error_code="RightOperandEvaluationError",
                error_message=f"Error evaluating right operand: {right_result.error_code} - {right_result.error_message}",  # type: ignore
                context_error=right_result
                if isinstance(right_result, BaseResultError)
                else None,
            )

        try:
            if self.operator == "+":
                result_value = left_result.value + right_result.value  # type: ignore
            elif self.operator == "-":
                result_value = left_result.value - right_result.value  # type: ignore
            elif self.operator == "*":
                result_value = left_result.value * right_result.value  # type: ignore
            elif self.operator == "/":
                result_value = left_result.value / right_result.value  # type: ignore
            else:
                return ExpressionResultError(
                    context=context,
                    error_code="UnsupportedOperator",
                    error_message=f"Unsupported operator '{self.operator}'",
                )
            return ExpressionResultOK(context=context, value=result_value)
        except Exception as e:
            return ExpressionResultError(
                context=context,
                error_code="OperationEvaluationError",
                error_message=f"Error evaluating operation '{self.operator}': {str(e)}",
            )


class Program(ExpressionForm[Any]):
    def __init__(self, expressions: list[ExpressionForm[Any]] | None = None):
        self.expressions = expressions or []

    def add_expression(self, expression: ExpressionForm[Any]):
        self.expressions.append(expression)

    def evaluate(
        self, context: Context
    ) -> ExpressionResultOK[Any] | ExpressionResultError:
        last_value: Any = None
        for expression in self.expressions:
            result = expression.evaluate(context)
            if result.is_error:
                return ExpressionResultError(
                    context=context,
                    error_code="ProgramExpressionEvaluationError",
                    error_message=f"Error evaluating expression: {result.error_code} - {result.error_message}",  # type: ignore
                    context_error=result
                    if isinstance(result, BaseResultError)
                    else None,
                )
            last_value = result.value  # type: ignore

        return ExpressionResultOK(context=context, value=last_value)


class PrintExpression(ExpressionForm[Any]):
    def __init__(self, expression: ExpressionForm[Any]):
        self.expression = expression

    def evaluate(
        self, context: Context
    ) -> ExpressionResultOK[Any] | ExpressionResultError:
        result = self.expression.evaluate(context)
        if result.is_error:
            return ExpressionResultError(
                context=context,
                error_code="PrintExpressionEvaluationError",
                error_message=f"Error evaluating expression for print: {result.error_code} - {result.error_message}",  # type: ignore
                context_error=result if isinstance(result, BaseResultError) else None,
            )
        print(result.value)  # type: ignore
        return ExpressionResultOK(context=context, value=result.value)  # type: ignore


def export_expression(expression: ExpressionForm[Any]) -> JsonValue:
    if isinstance(expression, VariableReference):
        return {"type": "reference", "name": expression.name}

    if isinstance(expression, Value):
        return {"type": "value", "value": expression.value}

    if isinstance(expression, DefineVariable):
        return {
            "type": "define",
            "variable": expression.variable,
            "value": export_expression(expression.value),
        }

    if isinstance(expression, BinaryOperation):
        return {
            "type": "binary",
            "left": export_expression(expression.left),
            "operator": expression.operator,
            "right": export_expression(expression.right),
        }

    if isinstance(expression, Program):
        return {
            "type": "program",
            "expressions": [
                export_expression(child) for child in expression.expressions
            ],
        }

    if isinstance(expression, PrintExpression):
        return {
            "type": "print",
            "expression": export_expression(expression.expression),
        }

    raise TypeError(f"Cannot export {type(expression).__name__}.")


def import_expression(data: JsonValue) -> ExpressionForm[Any]:
    payload = _expect_object(data, "expression")
    expression_type = payload.get("type")

    if expression_type == "reference":
        return VariableReference(_expect_str(payload.get("name"), "reference name"))

    if expression_type == "value":
        value = payload.get("value")
        if isinstance(value, (int, str, float, bool)):
            return Value(cast(Any, value))
        raise ValueError("Invalid value payload.")

    if expression_type == "define":
        return DefineVariable(
            variable=_expect_str(payload.get("variable"), "variable name"),
            value=import_expression(payload.get("value")),
        )

    if expression_type == "binary":
        return BinaryOperation(
            left=import_expression(payload.get("left")),
            operator=_expect_str(payload.get("operator"), "binary operator"),
            right=import_expression(payload.get("right")),
        )

    if expression_type == "program":
        expressions = payload.get("expressions")
        if isinstance(expressions, list):
            return Program([import_expression(child) for child in expressions])
        raise ValueError("Invalid program expressions payload.")

    if expression_type == "print":
        return PrintExpression(import_expression(payload.get("expression")))

    raise ValueError(f"Unknown expression type: {expression_type!r}.")


def _expect_object(data: JsonValue, description: str) -> dict[str, JsonValue]:
    if isinstance(data, dict):
        return cast(dict[str, JsonValue], data)
    raise ValueError(f"Expected {description} object.")


def _expect_str(value: JsonValue | None, description: str) -> str:
    if isinstance(value, str):
        return value
    raise ValueError(f"Expected {description}.")


def print_error(result: BaseResultError):
    if result.context_error:
        print("Error before this error:")
        print_error(result.context_error)
    print(f"Error {result.error_code}: {result.error_message}")


class ProgramPrinter:
    def __init__(self, file: IO[str] = sys.stdout):
        self.indent_level = 0
        self.file = file

    def increment_indent(self):
        self.indent_level += 1

    def decrement_indent(self):
        self.indent_level = max(0, self.indent_level - 1)

    @contextmanager
    def indented(self):
        self.increment_indent()
        try:
            yield
        finally:
            self.decrement_indent()

    @contextmanager
    def bracket(self):
        self.write("(")
        try:
            yield
        finally:
            self.write(")")

    def write_indent(self):
        self.file.write("    " * self.indent_level)

    def write(self, message: str):
        self.file.write(message)

    def print_reference(self, var_ref: VariableReference):
        self.write(f"reference {var_ref.name}")

    def print_value(self, value: Value[Any]):
        self.write(f"value {value.value}")

    def print_define_variable(self, define_var: DefineVariable):
        self.write_indent()
        self.write(f"define variable {define_var.variable!r}")
        with self.indented():
            self.write(" ")
            with self.bracket():
                self.print_expression(define_var.value)

    def print_binary_operation(self, bin_op: BinaryOperation):
        self.write_indent()
        self.write(f"binary operation {bin_op.operator!r}")
        self.write(" ")
        with self.bracket():
            self.print_expression(bin_op.left)
            self.print_expression(bin_op.right)

    def print_program(self, program: Program):
        self.write("program: ")
        with self.indented():
            with self.bracket():
                self.write("\n")
                for expression in program.expressions:
                    self.print_expression(expression)
                    self.write("\n")

    def print_print_expression(self, print_expression: PrintExpression):
        self.write_indent()
        self.write("print ")
        with self.bracket():
            self.print_expression(print_expression.expression)

    def print_expression(self, expr: ExpressionForm[Any]):
        if isinstance(expr, VariableReference):
            self.print_reference(expr)
        elif isinstance(expr, Value):
            self.print_value(expr)
        elif isinstance(expr, DefineVariable):
            self.print_define_variable(expr)
        elif isinstance(expr, BinaryOperation):
            self.print_binary_operation(expr)
        elif isinstance(expr, Program):
            self.print_program(expr)
        elif isinstance(expr, PrintExpression):
            self.print_print_expression(expr)
        else:
            self.write(f"Unknown Expression: {type(expr).__name__}")


prog = Program(
    [
        DefineVariable("x", Value(10)),
        DefineVariable("y", BinaryOperation(VariableReference("x"), "+", Value(5))),
        PrintExpression(VariableReference("y")),
    ]
)
prog_result = prog.evaluate(Context())
if prog_result.is_error:
    print_error(prog_result)  # type: ignore
else:
    if isinstance(prog_result, ExpressionResultOK):
        if prog_result.value is not None:
            print(prog_result.value)


# varx = VariableReference("x")

# ctx = Context()
# ctx.set_variable("x", 10)
# var2 = DefineVariable("y", varx)
# var = DefineVariable("x", Value(42))

# program = Program([var2, var, PrintExpression(varx)])
# result = program.evaluate(ctx)
# if result.is_error:
#     print_error(result)  # type: ignore
# else:
#     print("Program evaluated successfully.")
#     for name, value in ctx.variables.items():
#         print(f"{name} = {value}")
# print(export_expression(program))
# printer = ProgramPrinter()
# printer.print_expression(program)
