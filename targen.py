import io
import sys
import tarfile
from shutil import copyfileobj

import faker

fa = faker.Faker()


def cpath_provider():
    return fa.file_path(
        depth=fa.random_int(min=1, max=5), file_system_rule="linux", absolute=False
    )


def fake_prod_dump():
    return f"root/depository/repository/{fa.file_path(absolute=False)}/+{fa.hexify('^' * 32)}/tree/{fa.file_path(absolute=False)}"


path_provider = fake_prod_dump
b = io.BytesIO()
with tarfile.open(fileobj=b, mode="w") as t:
    for _ in range(1000):
        p = path_provider()
        blob = fa.binary(fa.random_int(min=1, max=1024 * 1024))
        i = tarfile.TarInfo(p)
        i.size = len(blob)
        t.addfile(i, io.BytesIO(blob))
        print(f"Adding {p}", file=sys.stderr)
b.seek(0)
copyfileobj(b, sys.stdout.buffer)
