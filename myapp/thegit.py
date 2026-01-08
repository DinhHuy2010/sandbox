import email
import email.parser
from typing import cast
import pygit2


def walk(o: pygit2.Tree, *, depth: int = 0):
    for entry in o:
        if isinstance(entry, pygit2.Tree):
            print(f"{'  ' * depth}", (entry.name or "???") + "/")
            walk(entry, depth=depth + 1)
        elif isinstance(entry, pygit2.Blob):
            print(f"{'  ' * depth}", entry.name)


p = email.parser.BytesParser()

repo = pygit2.Repository("/tmp/git-mailing-list-lore.kernel.org")
for entry in repo.walk(repo.head.target):
    msg = cast(pygit2.Blob, next(iter(entry.tree)))
    msg = p.parsebytes(msg.data)
    print(msg["Subject"])
    # break
