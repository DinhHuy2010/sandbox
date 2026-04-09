from . import DistlibException as DistlibException
from .compat import (
    HTTPError as HTTPError,
    HTTPRedirectHandler as BaseRedirectHandler,
    Request as Request,
    URLError as URLError,
    build_opener as build_opener,
    pathname2url as pathname2url,
    queue as queue,
    quote as quote,
    text_type as text_type,
    unescape as unescape,
    url2pathname as url2pathname,
    urljoin as urljoin,
    urlparse as urlparse,
    urlunparse as urlunparse,
)
from .database import (
    Distribution as Distribution,
    DistributionPath as DistributionPath,
    make_dist as make_dist,
)
from .metadata import Metadata as Metadata, MetadataInvalidError as MetadataInvalidError
from .util import (
    ServerProxy as ServerProxy,
    cached_property as cached_property,
    ensure_slash as ensure_slash,
    get_project_data as get_project_data,
    normalize_name as normalize_name,
    parse_name_and_version as parse_name_and_version,
    parse_requirement as parse_requirement,
    split_filename as split_filename,
)
from .version import (
    UnsupportedVersionError as UnsupportedVersionError,
    get_scheme as get_scheme,
)
from .wheel import Wheel as Wheel, is_compatible as is_compatible
from _typeshed import Incomplete

logger: Incomplete
HASHER_HASH: Incomplete
CHARSET: Incomplete
HTML_CONTENT_TYPE: Incomplete
DEFAULT_INDEX: str

def get_all_distribution_names(url=None): ...

class RedirectHandler(BaseRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers): ...
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302

class Locator:
    source_extensions: Incomplete
    binary_extensions: Incomplete
    excluded_extensions: Incomplete
    wheel_tags: Incomplete
    downloadable_extensions: Incomplete
    scheme: Incomplete
    opener: Incomplete
    matcher: Incomplete
    errors: Incomplete
    def __init__(self, scheme: str = "default") -> None: ...
    def get_errors(self): ...
    def clear_errors(self) -> None: ...
    def clear_cache(self) -> None: ...
    def get_distribution_names(self) -> None: ...
    def get_project(self, name): ...
    def score_url(self, url): ...
    def prefer_url(self, url1, url2): ...
    def split_filename(self, filename, project_name): ...
    def convert_url_to_download_info(self, url, project_name): ...
    def locate(self, requirement, prereleases: bool = False): ...

class PyPIRPCLocator(Locator):
    base_url: Incomplete
    client: Incomplete
    def __init__(self, url, **kwargs) -> None: ...
    def get_distribution_names(self): ...

class PyPIJSONLocator(Locator):
    base_url: Incomplete
    def __init__(self, url, **kwargs) -> None: ...
    def get_distribution_names(self) -> None: ...

class Page:
    data: Incomplete
    base_url: Incomplete
    def __init__(self, data, url) -> None: ...
    @cached_property
    def links(self): ...

class SimpleScrapingLocator(Locator):
    decoders: Incomplete
    base_url: Incomplete
    timeout: Incomplete
    skip_externals: bool
    num_workers: Incomplete
    platform_check: bool
    def __init__(self, url, timeout=None, num_workers: int = 10, **kwargs) -> None: ...
    platform_dependent: Incomplete
    def get_page(self, url): ...
    def get_distribution_names(self): ...

class DirectoryLocator(Locator):
    recursive: Incomplete
    base_dir: Incomplete
    def __init__(self, path, **kwargs) -> None: ...
    def should_include(self, filename, parent): ...
    def get_distribution_names(self): ...

class JSONLocator(Locator):
    def get_distribution_names(self) -> None: ...

class DistPathLocator(Locator):
    distpath: Incomplete
    def __init__(self, distpath, **kwargs) -> None: ...

class AggregatingLocator(Locator):
    merge: Incomplete
    locators: Incomplete
    def __init__(self, *locators, **kwargs) -> None: ...
    def clear_cache(self) -> None: ...
    scheme: Incomplete
    def get_distribution_names(self): ...

default_locator: Incomplete
locate: Incomplete

class DependencyFinder:
    locator: Incomplete
    scheme: Incomplete
    def __init__(self, locator=None) -> None: ...
    def add_distribution(self, dist) -> None: ...
    def remove_distribution(self, dist) -> None: ...
    def get_matcher(self, reqt): ...
    def find_providers(self, reqt): ...
    def try_to_replace(self, provider, other, problems): ...
    provided: Incomplete
    dists: Incomplete
    dists_by_name: Incomplete
    reqts: Incomplete
    def find(self, requirement, meta_extras=None, prereleases: bool = False): ...
