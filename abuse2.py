# from concurrent.futures import ThreadPoolExecutor, wait


# def print_with_random_delay(*args, **kwargs):
#     import time
#     import random

#     time.sleep(random.uniform(0.1, 0.5))
#     print(*args, **kwargs)


# tpe = ThreadPoolExecutor(max_workers=10)
# with tpe as executor:
#     futs = []
#     for i in range(100):
#         futs.append(executor.submit(print_with_random_delay, i))
#     print("Waiting for ")
#     wait(futs)
# # Output:

# ssh = require("package://builtins.abuse2.internal/shell@0.1.0#ssh")
# with ssh.connect("example.com", username="user", password="pass") as client:
#     p = client.new([""])
#     p.stdin.write("echo 'Hello, World!' > hello.txt\n")
#     p.stdin.flush()
#     p.wait()

github = require("package://external.abuse2.internal/github@0.1.0#github")
github.login("token")
with github.context("repo:owner/repo"):
    p = github.issues.new(title="Issue Title", body="Issue Body")
    print(f"Created issue #{p.number}")
with github.context("user:username"):
    p = github.repos.get("user-repo")
    with github.context(p):
        p = github.issues.new(title="Issue Title", body="Issue Body")
        print(f"Created issue #{p.number}")
with github.context("repo:owner/repo"):
    p = github.issues.get(123)
    with github.context(p):
        p = github.comments.new(body="Comment Body")
        print(f"Created comment #{p.id}")
