import ast
from collections import defaultdict
from inspect import getmembers, getmro, isclass
from random import Random

generators = defaultdict(list)
classes_fields = {}

for _, member in getmembers(ast, isclass):
    if member.__module__ == "ast":
        # if not hasattr(member, "__deprecated__"):
        #     print(member.__name__)
        bases = getmro(member)[1:-1]
        if not bases:
            continue
        if ast.AST not in bases:
            continue
        if ast.Constant in bases:
            continue
        bases = bases[:-1]
        # print(member, bases)
        # if not bases:
        #     continue
        # print(member.__name__, "inherits from", ", ".join(base.__name__ for base in bases))
        # print(bases[:-1])
        if not bases:
            main_base = None
        else:
            main_base = bases[0]
        # print(member.__name__, bases[:-1])
        # generators[member.__name__] = bases[:-1]
        classes_fields[member.__name__] = member._fields
        if main_base is not None:
            generators[main_base.__name__].append(member.__name__)
        # print(main_base, member.__name__, member._fields)


def print_fn(gen):
    fndef = ast.FunctionDef(
        name=f"generate_{gen}",
        args=ast.arguments(
            posonlyargs=[],
            args=[],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=[
            ast.Raise(
                exc=ast.Call(
                    func=ast.Name(id="NotImplementedError", ctx=ast.Load()),
                    args=[],
                    keywords=[],
                ),
                cause=None,
            )
            if not issubclass(getattr(ast, gen), (ast.operator, ast.expr_context, ast.boolop, ast.cmpop, ast.unaryop))
            else ast.Return(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="ast", ctx=ast.Load()),
                        attr=gen,
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                )
            )
        ],
        decorator_list=[],
        returns=ast.Attribute(
            value=ast.Name(id="ast", ctx=ast.Load()), attr=gen, ctx=ast.Load()
        ),
        type_comment=None,
        type_params=None,
    )
    print(ast.unparse(ast.fix_missing_locations(fndef)))


AST_STUBPATH = "/home/huyonunix/.vscode-server/extensions/ms-python.vscode-pylance-2026.2.1/dist/typeshed-fallback/stdlib/ast.pyi"

with open(AST_STUBPATH, "r") as f:
    ast_stub = f.read()
tree = ast.parse(ast_stub)
deprecated_classes = set()
schemas = {}

for node in ast.walk(tree):
    if not isinstance(node, ast.ClassDef):
        continue
    if node.name not in classes_fields:
        continue
    has_deprecated = False
    for d in node.decorator_list:
        match d:
            case (
                ast.Name(id="deprecated" | "type_check_only")
                | ast.Call(func=ast.Name(id="deprecated" | "type_check_only"))
            ):
                has_deprecated = True
                break
    if has_deprecated:
        deprecated_classes.add(node.name)
        continue


def print_parent_gen(gen, subgens):
    fndef = ast.FunctionDef(
        name=f"generate_{gen}",
        args=ast.arguments(
            posonlyargs=[],
            args=[],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=ast.parse(
            f"x = random.choice([{', '.join(f'generate_{s}' for s in subgens)}])\nreturn x()"
        ).body,
        decorator_list=[],
        returns=ast.Attribute(
            value=ast.Name(id="ast", ctx=ast.Load()), attr=gen, ctx=ast.Load()
        ),
        type_comment=None,
        type_params=None,
    )
    print(ast.unparse(ast.fix_missing_locations(fndef)))


generators = {
    gen: [sg for sg in subgen if sg not in deprecated_classes]
    for gen, subgen in generators.items()
}
print("# pyright: strict")
print()
print("import ast")
print("from random import Random")
print("from typing import Callable")
print("random = Random()")
print("MAX_LIST_SIZE = 300")
print()
print("""
def generate_list[T](gen: Callable[[], T]) -> list[T]:
    return [gen() for _ in range(random.randint(2, MAX_LIST_SIZE))]
""")

for gen, subgen in generators.items():
    print_parent_gen(gen, subgen)
    for sg in subgen:
        print_fn(sg)

# print(generators)


# def anno_expr_to_schema(anno: ast.expr):
#     match anno:
#         case ast.Name(id="str"):
#             return {"type": "string"}
#         case ast.Name(id="int"):
#             return {"type": "integer"}
#         case ast.Name(id="float"):
#             return {"type": "number"}
#         case ast.Name(id="bool"):
#             return {"type": "boolean"}
#         case ast.Subscript(value=ast.Name(id="list"), slice=elt):
#             return {"type": "array", "items": anno_expr_to_schema(elt)}
#         case ast.Subscript(value=ast.Name(id="Optional"), slice=elt):
#             return {"anyOf": [anno_expr_to_schema(elt), {"type": "null"}]}
#         case ast.Subscript(value=ast.Name(id="Union"), slice=elts):
#             if isinstance(elts, ast.Tuple):
#                 return {"anyOf": [anno_expr_to_schema(elt) for elt in elts.elts]}
#             else:
#                 return {"anyOf": [anno_expr_to_schema(elts)]}
#         case ast.BinOp(left=first_anno, op=ast.BitOr(), right=second_anno):
#             return {
#                 "anyOf": [
#                     anno_expr_to_schema(first_anno),
#                     anno_expr_to_schema(second_anno),
#                 ]
#             }
#         case ast.Name(id=id):
#             return {"x-name": id}
#         case ast.Constant(value=None):
#             return {"type": "null"}
#         case ast.Attribute(value=ast.Name(id="ast"), attr=id):
#             return {"x-name": id}
#         case _:
#             raise NotImplementedError(f"Unsupported annotation: {ast.dump(anno)}")


#     for stmt in node.body:
#         match stmt:
#             case ast.AnnAssign(target=ast.Name(id=name), annotation=type):
#                 # print(node.name, classes_fields[node.name])
#                 # print(node.name, name)
#                 anno = ast.get_source_segment(ast_stub, type)
#                 # anno = ast.unparse(type)
#                 # print(f"{node.name}.{name}: {anno}")
#                 # print(anno_expr_to_schema(type))
#                 schemas[f"{node.name}.{name}"] = anno_expr_to_schema(type)


# def build_schema_for_class(class_name):
#     fields = classes_fields[class_name]
#     schema = {"type": "object", "properties": {}}
#     for field in fields:
#         field_schema = schemas.get(f"{class_name}.{field}")
#         if field_schema is not None:
#             schema["properties"][field] = field_schema
#     return schema


# def write_gen_function(class_name, fields):
#     ...

# t = write_gen_function("Expr", classes_fields["Expr"])

# print(ast.unparse(ast.fix_missing_locations(t)))
