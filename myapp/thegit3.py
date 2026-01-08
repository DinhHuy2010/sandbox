import pygit2

repo = pygit2.Repository("/tmp/cpython.git")
for oid in repo.odb:
    print(repo.git_object_lookup_prefix(oid))
