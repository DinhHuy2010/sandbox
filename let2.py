"""
Parser + interpreter for the /command-call grammar:

    <command_call> = /<command> <values[]> <option[]>
    <command>      = IDENT ('.' IDENT)*         # dot-namespaced, so the
                                                  # command name is unambiguous
                                                  # from the values that follow
    <values>       = STRING | NUMBER | FLOAT | <magicref> | <file> | <nested_call>
    <nested_call>  = /( <command_call, no leading '/' before the '('> )
    <option>       = ('-'|'--') IDENT [<values>]  # no value => boolean flag
    <file>         = @<path>                      # no whitespace in path
    <magicref>     = <anything inside angle brackets>

    <function_def> =
        :define <name>
        :parameters <p1> <p2> ...
        :start
        <command_call>*
        :end
        [-scoped | -global]      # optional, default = global

Resolved ambiguities (per spec discussion):
  1. Nested /( ... ) calls are AST nodes (CommandCall), evaluated lazily
     at the point their containing call actually needs the value.
  2. <magicref> can resolve to any type - plain dynamic lookup at eval time.
  3. Every option takes exactly one value, or none (boolean flag). Only
     positional `values` are ever a list.
  4. Functions can be defined -scoped (visible only within the frame that
     is active while it's defined - relevant once functions nest) or
     -global (visible everywhere, forever). Default is -global.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

# ============================================================ Lexer ==

TOKEN_SPEC = [
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t]+"),
    ("COMMENT", r"\#[^\n]*"),
    ("MAGICREF", r"<[^<>\n]*>"),
    ("FILEREF", r"@[^\s()]+"),
    ("STRING", r'"(?:\\.|[^"\\])*"'),
    ("FLOAT", r"-?\d+\.\d+"),
    ("NUMBER", r"-?\d+"),
    ("DASHDASH", r"--[A-Za-z_][A-Za-z0-9_\-]*"),
    ("DASH", r"-[A-Za-z_][A-Za-z0-9_\-]*"),
    ("COLON", r":"),
    ("SLASH", r"/"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("DOT", r"\."),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("MISMATCH", r"."),
]
MASTER_RE = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC))


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    pos: int


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    for m in MASTER_RE.finditer(src):
        kind = m.lastgroup
        val = m.group()
        if kind in ("SKIP", "COMMENT"):
            continue
        if kind == "MISMATCH":
            raise SyntaxError(f"Unexpected character {val!r} at position {m.start()}")
        tokens.append(Token(kind, val, m.start()))
    tokens.append(Token("EOF", "", len(src)))
    return tokens


# ============================================================== AST ==


@dataclass(frozen=True)
class MagicRef:
    name: str


@dataclass(frozen=True)
class FileRef:
    path: str


@dataclass(frozen=True)
class Option:
    name: str
    value: Optional["Value"]
    long: bool


@dataclass(frozen=True)
class CommandCall:
    path: tuple[str, ...]
    values: tuple["Value", ...]
    options: tuple[Option, ...]

    @property
    def name(self) -> str:
        return ".".join(self.path)


@dataclass(frozen=True)
class FunctionDef:
    name: str
    params: tuple[str, ...]
    body: tuple[CommandCall, ...]
    scope: str  # "scoped" | "global"


Value = Union[str, int, float, MagicRef, FileRef, CommandCall]
Statement = Union[CommandCall, FunctionDef]


# ============================================================ Parser ==


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]):
        self.toks = tokens
        self.i = 0

    # -- token stream helpers ------------------------------------------
    def peek(self, offset: int = 0) -> Token:
        j = self.i + offset
        return self.toks[j] if j < len(self.toks) else self.toks[-1]

    def advance(self) -> Token:
        t = self.toks[self.i]
        if t.kind != "EOF":
            self.i += 1
        return t

    def expect(self, kind: str) -> Token:
        t = self.peek()
        if t.kind != kind:
            raise ParseError(f"Expected {kind}, got {t.kind} ({t.value!r}) at {t.pos}")
        return self.advance()

    def skip_newlines(self) -> None:
        while self.peek().kind == "NEWLINE":
            self.advance()

    def at_keyword(self, word: str) -> bool:
        return (
            self.peek().kind == "COLON"
            and self.peek(1).kind == "IDENT"
            and self.peek(1).value == word
        )

    # -- top level -------------------------------------------------------
    def parse_program(self) -> list[Statement]:
        stmts: list[Statement] = []
        self.skip_newlines()
        while self.peek().kind != "EOF":
            if self.at_keyword("define"):
                stmts.append(self.parse_function_def())
            elif self.peek().kind == "SLASH":
                stmts.append(self.parse_command_call())
            else:
                raise ParseError(f"Unexpected token {self.peek()} at top level")
            self.skip_newlines()
        return stmts

    # -- function definitions ---------------------------------------------
    def parse_function_def(self) -> FunctionDef:
        self.expect("COLON")
        self.expect("IDENT")  # 'define'
        name_val = self.parse_value()
        name = name_val if isinstance(name_val, str) else str(name_val)
        self.skip_newlines()

        self.expect("COLON")
        kw = self.expect("IDENT")
        if kw.value != "parameters":
            raise ParseError("Expected ':parameters' after ':define <name>'")
        params: list[str] = []
        while self.peek().kind not in ("NEWLINE", "EOF"):
            pv = self.parse_value()
            params.append(pv if isinstance(pv, str) else str(pv))
        self.skip_newlines()

        self.expect("COLON")
        kw = self.expect("IDENT")
        if kw.value != "start":
            raise ParseError("Expected ':start' after ':parameters ...'")
        self.skip_newlines()

        body: list[CommandCall] = []
        while not self.at_keyword("end"):
            if self.peek().kind == "EOF":
                raise ParseError("Unterminated function body, missing ':end'")
            body.append(self.parse_command_call())
            self.skip_newlines()

        self.expect("COLON")
        self.expect("IDENT")  # 'end'

        scope = "global"
        if self.peek().kind in ("DASH", "DASHDASH"):
            flag = self.advance().value.lstrip("-")
            if flag in ("scoped", "global"):
                scope = flag
            else:
                raise ParseError(f"Unknown function definition flag {flag!r}")

        return FunctionDef(
            name=name, params=tuple(params), body=tuple(body), scope=scope
        )

    # -- command calls -----------------------------------------------------
    def parse_command_call(self, *, nested: bool = False) -> CommandCall:
        # Only a top-level call consumes its own leading '/'; a nested
        # /( ... ) call has its '/' and '(' consumed by parse_value already.
        if not nested:
            self.expect("SLASH")
        path = self.parse_command_path()

        values: list[Value] = []
        options: list[Option] = []
        stop_kinds = {"RPAREN"} if nested else {"NEWLINE"}
        while self.peek().kind not in stop_kinds and self.peek().kind != "EOF":
            if self.peek().kind == "DASH":
                options.append(self.parse_option(long=False))
            elif self.peek().kind == "DASHDASH":
                options.append(self.parse_option(long=True))
            else:
                values.append(self.parse_value())

        return CommandCall(
            path=tuple(path), values=tuple(values), options=tuple(options)
        )

    def parse_command_path(self) -> list[str]:
        parts = [self.expect("IDENT").value]
        while self.peek().kind == "DOT":
            self.advance()
            parts.append(self.expect("IDENT").value)
        return parts

    def parse_option(self, *, long: bool) -> Option:
        tok = self.advance()  # DASH or DASHDASH; value includes leading dashes
        name = tok.value.lstrip("-")
        nxt = self.peek()
        takes_value = nxt.kind not in ("NEWLINE", "EOF", "RPAREN", "DASH", "DASHDASH")
        value = self.parse_value() if takes_value else None
        return Option(name=name, value=value, long=long)

    def parse_value(self) -> Value:
        t = self.peek()
        if t.kind == "STRING":
            self.advance()
            return _unescape_string(t.value[1:-1])
        if t.kind == "NUMBER":
            self.advance()
            return int(t.value)
        if t.kind == "FLOAT":
            self.advance()
            return float(t.value)
        if t.kind == "MAGICREF":
            self.advance()
            return MagicRef(t.value[1:-1])
        if t.kind == "FILEREF":
            self.advance()
            return FileRef(t.value[1:])
        if t.kind == "IDENT":
            self.advance()  # bare word -> treated as a string literal
            return t.value
        if t.kind == "SLASH" and self.peek(1).kind == "LPAREN":
            self.advance()  # SLASH
            self.advance()  # LPAREN
            call = self.parse_command_call(nested=True)
            self.expect("RPAREN")
            return call
        raise ParseError(
            f"Unexpected token {t.kind} ({t.value!r}) in value position at {t.pos}"
        )


def _unescape_string(s: str) -> str:
    return s.encode("utf-8").decode("unicode_escape")


def parse(src: str) -> list[Statement]:
    return Parser(tokenize(src)).parse_program()


# =========================================================== Runtime ==


class DSLError(Exception):
    pass


class Frame:
    """One lexical scope: local vars (params/magicrefs) + scoped functions."""

    def __init__(self, parent: Optional["Frame"] = None):
        self.parent = parent
        self.vars: dict[str, Any] = {}
        self.functions: dict[str, FunctionDef] = {}

    def get_var(self, name: str) -> Any:
        f: Optional[Frame] = self
        while f is not None:
            if name in f.vars:
                return f.vars[name]
            f = f.parent
        raise DSLError(f"Unresolved magicref <{name}>")

    def find_function(self, name: str) -> Optional[FunctionDef]:
        f: Optional[Frame] = self
        while f is not None:
            if name in f.functions:
                return f.functions[name]
            f = f.parent
        return None


class Interpreter:
    def __init__(self, base_dir: str | Path = "."):
        self.base_dir = Path(base_dir)
        self.global_frame = Frame()
        self.builtins: dict[str, Any] = {}
        self._install_builtins()

    # -- builtin commands --------------------------------------------------
    def _install_builtins(self) -> None:
        def _print(args, opts, frame):
            text = " ".join(str(a) for a in args)
            print(text)
            return text

        def _set(args, opts, frame):
            if len(args) != 2:
                raise DSLError("/set requires exactly 2 values: name, value")
            name, value = args
            self.global_frame.vars[str(name)] = value
            return value

        def _add(args, opts, frame):
            return sum(args)

        def _sub(args, opts, frame):
            result = args[0]
            for a in args[1:]:
                result -= a
            return result

        def _mul(args, opts, frame):
            result = 1
            for a in args:
                result *= a
            return result

        def _concat(args, opts, frame):
            sep = opts.get("sep", "")
            return str(sep).join(str(a) for a in args)

        def _len(args, opts, frame):
            return len(args[0])

        def _echo(args, opts, frame):
            return {"values": list(args), "options": opts}

        self.builtins.update(
            {
                "print": _print,
                "set": _set,
                "add": _add,
                "sub": _sub,
                "mul": _mul,
                "concat": _concat,
                "len": _len,
                "echo": _echo,
            }
        )

    # -- program execution ---------------------------------------------------
    def run(self, source: str) -> list[Any]:
        program = parse(source)
        results: list[Any] = []
        for stmt in program:
            if isinstance(stmt, FunctionDef):
                # Top level has only one active frame, so -scoped and
                # -global are equivalent here; the distinction takes effect
                # once a :define appears inside another function's body,
                # where -scoped would register on that call's local frame
                # instead of self.global_frame.
                self.global_frame.functions[stmt.name] = stmt
            else:
                results.append(self.exec_call(stmt, self.global_frame))
        return results

    # -- evaluation -------------------------------------------------------------
    def eval_value(self, value: Value, frame: Frame) -> Any:
        if isinstance(value, (str, int, float)):
            return value
        if isinstance(value, MagicRef):
            return frame.get_var(value.name)
        if isinstance(value, FileRef):
            path = Path(value.path)
            if not path.is_absolute():
                path = self.base_dir / path
            return path.read_text()
        if isinstance(value, CommandCall):
            return self.exec_call(value, frame)
        raise DSLError(f"Cannot evaluate value of type {type(value)}")

    def exec_call(self, call: CommandCall, frame: Frame) -> Any:
        args = [self.eval_value(v, frame) for v in call.values]
        opts = {
            o.name: (self.eval_value(o.value, frame) if o.value is not None else True)
            for o in call.options
        }

        fn_def = frame.find_function(call.name)
        if fn_def is not None:
            return self._call_user_function(fn_def, args, opts, frame)

        builtin = self.builtins.get(call.name)
        if builtin is not None:
            return builtin(args, opts, frame)

        raise DSLError(f"Unknown command: /{call.name}")

    def _call_user_function(
        self, fn: FunctionDef, args: list[Any], opts: dict, caller_frame: Frame
    ) -> Any:
        parent = self.global_frame if fn.scope == "global" else caller_frame
        call_frame = Frame(parent=parent)
        for i, pname in enumerate(fn.params):
            call_frame.vars[pname] = args[i] if i < len(args) else None
        call_frame.vars.update(opts)  # options are reachable as magicrefs too

        result = None
        for stmt in fn.body:
            result = self.exec_call(stmt, call_frame)
        return result


# ============================================================== CLI ==


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        script_path = Path(argv[1])
        src = script_path.read_text()
        base_dir = script_path.parent
    else:
        src = DEMO_SCRIPT
        base_dir = "."

    interp = Interpreter(base_dir=base_dir)
    try:
        interp.run(src)
    except (ParseError, SyntaxError, DSLError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


DEMO_SCRIPT = r"""
:define greet
:parameters name greeting
:start
/print /(concat <greeting> ", " <name> "!" -sep "")
:end -global

/set username "Huy"
/greet <username> "Hello"

/print "2+3+5 =" /(add 2 3 5)
/print "2*(1+1)*3 =" /(mul 2 /(add 1 1) 3)
/print "file contents:" @example.script
/print "echo test:" /(echo "a" "b" -flag)
"""

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
