import argparse
import builtins
from pyinterpeter import Options, ScriptRunner


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A Python interpreter implemented in Python."
    )
    parser.add_argument("file", nargs="?", help="The Python file to execute.")
    parser.add_argument(
        "--future-op", action="store_true", help="Make binary operation lazy"
    )
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    if args.file:
        with open(args.file, "r") as f:
            code = f.read()
        runner = ScriptRunner(
            Options(debug=args.debug, future_op_enabled=args.future_op)
        )
        runner.run(code, builtins=builtins.__dict__, filename=args.file)


if __name__ == "__main__":
    main()
