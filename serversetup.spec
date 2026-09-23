# comment here

want $.storage.brands

version = 1.0
storage = [
    {
        typeid: "nvme5:pcie5:ssd",
        capacity: 8TiB,
        brand: $.storage.brands.samsung
    },
    {
        typeid: "nvme5:pcie5:ssd",
        capacity: 8TiB,
        brand: $.storage.brands.samsung
    },
    {
        typeid: "nvme5:pcie5:ssd",
        capacity: 8TiB,
        brand: $.storage.brands.samsung
    },
    {
        typeid: "nvme5:pcie5:ssd",
        capacity: 8TiB,
        brand: $.storage.brands.samsung
    },
    {
        typeid: "nvme5:pcie5:ssd",
        capacity: 8TiB,
        brand: $.storage.brands.samsung
    },
    {
        typeid: "nvme5:pcie5:ssd",
        capacity: 8TiB,
        brand: $.storage.brands.samsung
    },
    {
        typeid: "jbod",
        disks: $.dupe {quantity: 60, item: {
            typeid: "sata3:ssd",
            capacity: 36TiB,
            brand: $.storage.brands.seagate
        }}
    }
]
cpu = {
    cores: 128,
    threads: .cores * 3,
    clock_speed: 5.2GHz,
    cache: 256MiB,
    pcie_lanes: 32
}
gpu = $.dupe {quantity: 8, item: {
    typeid: "pcie-expansion:gpu",
    vram: 96GiB,
    brand: $.gpu.brands.nvidia
}}
memory = $.dupe {quantity: 32, item: {
    typeid: "ddr5:rdimm:ecc",
    capacity: 512GiB,
    speed: 4800MHz,
    brand: $.memory.brands.kingston
}}
software = {
    os: {
        family: "linux",
        flavor: "proxmox"
    },
    exposed_services: [
        {
            type: "smb",
            port: 445,
            name: "file-server"
        },
        {
            type: "s3:minio",
            port: 9000,
            name: "object-storage"
        }
    ]
}
