from . import DistlibException as DistlibException, __version__ as __version__
from .compat import (
    ZipFile as ZipFile,
    filter as filter,
    fsdecode as fsdecode,
    sysconfig as sysconfig,
    text_type as text_type,
)
from .database import InstalledDistribution as InstalledDistribution
from .metadata import (
    LEGACY_METADATA_FILENAME as LEGACY_METADATA_FILENAME,
    Metadata as Metadata,
    WHEEL_METADATA_FILENAME as WHEEL_METADATA_FILENAME,
)
from .util import (
    CSVReader as CSVReader,
    CSVWriter as CSVWriter,
    Cache as Cache,
    FileOperator as FileOperator,
    cached_property as cached_property,
    convert_path as convert_path,
    get_cache_base as get_cache_base,
    get_platform as get_platform,
    read_exports as read_exports,
    tempdir as tempdir,
)
from .version import (
    NormalizedVersion as NormalizedVersion,
    UnsupportedVersionError as UnsupportedVersionError,
)
from _typeshed import Incomplete
from collections.abc import Generator

logger: Incomplete
cache: Incomplete
IMP_PREFIX: str
VER_SUFFIX: Incomplete
PYVER: Incomplete
IMPVER: Incomplete
ARCH: Incomplete
ABI: Incomplete
FILENAME_RE: Incomplete
NAME_VERSION_RE: Incomplete
SHEBANG_RE: Incomplete
SHEBANG_DETAIL_RE: Incomplete
SHEBANG_PYTHON: bytes
SHEBANG_PYTHONW: bytes
to_posix: Incomplete
imp: Incomplete

class Mounter:
    impure_wheels: Incomplete
    libs: Incomplete
    def __init__(self) -> None: ...
    def add(self, pathname, extensions) -> None: ...
    def remove(self, pathname) -> None: ...
    def find_module(self, fullname, path=None): ...
    def load_module(self, fullname): ...

class Wheel:
    wheel_version: Incomplete
    hash_kind: str
    sign: Incomplete
    should_verify: Incomplete
    buildver: str
    pyver: Incomplete
    abi: Incomplete
    arch: Incomplete
    dirname: Incomplete
    name: str
    version: str
    def __init__(
        self, filename=None, sign: bool = False, verify: bool = False
    ) -> None: ...
    @property
    def filename(self): ...
    @property
    def exists(self): ...
    @property
    def tags(self) -> Generator[Incomplete]: ...
    @cached_property
    def metadata(self): ...
    def get_wheel_metadata(self, zf): ...
    @cached_property
    def info(self): ...
    def process_shebang(self, data): ...
    def get_hash(self, data, hash_kind=None): ...
    def write_record(self, records, record_path, archive_record_path) -> None: ...
    def write_records(self, info, libdir, archive_paths) -> None: ...
    def build_zip(self, pathname, archive_paths) -> None: ...
    def build(self, paths, tags=None, wheel_version=None): ...
    def skip_entry(self, arcname): ...
    def install(self, paths, maker, **kwargs): ...
    def is_compatible(self): ...
    def is_mountable(self): ...
    def mount(self, append: bool = False) -> None: ...
    def unmount(self) -> None: ...
    def verify(self) -> None: ...
    def update(self, modifier, dest_dir=None, **kwargs): ...

def compatible_tags(): ...

COMPATIBLE_TAGS: Incomplete

def is_compatible(wheel, tags=None): ...
