# # import ast
# # from inspect import getsource


# # def on_error_impl(func, /, *handlers_args, else_block=None, finally_block=None):
# #     caught = False
# #     try:
# #         return func()
# #     except BaseException as e:
# #         for exc_type, handler in handlers_args:
# #             if isinstance(e, exc_type):
# #                 caught = True
# #                 return handler(e)
# #         raise
# #     finally:
# #         if else_block is not None and not caught:
# #             else_block()
# #         if finally_block is not None:
# #             finally_block()


# # TARGET = getsource(on_error_impl)
# # tree = ast.parse(TARGET)
# # names = set()
# # for node in ast.walk(tree):
# #     names.add(type(node).__name__)
# # names.add("fix_missing_locations")
# # names = sorted(names)
# # print(
# #     ", ".join(names), "=", "names[" + ", ".join(f'"ast:{name}"' for name in names) + "]"
# # )
# # print("__on_error_impl_tree =", ast.dump(tree))

# import ast


# x = """
# Module(
#         body=[
#             FunctionDef(
#                 name="on_error_impl",
#                 args=arguments(
#                     posonlyargs=[arg(arg="func")],
#                     args=[],
#                     vararg=arg(arg="handlers_args"),
#                     kwonlyargs=[arg(arg="else_block"), arg(arg="finally_block")],
#                     kw_defaults=[Constant(value=None), Constant(value=None)],
#                     defaults=[],
#                 ),
#                 body=[
#                     Assign(
#                         targets=[Name(id="caught", ctx=Store())],
#                         value=Constant(value=False),
#                     ),
#                     Try(
#                         body=[
#                             Return(
#                                 value=Call(
#                                     func=Name(id="func", ctx=Load()),
#                                     args=[],
#                                     keywords=[],
#                                 )
#                             )
#                         ],
#                         handlers=[
#                             ExceptHandler(
#                                 type=Name(id="BaseException", ctx=Load()),
#                                 name="e",
#                                 body=[
#                                     For(
#                                         target=Tuple(
#                                             elts=[
#                                                 Name(id="exc_type", ctx=Store()),
#                                                 Name(id="handler", ctx=Store()),
#                                             ],
#                                             ctx=Store(),
#                                         ),
#                                         iter=Name(id="handlers_args", ctx=Load()),
#                                         body=[
#                                             If(
#                                                 test=Call(
#                                                     func=Name(
#                                                         id="isinstance", ctx=Load()
#                                                     ),
#                                                     args=[
#                                                         Name(id="e", ctx=Load()),
#                                                         Name(id="exc_type", ctx=Load()),
#                                                     ],
#                                                     keywords=[],
#                                                 ),
#                                                 body=[
#                                                     Assign(
#                                                         targets=[
#                                                             Name(
#                                                                 id="caught", ctx=Store()
#                                                             )
#                                                         ],
#                                                         value=Constant(value=True),
#                                                     ),
#                                                     Return(
#                                                         value=Call(
#                                                             func=Name(
#                                                                 id="handler", ctx=Load()
#                                                             ),
#                                                             args=[
#                                                                 Name(id="e", ctx=Load())
#                                                             ],
#                                                             keywords=[],
#                                                         )
#                                                     ),
#                                                 ],
#                                                 orelse=[],
#                                             )
#                                         ],
#                                         orelse=[],
#                                     ),
#                                     Raise(),
#                                 ],
#                             )
#                         ],
#                         orelse=[],
#                         finalbody=[
#                             If(
#                                 test=BoolOp(
#                                     op=And(),
#                                     values=[
#                                         Compare(
#                                             left=Name(id="else_block", ctx=Load()),
#                                             ops=[IsNot()],
#                                             comparators=[Constant(value=None)],
#                                         ),
#                                         UnaryOp(
#                                             op=Not(),
#                                             operand=Name(id="caught", ctx=Load()),
#                                         ),
#                                     ],
#                                 ),
#                                 body=[
#                                     Expr(
#                                         value=Call(
#                                             func=Name(id="else_block", ctx=Load()),
#                                             args=[],
#                                             keywords=[],
#                                         )
#                                     )
#                                 ],
#                                 orelse=[],
#                             ),
#                             If(
#                                 test=Compare(
#                                     left=Name(id="finally_block", ctx=Load()),
#                                     ops=[IsNot()],
#                                     comparators=[Constant(value=None)],
#                                 ),
#                                 body=[
#                                     Expr(
#                                         value=Call(
#                                             func=Name(id="finally_block", ctx=Load()),
#                                             args=[],
#                                             keywords=[],
#                                         )
#                                     )
#                                 ],
#                                 orelse=[],
#                             ),
#                         ],
#                     ),
#                 ],
#                 decorator_list=[],
#                 type_params=[],
#             )
#         ],
#         type_ignores=[],
#     )
# """
# print(ast.unparse(ast.fix_missing_locations(eval(x, {**ast.__dict__}))))


from inspect import getsource


def _(f, /, *a, e=None, fb=None):
    c = False
    try:
        return f()
    except BaseException as e:
        for t, h in a:
            if isinstance(e, t):c = True;return h(e)
        raise
    finally:
        if e is not None and (not c):e()
        if fb is not None:fb()
print(repr(getsource(_).replace(" " * 4, "\x00")))