# pyright: standard

from lark import Lark, Token

ebnf = """
?start: expr

?expr: operator
     | list
     | NAME
     | NUMBER

list: expr ("," expr)*

?operator: "(" expr "+" expr ")" -> operator_add
         | "(" expr "-" expr ")" -> operator_sub
         | "(" expr "*" expr ")" -> operator_mul
         | "(" expr "/" expr ")" -> operator_div

%import common.NUMBER
%import common.CNAME -> NAME
%import common.WS
%ignore WS
"""

lk = Lark(ebnf)


def test_parser():
    tree = lk.parse("abc, def, (ghi+jkl), (mno-pqr), (stu*vw), (xyz/123)")
    if isinstance(tree, Token):
        print(tree)
    else:
        print(tree.pretty())


if __name__ == "__main__":
    test_parser()
