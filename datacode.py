# import nothing

# ai = nothing.AI
# ai.init()
# ai.performAuthentication.credentials = ai.performAuthentication.binds.local.filesystem(
#     ai.performAuthentication.binds.local.filesystem.createFileSystemGateway(
#         rootMount="."
#     ).resolvePath("/credentials.json"),
# )
# ai.performAuthentication().whenOK(lambda: print("Authenticated!"))


# @ai.agents.createTool()
# def my_tool(context: ai.agents.Agent.getClass("context")):
#     # .getField_<fieldname>
#     return context.createResponse(
#         f"Hello from my_tool!, it is number {context.getField_number()}"
#     )


# _mt_toolkit = ai.agents.getTool(my_tool)


# @_mt_toolkit.whenRegisterOnChatbot()
# def register_tool_on_chatbot(chatbot: ai.agents.Agent.getClass("chatbot")):
#     print(f"Registering tool {my_tool.__name__} on chatbot {chatbot.getField_name()}")


# ai.currentUser().createChatbot(
#     "[CurrentDomain]::myChatbot",
#     model=ai.currentUser().models.provider["openai"].model["gpt-4"],
# ).whenOK(
#     lambda: ai.agents.registerTool(my_tool).whenOK(
#         lambda: print(f"Tool {my_tool.__name__} registered successfully!")
#     )
# )
# ai.currentUser().getCurrentDomain().getObject("::myChatbot").whenOK(
#     lambda chatbot: (
#         print(f"Chatbot {chatbot.getField_name()} is ready to use!"),
#         chatbot.startChatSession().whenOK(
#             lambda session: (
#                 print(f"Chat session started with ID: {session.getField_sessionId()}"),
#                 session.sendMessage("Hello, chatbot!").whenOK(
#                     lambda response: print(
#                         f"Chatbot response: {response.getField_message()}"
#                     )
#                 ),
#             )
#         ),
#     )
# )

from abc import ABC, abstractmethod

from attrs import define, field


@define
class Node(ABC):
    @abstractmethod
    def get_guid(self) -> str:
        pass


@define
class Domain(Node):
    name: str
    nodes: list[Node] = field(factory=list)

    def get_guid(self) -> str:
        return f"[AbsoluteRoot.Foundation.Core.Domains]::{self.name}"

    def get_domain_str(self):
        return f"domains:{self.name}"

    def remove_node(self, node: Node):
        if node in self.nodes:
            self.nodes.remove(node)
            return True
        return False


class OwnableNode(Node):
    pass


@define
class User(OwnableNode):
    name: str
    domain: Domain

    def get_guid(self) -> str:
        return f"[User@{self.domain.get_domain_str()}]::{self.name}"


@define
class Resource(Node):
    name: str
    domain: Domain
    owner: OwnableNode

    def get_guid(self) -> str:
        return f"[Resource@{self.domain.get_domain_str()}]::{self.name}"


@define
class Machine(Resource, OwnableNode):
    cpu: "CPU"
    gpu: "GPU"
    ram: list["RAM"]
    storage: list["StorageUnit"]

    def get_guid(self) -> str:
        return f"[Resource.Machine@{self.domain.get_domain_str()}]::{self.name}"


@define
class MachineUnit(Resource):
    def get_guid(self) -> str:
        return f"[Resource.Machine.Unit@{self.domain.get_domain_str()}]::{self.name}"


@define
class CPU(MachineUnit):
    cores: int

    def get_guid(self) -> str:
        return f"[Resource.Machine.CPU@{self.domain.get_domain_str()}]::{self.name}"


@define
class GPU(MachineUnit):
    vram_capacity: int  # in bytes

    def get_guid(self) -> str:
        return f"[Resource.Machine.GPU@{self.domain.get_domain_str()}]::{self.name}"


@define
class RAM(MachineUnit):
    capacity: int  # in bytes

    def get_guid(self) -> str:
        return f"[Resource.Machine.RAM@{self.domain.get_domain_str()}]::{self.name}"


@define
class StorageUnit(MachineUnit):
    raw_capacity: int  # in bytes

    def get_guid(self) -> str:
        return f"[Resource.Machine.StorageUnit@{self.domain.get_domain_str()}]::{self.name}"


@define
class PC(Machine):
    def get_guid(self) -> str:
        return f"[Resource.PC@{self.domain.get_domain_str()}]::{self.name}"


@define
class Laptop(PC):
    def get_guid(self) -> str:
        return f"[Resource.Laptop@{self.domain.get_domain_str()}]::{self.name}"


@define
class Server(PC):
    def get_guid(self) -> str:
        return f"[Resource.Server@{self.domain.get_domain_str()}]::{self.name}"


@define
class ClustersServer(Server):
    clusters: list[Server] = field(factory=list)

    def get_guid(self) -> str:
        return f"[Resource.ClustersServer@{self.domain.get_domain_str()}]::{self.name}"


@define
class CloudServer(Server):
    cloud_provider: str

    def get_guid(self) -> str:
        return f"[Resource.CloudServer@{self.domain.get_domain_str()}]::{self.name}"


@define
class VirtualMachine(Machine):
    hypervisor: str

    def get_guid(self) -> str:
        return f"[Resource.VirtualMachine@{self.domain.get_domain_str()}]::{self.name}"

@define
class Container(VirtualMachine):
    container_engine: str

    def get_guid(self) -> str:
        return f"[Resource.Container@{self.domain.get_domain_str()}]::{self.name}"

@define
class VirtualPrivateServer(VirtualMachine, Server):
    vps_provider: str

    def get_guid(self) -> str:
        return f"[Resource.VirtualPrivateServer@{self.domain.get_domain_str()}]::{self.name}"


# domain = Domain(name="internal.hellokitty.fiction")
# user = User(name="admin", domain=domain)
# domain.nodes.append(user)
# machine = Machine(name="server01", domain=domain, owner=user)
# domain.nodes.append(machine)
# # print(machine.get_guid())  # Output: [Machine@domains:internal.hellokitty.fiction]::server01
