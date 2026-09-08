from uuid import UUID, uuid4

from attrs import define, field


@define
class Node:
    uuid: UUID = field(factory=uuid4, kw_only=True)


@define
class Identity(Node):
    name: str = ""
    description: str = ""


UNKNOWN_OWNER = Identity(
    uuid=UUID("3b983cb8-5573-4511-ad8d-a4764b80302e"),
    name="<unidentifiable>",
    description="<unidentifiable>",
)


@define
class Server(Node):
    owner: Identity
    # all values are in bytes

    cores: int
    ram: list[int] = field(factory=list)
    vram: int = 0
    storage: list[int] = field(factory=list)

    @property
    def total_ram(self) -> int:
        return sum(self.ram)

    @property
    def total_storage(self) -> int:
        return sum(self.storage)


@define
class ServerCluster(Node):
    owner: Identity
    servers: dict[UUID, Server] = field(factory=dict)

    def add_server(self, server: Server) -> None:
        self.servers[server.uuid] = server

    @property
    def total_servers(self) -> int:
        return len(self.servers)

    @property
    def total_cores(self) -> int:
        return sum(server.cores for server in self.servers.values())

    @property
    def total_ram(self) -> int:
        return sum(server.total_ram for server in self.servers.values())

    @property
    def total_vram(self) -> int:
        return sum(server.vram for server in self.servers.values())

    @property
    def total_storage(self) -> int:
        return sum(server.total_storage for server in self.servers.values())


GB = 1024 * 1024 * 1024


cluster = ServerCluster(owner=UNKNOWN_OWNER)

cluster.add_server(
    Server(
        owner=UNKNOWN_OWNER,
        cores=8,
        ram=[16 * GB, 16 * GB],
        vram=8 * GB,
        storage=[256 * GB, 512 * GB],
    )
)

cluster.add_server(
    Server(
        owner=UNKNOWN_OWNER,
        cores=16,
        ram=[32 * GB, 32 * GB],
        vram=16 * GB,
        storage=[512 * GB, 1024 * GB],
    )
)

cluster.add_server(
    Server(
        owner=UNKNOWN_OWNER,
        cores=4,
        ram=[8 * GB, 8 * GB],
        vram=4 * GB,
        storage=[128 * GB, 256 * GB],
    )
)

print(f"Servers: {cluster.total_servers}")
print(f"Cores: {cluster.total_cores}")
print(f"RAM: {cluster.total_ram / GB}")
print(f"VRAM: {cluster.total_vram / GB}")
print(f"Storage: {cluster.total_storage / GB}")
