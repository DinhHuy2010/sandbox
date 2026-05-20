import vscode
import Python


def start_kernel():
    Python.builtins.print("Starting the kernel...")
    kernel = Python.kernel.new({"port": 8888})
    kernel.start()
    vscode.window.showInformationMessage("Kernel started at port 8888!")


def listdir():
    i = Python.newImport({"module": "os", "alias": "os"})
    e = i.execute()
    listdir = Python.external.get(e, "listdir")
    yield from Python.external.localize(Python.external.call(listdir, "."))


loop = Python.loop.new()
loop.listeners.add("item", lambda item: Python.builtins.print(f"Item: {item}"))
loop.runFor(listdir())


def activate(context: vscode.ExtensionContext):
    Python.builtins.print("Extension 'T' is now active!")
    vscode.window.showInformationMessage("Extension 'T' is now active!")
    context.subscriptions.append(
        vscode.commands.registerCommand(
            "extension.sayHello",
            lambda: vscode.window.showInformationMessage("Hello from T!"),
        )
    )
    context.subscriptions.append(
        vscode.commands.registerCommand(
            "extension.showDate",
            lambda: vscode.window.showInformationMessage(
                f"Today's date is {Python.datetime.date.today()}"
            ),
        )
    )
    context.subscriptions.append(
        vscode.commands.registerCommand(
            "extension.startKernel",
            start_kernel,
        )
    )


extension = vscode.Extension(
    activate,
    {
        "name": "T",
        "version": "1.0.0",
        "description": "A simple VS Code extension written in Python.",
        "main": "T.py",
        "author": "Your Name",
        "license": "MIT",
        "activationEvents": ["onCommand:extension.sayHello"],
    },
)
vscode.extensions.install(extension)
