import ast
import importlib
import importlib.util
from abc import ABC, abstractmethod
from importlib.machinery import ModuleSpec, SourceFileLoader
from types import ModuleType

NOT_FOUND = object()


class BaseExternalResolver(ABC):
    @abstractmethod
    def resolve(self, name: str):
        pass

    def is_variable_usable(self, name: str) -> bool:
        return True


class ReturnException(Exception):
    """Control flow exception used to return values from user-defined functions."""

    def __init__(self, value):
        self.value = value


class BreakException(Exception):
    """Control flow exception used to break out of loops."""


class ContinueException(Exception):
    """Control flow exception used to continue to the next iteration of loops."""


class InterpretedException(Exception):
    """Wraps exceptions raised during interpreted code execution."""

    def __init__(self, raw_exception: BaseException):
        self.raw_exception = raw_exception
        super().__init__(f"{type(raw_exception).__name__}: {raw_exception}")


class BaseImporter(ABC):
    @abstractmethod
    def resolve_module(self, module_name: str) -> ModuleSpec:
        pass

    @abstractmethod
    def exec_module(
        self, interpreter: "PythonInterpreter", module_spec: ModuleSpec
    ) -> ModuleType:
        pass


class StandardImporter(BaseImporter):
    def resolve_module(self, module_name: str) -> ModuleSpec:
        # Find where Python would locate this module
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            raise ImportError(f"Module '{module_name}' not found.")
        return spec

    def exec_module(self, interpreter: "PythonInterpreter", module_spec: ModuleSpec):
        # Create an empty module object
        module = importlib.util.module_from_spec(module_spec)

        # Check if the module is a .py file that we can read as AST
        is_python_file = (
            module_spec.origin
            and module_spec.origin.endswith(".py")
            and isinstance(module_spec.loader, SourceFileLoader)
        )

        if is_python_file:
            # 1. Read source code
            with open(module_spec.origin, "r", encoding="utf-8") as f:
                source = f.read()

            # 2. Parse AST
            tree = ast.parse(source, filename=module_spec.origin)

            # 3. Spawn a child sub-interpreter targeting module.__dict__
            # This forces all statements in the module to run in your interpreter
            sub_interpreter = PythonInterpreter(
                resolvers=interpreter.resolvers,
                parent=interpreter,
                initial_variables=module.__dict__,  # Scope populated inside the module
                middlewares=interpreter.middlewares,
                importers=interpreter.importers,
            )

            # 4. Evaluate the AST in the custom interpreter
            sub_interpreter.visit(tree)
        else:
            # Native C-extension (e.g. math, sys, _struct) -> Execute via CPython
            if module_spec.loader:
                module_spec.loader.exec_module(module)

        return module


class UserFunction:
    """Represents a user-defined function in the AST interpreter."""

    def __init__(
        self,
        name: str,
        args: list[str],
        body: list[ast.stmt],
        closure_interpreter: "PythonInterpreter",
    ):
        self.name = name
        self.args = args
        self.body = body
        self.closure_interpreter = closure_interpreter

    def __call__(self, *passed_args, **passed_kwargs):
        # Create a child scope for execution
        local_scope = {}

        # Bind positional arguments
        for param_name, arg_val in zip(self.args, passed_args):
            local_scope[param_name] = arg_val

        # Bind keyword arguments
        for kw_name, kw_val in passed_kwargs.items():
            if kw_name in self.args:
                local_scope[kw_name] = kw_val

        # Execute body inside a child interpreter with local scoping
        child_interpreter = PythonInterpreter(
            resolvers=self.closure_interpreter.resolvers,
            parent=self.closure_interpreter,
            initial_variables=local_scope,
            middlewares=self.closure_interpreter.middlewares,
            importers=self.closure_interpreter.importers,
        )

        try:
            for stmt in self.body:
                child_interpreter.visit(stmt)
        except ReturnException as ret:
            return ret.value

        return None

    def __get__(self, instance, owner):
        # Support method binding when accessed from a class instance
        if instance is None:
            return self  # Accessed from the class itself
        else:
            # Return a bound method that includes the instance as the first argument
            def bound_method(*args, **kwargs):
                return self(instance, *args, **kwargs)

            return bound_method


class _SpecializedNodeVisitor(ast.NodeVisitor):
    def __init__(self, middlewares=None):
        self.middlewares = middlewares if middlewares is not None else []

    def visit(self, node):
        def call_middlewares(index):
            if index < len(self.middlewares):
                return self.middlewares[index](
                    self, type(node).__name__, node, lambda: call_middlewares(index + 1)
                )
            return super(_SpecializedNodeVisitor, self).visit(node)

        return call_middlewares(0)

    def __getattribute__(self, name):
        if not name.startswith("visit_"):
            return super().__getattribute__(name)

        def wrap_with_middlewares(node):
            def call_middlewares(index):
                if index < len(self.middlewares):
                    return self.middlewares[index](
                        self, name, node, lambda: call_middlewares(index + 1)
                    )
                return super(_SpecializedNodeVisitor, self).__getattribute__(name)(node)

            return call_middlewares(0)

        return wrap_with_middlewares


class PythonInterpreter(_SpecializedNodeVisitor):
    def __init__(
        self,
        resolvers: list[BaseExternalResolver] | None = None,
        parent: "PythonInterpreter | None" = None,
        initial_variables: dict | None = None,
        middlewares: list | None = None,
        importers: list[BaseImporter] | None = None,
    ):
        self.variables = initial_variables if initial_variables is not None else {}
        self.resolvers = resolvers if resolvers is not None else []
        self.parent = parent
        self.importers = importers if importers is not None else []
        super().__init__(middlewares=middlewares)

    def resolve_variable(self, name: str):
        # 1. Local scope
        if name in self.variables:
            return self.variables[name]

        # 2. Enclosing/Parent scope
        if self.parent is not None:
            try:
                return self.parent.resolve_variable(name)
            except NameError:
                pass

        # 3. External resolvers
        for resolver in self.resolvers:
            value = resolver.resolve(name)
            if value is not NOT_FOUND:
                return value

        raise NameError(f"Name '{name}' is not defined.")

    def is_variable_assignable(self, name: str) -> bool:
        for resolver in self.resolvers:
            if not resolver.is_variable_usable(name):
                return False
        return True

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not self.is_variable_assignable(node.name):
            raise NameError(f"Cannot define function named '{node.name}'.")

        param_names = [arg.arg for arg in node.args.args]
        func_obj = UserFunction(
            name=node.name,
            args=param_names,
            body=node.body,
            closure_interpreter=self,
        )
        self.variables[node.name] = func_obj
        return func_obj

    def visit_Return(self, node: ast.Return):
        value = self.visit(node.value) if node.value else None
        raise ReturnException(value)

    def visit_Assign(self, node: ast.Assign):
        value = self.visit(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                if not self.is_variable_assignable(target.id):
                    raise NameError(
                        f"Cannot reassign protected variable '{target.id}'."
                    )
                self.variables[target.id] = value
            else:
                raise NotImplementedError("Only simple assignments supported.")

    def visit_Name(self, node: ast.Name):
        match node.ctx:
            case ast.Load():
                return self.resolve_variable(node.id)
            case ast.Store():
                return node.id
            case _:
                raise NotImplementedError(
                    f"Context {type(node.ctx).__name__} unsupported."
                )

    def visit_Call(self, node: ast.Call):
        func = self.visit(node.func)
        if not callable(func):
            raise TypeError(f"'{type(func).__name__}' object is not callable.")

        args = [self.visit(arg) for arg in node.args]
        kwargs = {
            kw.arg: self.visit(kw.value) for kw in node.keywords if kw.arg is not None
        }
        return func(*args, **kwargs)

    def visit_Expr(self, node: ast.Expr):
        return self.visit(node.value)

    def visit_Constant(self, node: ast.Constant):
        return node.value

    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        match node.op:
            case ast.Add():
                return left + right
            case ast.Sub():
                return left - right
            case ast.Mult():
                return left * right
            case ast.Div():
                return left / right
            case ast.Mod():
                return left % right
            case ast.Pow():
                return left**right
            case _:
                raise NotImplementedError(
                    f"Operator {type(node.op).__name__} unsupported."
                )

    def visit_Module(self, node: ast.Module):
        result = None
        for stmt in node.body:
            result = self.visit(stmt)
        return result

    def visit_If(self, node: ast.If):
        condition = self.visit(node.test)
        if condition:
            for stmt in node.body:
                self.visit(stmt)
        else:
            for stmt in node.orelse:
                self.visit(stmt)

    def visit_While(self, node: ast.While):
        while self.visit(node.test):
            try:
                for stmt in node.body:
                    self.visit(stmt)
            except BreakException:
                break
            except ContinueException:
                continue
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_Break(self, node: ast.Break):
        raise BreakException()

    def visit_Continue(self, node: ast.Continue):
        raise ContinueException()

    def visit_Pass(self, node: ast.Pass):
        pass  # No operation for 'pass' statement

    def visit_UnaryOp(self, node: ast.UnaryOp):
        operand = self.visit(node.operand)
        match node.op:
            case ast.UAdd():
                return +operand
            case ast.USub():
                return -operand
            case _:
                raise NotImplementedError(
                    f"Unary operator {type(node.op).__name__} unsupported."
                )

    def visit_Compare(self, node: ast.Compare):
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            match op:
                case ast.Eq():
                    if left != right:
                        return False
                case ast.NotEq():
                    if left == right:
                        return False
                case ast.Lt():
                    if not (left < right):
                        return False
                case ast.LtE():
                    if not (left <= right):
                        return False
                case ast.Gt():
                    if not (left > right):
                        return False
                case ast.GtE():
                    if not (left >= right):
                        return False
                case _:
                    raise NotImplementedError(
                        f"Comparison operator {type(op).__name__} unsupported."
                    )
            left = right  # For chained comparisons
        return True

    def visit_BoolOp(self, node: ast.BoolOp):
        if isinstance(node.op, ast.And):
            for value in node.values:
                if not self.visit(value):
                    return False
            return True
        elif isinstance(node.op, ast.Or):
            for value in node.values:
                if self.visit(value):
                    return True
            return False
        else:
            raise NotImplementedError(
                f"Boolean operator {type(node.op).__name__} unsupported."
            )

    def visit_For(self, node):
        iter_obj = self.visit(node.iter)
        if not hasattr(iter_obj, "__iter__"):
            raise TypeError(f"'{type(iter_obj).__name__}' object is not iterable.")

        for item in iter_obj:
            try:
                # Assign the current item to the target variable
                if isinstance(node.target, ast.Name):
                    self.variables[node.target.id] = item
                else:
                    raise NotImplementedError(
                        "Only simple variable targets are supported in for loops."
                    )

                # Execute the loop body
                for stmt in node.body:
                    self.visit(stmt)
            except BreakException:
                break
            except ContinueException:
                continue

        # Execute the else block if the loop wasn't broken
        if not any(isinstance(stmt, BreakException) for stmt in node.body):
            for stmt in node.orelse:
                self.visit(stmt)

    def visit_Raise(self, node: ast.Raise):
        if node.exc:
            exc = self.visit(node.exc)
            if isinstance(exc, type) and issubclass(exc, BaseException):
                exc = exc()
            if isinstance(exc, BaseException):
                raise InterpretedException(exc)
            raise TypeError("Exceptions must derive from BaseException")
        raise NotImplementedError("Bare 'raise' outside except block is not supported.")

    def visit_Try(self, node: ast.Try):

        try:
            for stmt in node.body:
                self.visit(stmt)
        except (ReturnException, BreakException, ContinueException):
            # Control flow signals bypass except handlers!
            raise
        except (InterpretedException, Exception) as err:  # noqa: BLE001
            # Extract raw exception if it was wrapped or caught natively (e.g. ZeroDivisionError)
            raw_exc = (
                err.raw_exception if isinstance(err, InterpretedException) else err
            )
            handled = False

            for handler in node.handlers:
                if self._match_except_handler(handler, raw_exc):
                    handled = True

                    # Bind exception instance to variable if requested (e.g., 'except Exception as e:')
                    if handler.name:
                        self.variables[handler.name] = raw_exc

                    for stmt in handler.body:
                        self.visit(stmt)
                    break  # Execute only the first matching except block

            if not handled:
                # Re-raise if no except handler matched
                raise (
                    err
                    if isinstance(err, InterpretedException)
                    else InterpretedException(raw_exc)
                )
        else:
            # Runs if NO exception occurred in 'body'
            if node.orelse:
                for stmt in node.orelse:
                    self.visit(stmt)
        finally:
            # Runs unconditionally
            if node.finalbody:
                for stmt in node.finalbody:
                    self.visit(stmt)

    def _match_except_handler(
        self, handler: ast.ExceptHandler, exc: BaseException
    ) -> bool:
        # Bare 'except:' matches all exceptions
        if handler.type is None:
            return True

        expected_type = self.visit(handler.type)
        if isinstance(expected_type, tuple):
            return isinstance(exc, expected_type)
        if isinstance(expected_type, type) and issubclass(expected_type, BaseException):
            return isinstance(exc, expected_type)

        return False

    def visit_List(self, node):
        return [self.visit(elt) for elt in node.elts]

    def visit_Dict(self, node):
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}

    def visit_Subscript(self, node):
        value = self.visit(node.value)
        index = self.visit(node.slice)
        return value[index]

    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Attribute(self, node):
        value = self.visit(node.value)
        return getattr(value, node.attr)

    def visit_AugAssign(self, node):
        target = self.visit(node.target)
        value = self.visit(node.value)

        if isinstance(node.op, ast.Add):
            new_value = target + value
        elif isinstance(node.op, ast.Sub):
            new_value = target - value
        elif isinstance(node.op, ast.Mult):
            new_value = target * value
        elif isinstance(node.op, ast.Div):
            new_value = target / value
        else:
            raise NotImplementedError(
                f"Augmented assignment operator {type(node.op).__name__} unsupported."
            )

        if isinstance(node.target, ast.Name):
            if not self.is_variable_assignable(node.target.id):
                raise NameError(
                    f"Cannot reassign protected variable '{node.target.id}'."
                )
            self.variables[node.target.id] = new_value
        else:
            raise NotImplementedError(
                "Only simple variable targets are supported in augmented assignments."
            )

    def visit_IfExp(self, node):
        condition = self.visit(node.test)
        if condition:
            return self.visit(node.body)
        else:
            return self.visit(node.orelse)

    def visit_FormattedValue(self, node):
        value = self.visit(node.value)
        if node.format_spec is not None:
            format_spec = self.visit(node.format_spec)
            return format(value, format_spec)
        return str(value)

    def visit_Import(self, node):
        for alias in node.names:
            module_name = alias.name
            asname = alias.asname if alias.asname else module_name.split(".")[0]

            # Attempt to resolve the module using importers
            for importer in self.importers:
                try:
                    module_spec = importer.resolve_module(module_name)
                    module = importer.exec_module(self, module_spec)
                    self.variables[asname] = module
                    break  # Successfully imported, exit the loop
                except ImportError:
                    continue  # Try the next importer
            else:
                raise ImportError(f"Module '{module_name}' not found.")

    def visit_ImportFrom(self, node):
        module_name = node.module
        module = None
        for importer in self.importers:
            try:
                module_spec = importer.resolve_module(module_name)
                module = importer.exec_module(self, module_spec)
                break
            except ImportError:
                continue
        else:
            raise ImportError(f"Module '{module_name}' not found.")
        for alias in node.names:
            name = alias.name
            asname = alias.asname if alias.asname else name
            if not hasattr(module, name):
                raise ImportError(f"Module '{module_name}' has no attribute '{name}'.")
            self.variables[asname] = getattr(module, name)

    def visit_ClassDef(self, node: ast.ClassDef):
        # 1. Evaluate base classes
        bases = tuple(self.visit(b) for b in node.bases)

        # Check for invalid/unresolved base classes
        for b in bases:
            if not isinstance(b, type):
                raise TypeError(f"Class '{node.name}' has invalid base class: {b}")

        # 2. Execute class body in a child scope
        class_scope = {}
        class_interpreter = PythonInterpreter(
            resolvers=self.resolvers,
            parent=self,
            initial_variables=class_scope,
            middlewares=self.middlewares,
            importers=self.importers,
        )

        for stmt in node.body:
            class_interpreter.visit(stmt)

        # 3. Construct the native Python class
        class_obj = type(node.name, bases, class_scope)

        # 4. CRITICAL: Store the class in current variables scope so child classes can find it!
        self.variables[node.name] = class_obj
        return class_obj

    def visit_Lambda(self, node):
        param_names = [arg.arg for arg in node.args.args]
        body = [
            ast.Return(value=node.body)
        ]  # Wrap the expression in a Return statement
        return UserFunction(
            name="<lambda>",
            args=param_names,
            body=body,
            closure_interpreter=self,
        )

    def visit_Tuple(self, node):
        return tuple(self.visit(elt) for elt in node.elts)


class DefaultResolver(BaseExternalResolver):
    def resolve(self, name: str):
        return getattr(__builtins__, name, NOT_FOUND)


class BuiltinExceptionResolver(BaseExternalResolver):
    def resolve(self, name: str):
        for exc_name in dir(__builtins__):
            exc_obj = getattr(__builtins__, exc_name)
            if isinstance(exc_obj, type) and issubclass(exc_obj, BaseException):  # noqa: SIM102
                if name == exc_name:
                    return exc_obj
        return NOT_FOUND

    def is_variable_usable(self, name: str) -> bool:
        return True  # Allow overwriting built-in exceptions if desired


code = """
import math
import random

def find_evens(limit):
    evens = []
    i = 0
    while True:
        i = i + 1
        if i > limit:
            break
        
        # Skip odd numbers
        if i % 2 != 0:
            continue
            
        print("Found even number:", i)
        evens.append(i)
    return evens

print(find_evens(6))
try:
    10 / 0
except ZeroDivisionError:
    print("Caught division by zero")
# raise ValueError("This is a test error")
print(math.sqrt(16))
"""

tree = ast.parse(code)
interpreter = PythonInterpreter(
    resolvers=[DefaultResolver(), BuiltinExceptionResolver()],
    importers=[StandardImporter()],
)
interpreter.visit(tree)
