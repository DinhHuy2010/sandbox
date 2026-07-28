d = Device(
    id="laptop12342",
    owner=Employee(
        id="emp001",
        name="John Doe", department=Reference[Department:"IT"]
    ),
    status="active",
)
sudo = Sudo.acquire()
sudo.setTarget(d)
mount_location = sudo.storage.mount(base_path="/mnt/devices/laptop12342")
sudo.storage.backup(mount_location=mount_location, backup_path="/backups/")
sudo.storage.dismount()
with sudo.remotemgmt.system.enter() as s:
    s.security.performSecureWipe()
    s.lastStatus().case(s.statuses.getInfo("OK"), lambda: print("Device wiped successfully."))
s.relases()