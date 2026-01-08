from libresolver.core import resolve, init_core

init_core()

print(resolve("python:version?output=string"))  # Example usage

# resolve("game:guess-the-number?difficulty=hard")