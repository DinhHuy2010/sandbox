from html import unescape
from html.parser import HTMLParser
from importlib.util import cache_from_source
from io import StringIO
from itertools import filterfalse
from logging.config import BaseConfigurator
from platform import python_implementation
from shutil import which
from tokenize import detect_encoding
from urllib.error import (
    ContentTooShortError,
    HTTPError,
)
from urllib.parse import (
    quote,
    unquote,
    urljoin,
    urlparse,
    urlsplit,
    urlunparse,
    urlunsplit,
)
from urllib.request import (
    HTTPBasicAuthHandler,
    HTTPHandler,
    HTTPPasswordMgr,
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    urlopen,
    urlretrieve,
)
from ssl import CertificateError
from types import SimpleNamespace as Container

from zipfile import ZipFile
from os import fsencode
from os import fsdecode
from collections import OrderedDict, ChainMap

__all__ = [
    "BaseConfigurator",
    "CertificateError",
    "ChainMap",
    "ContentTooShortError",
    "Container",
    "filterfalse",
    "HTTPBasicAuthHandler",
    "HTTPError",
    "HTTPHandler",
    "HTTPPasswordMgr",
    "HTTPRedirectHandler",
    "HTTPSHandler",
    "HTMLParser",
    "quote",
    "Request",
    "StringIO",
    "unescape",
    "unquote",
    "urljoin",
    "urlparse",
    "urlsplit",
    "urlunparse",
    "urlunsplit",
    "urlopen",
    "urlretrieve",
    "which",
    "ZipFile",
    "cache_from_source",
    "detect_encoding",
    "fsdecode",
    "fsencode",
    "OrderedDict",
    "python_implementation",
]
