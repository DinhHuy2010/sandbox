import Python.builtins

Python.builtins.startmaindef()
class Main:
    @Python.builtins.staticmethod
    def main():
        Python.builtins.io.print("Hello, World!")
        Python.builtins.done()
Python.builtins.endmaindef()
Python.builtins.setmainentry()
Python.builtins.loop()

# Run with
# python-execute-command \
# python://rpc.python.org compile.python.org \
# inputFile=file://<pwd>/test.py \
# outputFile=file://<pwd>/<filename>-<compileid>-<version>.pynat
# mode=debug
# python-execute-command \
# python://rpc.python.org run.python.org \
# target=file://<pwd>/<filename>-<compileid>-<version>.pynat \
# stdinFile=file://<pwd>/test.stdin \
# stdoutFile=file://<pwd>/test.stdout \
# stderrFile=file://<pwd>/test.stderr \
# mode=debug
# policy.enableNetworking=false
# policy.enableFileSystemAccess=true


# Install packages from "PyPI"
# python-manager 