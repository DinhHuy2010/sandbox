from _typeshed import Incomplete

__all__ = ["interpret"]

class Evaluator:
    operations: Incomplete
    def evaluate(self, expr, context): ...

def interpret(marker, execution_context=None): ...
