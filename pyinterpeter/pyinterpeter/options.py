from dataclasses import dataclass


@dataclass
class Options:
    debug: bool = False
    future_op_enabled: bool = False
