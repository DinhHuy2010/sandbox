import asyncio
from dataclasses import dataclass
from pathlib import Path

from packaging.utils import parse_wheel_filename
from simple_repository.components.http_cached import CachedHttpRepository
from simple_repository import SimpleRepository
from simple_repository.model import HttpResource


@dataclass
class Context:
    repository: SimpleRepository


def create_context() -> Context:
    repository = CachedHttpRepository(
        "https://pypi.org/simple/", Path(".cache/simple-repository")
    )
    return Context(repository=repository)


async def fetch_wheel_file(context: Context, filename: str) -> HttpResource:
    try:
        name, *_ = parse_wheel_filename(filename)  # Validate the filename
    except Exception as e:
        raise ValueError(f"Invalid wheel filename: {filename}") from e
    resource: HttpResource = await context.repository.get_resource(name, filename)
    return resource


if __name__ == "__main__":
    from app._rangeresp import HTTPFile, NonSeekableHTTPFile
    from zipfile import ZipFile
    from tarfile import TarFile

    context = create_context()
    # fn = "pandas-3.0.2-cp314-cp314t-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl"
    # resource = asyncio.run(fetch_wheel_file(context, fn))
    # print(f"Fetched resource: {resource}")
    # with HTTPFile(resource.url) as f:
    #     print(f"File size: {f._size} bytes")
    #     with ZipFile(f) as zip_file:
    #         print("Contents of the wheel file:")
    #         zip_file.printdir()
    fn = "pandas-3.0.2.tar.gz"
    resource = asyncio.run(context.repository.get_resource("pandas", fn))
    with NonSeekableHTTPFile(resource.url) as f:
        with TarFile.open(fileobj=f, mode="r|gz") as tar_file:
            print("Contents of the tar.gz file:")
            for member in tar_file:
                print(member.name)
                print(f"  Size: {member.size} bytes")
                print(tar_file.extractfile(member).read(100))
