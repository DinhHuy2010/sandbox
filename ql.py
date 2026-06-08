# def ql(*a, **b):
#     if not a and not b:
#         print("Hello, world!")
#         return "OK"
#     elif b["action"] == "setState":
#         key, val = b["key"], b["value"]
#         ql.state[key] = val
#         return "OK"
#     elif b["action"] == "getState":
#         key = a[0]
#         ql.value = ql.state.get(key, __sentinel__)
#         return "OK"
#     elif b["action"] == "deleteState":
#         key = b["key"]
#         del ql.state[key]
#         return "OK"
#     elif b["action"] == "clearState":
#         ql.state.clear()
#         return "OK"
#     else:
#         print("Unknown action:", b["action"])
#         return "ERROR"


# __sentinel__ = object()
# ql.state = {}
# ql.value = __sentinel__

# ql(action="setState", key="foo", value=42)
# ql("foo", action="getState")
# print("Value:", ql.value)  # Should print: Value: 42

# __sentinel__ = object()


# class StateMachine[T]:
#     def __init__(self, initial_state: T = __sentinel__):
#         self.state: T = initial_state

#     def set_state(self, new_state: T):
#         self.state = new_state
#         # print(f"State set to: {self.state}")

#     def get_state(self) -> T:
#         # print(f"Current state: {self.state}")
#         return self.state

#     def clear_state(self) -> None:
#         self.state = __sentinel__
#         # print("State cleared to sentinel value.")

#     def is_state_set(self) -> bool:
#         return self.state is not __sentinel__

#     def __get__(self, instance, owner):
#         return self.get_state()

#     def __set__(self, instance, value):
#         self.set_state(value)

#     def __delete__(self, instance):
#         self.clear_state()


# class Example:
#     a = StateMachine(0)
#     b = StateMachine("initial")


# Example.c = StateMachine(Example())
# e = Example()
# print(e.c.c.c.c)

# from dataclasses import dataclass
# from datetime import datetime


# @dataclass
# class Node:
#     type: str
#     content: str


# @dataclass
# class Content:
#     nodes: list[Node]


# @dataclass
# class Section:
#     title: str
#     content: Content


# @dataclass
# class Content:
#     sections: list[Section]


# @dataclass
# class Revision:
#     content: Content
#     comment: str
#     published: datetime
#     past: "Revision | None" = None


# @dataclass
# class Page:
#     title: str
#     categories: list["Category"]
#     revision: Revision


# @dataclass
# class Category(Page):
#     pages: list[Page]


# @dataclass
# class Wiki:
#     pages: list[Page]


# p1 = Page(
#     title="Page 1",
#     categories=[],
#     revision=Revision(
#         content=Content(
#             sections=[
#                 Section(
#                     title="Section 1",
#                     content=Content(
#                         nodes=[
#                             Node(
#                                 type="paragraph",
#                                 content="This is the first section of page 1.",
#                             ),
#                             Node(type="paragraph", content="It has some text content."),
#                         ]
#                     ),
#                 ),
#                 Section(
#                     title="Section 2",
#                     content=Content(
#                         nodes=[
#                             Node(
#                                 type="paragraph",
#                                 content="This is the second section of page 1.",
#                             ),
#                             Node(
#                                 type="paragraph",
#                                 content="It also has some text content.",
#                             ),
#                             Node(type="link", content="https://example.com/"),
#                         ]
#                     ),
#                 ),
#             ]
#         ),
#         comment="Initial revision",
#         published=datetime.now(),
#     ),
# )
# p2 = Category(
#     title="Category 1",
#     categories=[],
#     revision=Revision(
#         content=Content(
#             sections=[
#                 Section(
#                     title="Section 1",
#                     content=Content(
#                         nodes=[
#                             Node(
#                                 type="paragraph",
#                                 content="This is the first section of category 1.",
#                             ),
#                             Node(type="paragraph", content="It has some text content."),
#                         ]
#                     ),
#                 ),
#             ]
#         ),
#         comment="Initial revision",
#         published=datetime.now(),
#     ),
#     pages=[p1],
# )

# wiki = Wiki(pages=[p1, p2])
