from abc import ABC, abstractmethod


class BaseComponent(ABC):
    kernel: "Kernel"

    @abstractmethod
    def getCodename(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def run(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def setKernel(self, kernel):
        self.kernel = kernel


class BaseApplication(BaseComponent):
    def registerComponent(self, component):
        pass

    @abstractmethod
    def run(self):
        raise NotImplementedError("Subclasses should implement this method.")


class Shell(BaseApplication):
    def __init__(self):
        super().__init__()
        self.commands = {}

    def getCodename(self):
        return "shell"

    def registerComponent(self, component):
        print(f"Registering component: {component}")
        self.commands[component.getCodename()] = component

    def run(self):
        print("Running the shell application.")
        while True:
            command = input("Enter command (or 'exit' to quit): ")
            if command == "exit":
                print("Exiting the shell application.")
                break
            elif command in self.commands:
                self.commands[command].setKernel(self.kernel)
                self.commands[command].run()
            else:
                print(f"Unknown command: {command}")


class Kernel:
    def __init__(self, target):
        self.memory = {}
        self.target = target

    def run(self):
        print(f"Kernel is running with target: {self.target}")
        self.target.setKernel(self)
        self.target.run()


class Add(BaseComponent):
    def getCodename(self):
        return "add"

    def run(self):
        try:
            a = float(input("Enter first number: "))
            b = float(input("Enter second number: "))
            result = a + b
            print(f"The result of adding {a} and {b} is: {result}")
        except ValueError:
            print("Invalid input. Please enter numeric values.")


s = Shell()
s.registerComponent(s)
s.registerComponent(Add())
k = Kernel(s)
k.run()
