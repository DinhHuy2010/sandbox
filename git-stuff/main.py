import pathlib
import random
import tempfile

import faker
import pygit2

BASE_TMP_PATH = pathlib.Path("./temp-git-repository")
BASE_TMP_PATH.mkdir(exist_ok=True)
INIT_REF = "refs/heads/main"

rand = random.SystemRandom()


def create_blob(repo: pygit2.Repository) -> pygit2.Blob:
    blob = rand.randbytes(1024)  # Create a blob with 1KB of random data
    blob_id = repo.create_blob(blob)
    print(f"Created a new blob with ID: {blob_id}")
    return repo[blob_id].peel(pygit2.Blob)


def create_tree(
    repo: pygit2.Repository, objects_ids: list[pygit2.Blob | pygit2.Tree]
) -> pygit2.Tree:
    tree_builder = repo.TreeBuilder()
    for obj in objects_ids:
        # Add each object to the tree with a random name and mode
        name = f"object_{rand.randint(1, 100)}"
        if isinstance(obj, pygit2.Blob):
            name += ".bin"
        mode = (
            pygit2.GIT_FILEMODE_BLOB
            if isinstance(obj, pygit2.Blob)
            else pygit2.GIT_FILEMODE_TREE
        )
        tree_builder.insert(name, obj.id, mode)
        print(
            f"Added object with ID: {obj.id} to the tree as '{name}' with mode {mode}"
        )
    tree_id = tree_builder.write()
    print(f"Created a new tree with ID: {tree_id}")
    return repo[tree_id].peel(pygit2.Tree)
    # return tree_id


def create_deep_tree(repo: pygit2.Repository, depth: int) -> pygit2.Tree:
    if depth == 0:
        return create_tree(repo, [create_blob(repo) for _ in range(3)])
    should_create_subtrees = fake.boolean()
    blobs = [create_blob(repo) for _ in range(fake.random_digit())]
    if should_create_subtrees:
        subtrees = [create_deep_tree(repo, depth - 1) for _ in range(2)]
        return create_tree(repo, blobs + subtrees)
    return create_tree(repo, blobs)


fake = faker.Faker()
commits = []
with tempfile.TemporaryDirectory(
    prefix="repository", suffix=".git", dir=BASE_TMP_PATH, delete=False
) as tmp_dir:
    print(f"Creating a temporary git repository at: {tmp_dir}")
    repo = pygit2.init_repository(tmp_dir, bare=True, initial_head=INIT_REF)
    print(f"Initialized a new git repository at: {repo.path}")
    # Create a new commit
    author = pygit2.Signature(fake.name(), fake.email())
    # committer = pygit2.Signature(fake.name(), "jane.doe@example.com")
    parents: list[str] = []
    for _ in range(10**3):  # Create 2 commits with random blobs
        tree = create_deep_tree(repo, depth=3)  # Create a tree with a depth of 3
        commit_message = fake.sentence()  # Generate a random commit message
        commit_id = repo.create_commit(
            INIT_REF, author, author, commit_message, tree.id, parents
        )
        print(f"Created a new commit with ID: {commit_id}")
        parents = [
            commit_id
        ]  # Set the current commit as the parent for the next commit
        commits.append(commit_id)
    for _ in range(500):
        ref = repo.references.create(
            f"refs/heads/branch_{fake.hex_color()[1:]}", random.choice(commits)
        )
        print(ref)

print(f"Finished creating commits in the repository at: {repo.path}")
