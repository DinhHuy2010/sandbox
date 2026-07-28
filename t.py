from queue import Queue
import threading


class StorageInterface:
    def createEntity(self, entity_type, path, data):
        pass

    def readEntity(self, path):
        pass

    def updateEntity(self, path, data, entity_type=None):
        pass

    def deleteEntity(self, path):
        pass


class Service:
    def __init__(self, kernel):
        self.data = {}
        self.kernel = kernel

    def startService(self):
        pass

    def suspendService(self):
        pass

    def shutdownService(self):
        pass

    def mainHandler(self, request):
        pass

    def getDependencies(self):
        return []


class FileSystemService(Service):
    def getStorageInterface(self):
        try:
            return self.data["storage_interface"]
        except KeyError:
            raise Exception("Storage interface not set.")

    def startService(self):
        print("FileSystemService started.")

    def suspendService(self):
        print("FileSystemService suspended.")

    def shutdownService(self):
        print("FileSystemService shut down.")

    def mainHandler(self, request):
        # Handle the request and perform file system operations
        match request["command"]:
            case "setStorageInterface":
                self.data["storage_interface"] = request["storageInterface"]
            case "createEntity":
                storage_interface = self.getStorageInterface()
                storage_interface.createEntity(
                    request["entityType"], request["path"], request["data"]
                )
            case "readEntity":
                storage_interface = self.getStorageInterface()
                return storage_interface.readEntity(request["path"])
            case "updateEntity":
                storage_interface = self.getStorageInterface()
                storage_interface.updateEntity(
                    request["path"], request["data"], request.get("entityType")
                )
            case "deleteEntity":
                storage_interface = self.getStorageInterface()
                storage_interface.deleteEntity(request["path"])


class Kernel:
    def __init__(self):
        self.services = {}
        self.queue = Queue()

    def log(self, message, component="kernel"):
        print(f"[{component}]: {message}")

    def registerService(self, service_name, service):
        self.services[service_name] = {"service": service, "status": "stopped"}

    def startService(self, service_name):
        if service_name in self.services:
            service = self.services[service_name]["service"]
            for dependency in self.resolveServiceDependencies(service):
                self.startService(dependency)
            service.startService()
            self.services[service_name]["status"] = "running"
        else:
            self.log(f"Service {service_name} not found.", component="services")

    def suspendService(self, service_name):
        if service_name in self.services:
            service = self.services[service_name]["service"]
            service.suspendService()
            self.services[service_name]["status"] = "suspended"
        else:
            self.log(f"Service {service_name} not found.", component="services")

    def shutdownService(self, service_name):
        if service_name in self.services:
            service = self.services[service_name]["service"]
            service.shutdownService()
            self.services[service_name]["status"] = "stopped"
        else:
            self.log(f"Service {service_name} not found.", component="services")

    def handleRequest(self, service_name, request):
        if service_name in self.services:
            service = self.services[service_name]["service"]
            return service.mainHandler(request)
        else:
            self.log(f"Service {service_name} not found.", component="services")
            return None

    def getServiceStatus(self, service_name):
        if service_name in self.services:
            return self.services[service_name]["status"]
        else:
            self.log(f"Service {service_name} not found.", component="services")
            return None

    def resolveServiceDependencies(self, service):
        dependencies = service.getDependencies()
        resolved_dependencies = []
        for dependency in dependencies:
            if dependency in self.services:
                resolved_dependencies.append(dependency)
            else:
                self.log(f"Dependency {dependency} not found.", component="services")
        return resolved_dependencies

    def init(self, services, target):
        for service_name, service_class in services.items():
            service = service_class(self)
            self.registerService(service_name, service)
        self.startService(target)

    def enterLoop(self):
        while True:
            # In a real implementation, this would handle incoming requests
            # For demonstration, we'll just break the loop
            payload = self.queue.get()
            if payload is None:
                break
            payload_target = payload.get("target")
            payload_from = payload.get("sender")
            payload = payload.get("data")
            if payload_target in self.services:
                response = self.handleRequest(payload_target, payload)
                self.handleRequest(payload_from, {"serviceResponse": response})
            else:
                self.log(f"Service {payload_target} not found.", component="services")
            self.queue.task_done()

    def sendRequest(self, target_service, request, sender_service):
        self.queue.put(
            {"target": target_service, "sender": sender_service, "data": request}
        )

    def shutdown(self):
        for service_name in list(self.services.keys()):
            self.shutdownService(service_name)
        self.log("Kernel shutdown complete.")


class MainInterface(Service):
    def startService(self):
        print("MainInterface started.")

    def suspendService(self):
        print("MainInterface suspended.")

    def shutdownService(self):
        print("MainInterface shut down.")

    def mainHandler(self, request):
        # Handle the request and perform main interface operations
        match request["command"]:
            case "sendRequest":
                target_service = request["targetService"]
                request_data = request["requestData"]
                sender_service = request["senderService"]
                self.kernel.sendRequest(target_service, request_data, sender_service)
            case "getServiceStatus":
                service_name = request["serviceName"]
                return self.kernel.getServiceStatus(service_name)

    def getDependencies(self):
        return [FileSystemService]


class InMemStorageInterface(StorageInterface):
    def __init__(self):
        self.storage = {}

    def createEntity(self, entity_type, path, data):
        if path in self.storage:
            raise Exception(f"Entity at path {path} already exists.")
        self.storage[path] = {"type": entity_type, "data": data}

    def readEntity(self, path):
        if path not in self.storage:
            raise Exception(f"Entity at path {path} does not exist.")
        return self.storage[path]

    def updateEntity(self, path, data, entity_type=None):
        if path not in self.storage:
            raise Exception(f"Entity at path {path} does not exist.")
        if entity_type is not None:
            self.storage[path]["type"] = entity_type
        self.storage[path]["data"] = data

    def deleteEntity(self, path):
        if path not in self.storage:
            raise Exception(f"Entity at path {path} does not exist.")
        del self.storage[path]


kernel = Kernel()
kernel.init(
    {"filesystem": FileSystemService, "main_interface": MainInterface}, "main_interface"
)
thr = threading.Thread(target=kernel.enterLoop, daemon=True)
thr.start()
kernel.sendRequest(
    "filesystem",
    {"command": "setStorageInterface", "storageInterface": InMemStorageInterface()},
    "main_interface",
)
