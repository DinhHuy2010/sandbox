from pygit2 import clone_repository

repo = clone_repository(
    "https://github.com/freeCodeCamp/freeCodeCamp.git",
    "./temp-git-repository/inf-repo.git",
    bare=True,
)
