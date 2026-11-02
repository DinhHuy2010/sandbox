# def build(cpu,motherboard,ram,storage,gpu,cooler,case):
#     motherboard.socket.attach(cpu)
#     motherboard.socket.attach(cooler)
#     with motherboard.memory() as memory:
#         for i, r in enumerate(ram):
#             memory.slots[i].attach(r)
#     with motherboard.pcie() as pcie:
#         pcie.slots[0].attach(gpu)
#     with motherboard.storage() as storage_slots:
#         for i, s in enumerate(storage):
#             storage_slots.slots[i].attach(s)
#     case.attach(motherboard)
#     builder = AcquireBuilder()
#     builder.prepare()
#     builder.finalize(case)
#     CloseBuilder(builder)
#     return GetPC(builder)

Lifecycle = Bootstrap()
Printer = Lifecycle.Acquire("builtins.python.org#print")


@Lifecycle.Register(
    "localhost#Main", PostCall=CreatePostCall(Lifecycle.Release, Printer)
)
def Main():
    P = CreateObject(Printer)
    P.PrintLine("Hello, World!")
