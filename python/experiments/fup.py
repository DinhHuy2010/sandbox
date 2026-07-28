import hashlib
import subprocess
import zlib
from datetime import datetime
from pathlib import Path
from shutil import rmtree

from faker import Faker
from tqdm import tqdm

path = Path("./temp/test-repo.git")
faker = Faker()


def git(*args: str, cwd: str | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {result.stderr}")
    return result.stdout.strip()


def build_object(type: str, content: bytes) -> bytes:
    # Generates the raw header + content structure Git expects
    header = f"{type} {len(content)}\0".encode()
    return header + content


def hash_object(type: str, content: bytes) -> str:
    object_data = build_object(type, content)
    hashlib_obj = hashlib.sha1(object_data)
    return hashlib_obj.hexdigest()


def write_object(type: str, content: bytes) -> str:
    object_hash = hash_object(type, content)
    object_path = path / "objects" / object_hash[:2] / object_hash[2:]
    object_path.parent.mkdir(parents=True, exist_ok=True)
    with object_path.open("wb") as f:
        f.write(zlib.compress(build_object(type, content)))
    return object_hash


DEFAULT_MODE = "100644"
TREE = "40000"


def create_tree(entries: list[tuple[str, str, str]]) -> bytes:
    # Custom sorting key function to match Git's internal C implementation
    def git_tree_sort_key(entry):
        mode, name, _ = entry
        # If it's a directory (mode 40000), Git sorts it as if it ends with a '/'
        if mode == "40000":
            return name + "/"
        return name

    # CRITICAL: Git requires tree entries to be strictly sorted by filename
    sorted_entries = sorted(entries, key=git_tree_sort_key)

    tree_content = b""
    for mode, name, object_hash in sorted_entries:
        tree_content += f"{mode} {name}\0".encode() + bytes.fromhex(object_hash)

    # We return the raw content bytes to be passed into write_object
    return tree_content


def create_commit(
    tree_hash: str, parent_hash: str | None, message: str, author: str
) -> bytes:
    # Git requires a Unix timestamp and a timezone offset on the identity lines
    timestamp = int(datetime.now().timestamp())
    identity_with_time = f"{author} {timestamp} +0000"

    commit_content = f"tree {tree_hash}\n"
    if parent_hash:
        commit_content += f"parent {parent_hash}\n"
    commit_content += f"author {identity_with_time}\n"
    commit_content += f"committer {identity_with_time}\n"  # Git needs a committer too!
    commit_content += f"\n{message}\n"
    return commit_content.encode()


def create_ref(ref_name: str, commit_hash: str) -> None:
    ref_path = (
        path / "refs" / ref_name.removeprefix("refs/")
    )  # Ensure we don't have duplicate 'refs/' in the path
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    with ref_path.open("w") as f:
        f.write(commit_hash + "\n")


def build_tree(depth: int = 3) -> str:
    entries = []
    nblobs = faker.random_int(min=5, max=5)
    ntrees = faker.random_int(min=0, max=2) if depth > 0 else 0
    # print(f"Building tree at depth {depth} with {nblobs} blobs and {ntrees} subtrees")
    for _ in range(nblobs):
        blob_content = faker.text().encode()
        blob_hash = write_object("blob", blob_content)
        entries.append((DEFAULT_MODE, faker.file_name(), blob_hash))
    for _ in range(ntrees):
        subtree_hash = build_tree(depth - 1)
        entries.append((TREE, faker.file_name(extension=""), subtree_hash))

    tree_content = create_tree(entries)
    p = write_object("tree", tree_content)
    # print(f"Created tree at {p}")
    return p


# Reset and init the repo
if path.exists():
    rmtree(path, ignore_errors=True)
git("-c", "init.defaultBranch=main", "init", "--bare", str(path))

parent_commit = None
commits: list[str] = []

for _ in tqdm(range(10**3)):  # Create a few commits to have some history
    tree = build_tree()
    commit_content = create_commit(
        tree, parent_commit, faker.paragraph(), f"{faker.name()} <{faker.email()}>"
    )
    commit_hash = write_object("commit", commit_content)
    create_ref("heads/main", commit_hash)
    # print(f"Created ref heads/main pointing to {commit_hash}")
    # print(f"Created commit at {commit_hash}")
    parent_commit = commit_hash
    commits.append(commit_hash)

for _ in tqdm(range(10**3)):  # Create some tags pointing to random commits
    target_commit = faker.random_element(elements=commits)
    tag_content = f"object {target_commit}\ntype commit\ntag {faker.word()}\ntagger {faker.name()} <{faker.email()}> {int(datetime.now().timestamp())} +0000\n\n{faker.sentence()}\n".encode()
    tag_hash = write_object("tag", tag_content)
    create_ref(f"refs/tags/{faker.word()}", tag_hash)

for _ in tqdm(range(10**3)):  # Create some branches pointing to random commits
    target_commit = faker.random_element(elements=commits)
    create_ref(f"refs/heads/{faker.word()}", target_commit)

print("Repository setup complete.")
