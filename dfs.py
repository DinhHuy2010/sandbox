# from pathlib import PurePosixPath

import zoneinfo

TZS = zoneinfo.available_timezones()


def tz_object_bases(base) -> list[str]:
    paths = []
    paths.append("offset")
    paths.append("name")
    paths.append("iana-id")
    paths.append("abbreviations")
    paths.append("iana-same-as")
    paths.append("dst-included")
    paths.extend(dt_object_bases("time"))
    return [f"{base}/{i}" for i in paths]


def dt_object_bases(base, _root=True) -> list[str]:
    paths = []
    paths.extend(["date", "month", "year", "hour", "minute", "second"])
    paths.extend(
        [
            f"formats/{i}"
            for i in ["iso8601", "rfc3339", "rfc2822", "rfc822", "rfc850", "asctime"]
        ]
    )
    paths.append("current-timezone")
    paths.append("dst-offset")
    if _root:
        paths.extend(dt_object_bases("in-timezones/<iana-timezone>", _root=False))
    return [f"{base}/{i}" for i in paths]


UNIX_BASE_PATH = "/by-unixtime/<unixtime>"
DATE_ISO_BASE_PATH = "/by-iso8601-date/<iso-date>"
TIMEZONE_BASE_PATH = "/timezones/by-iana/<iana-timezone>"
TIMEZONE_BASE_PATH_BY_OFFSET = "/timezones/by-offset/<utc-offset>"
paths = dt_object_bases(UNIX_BASE_PATH)
paths += dt_object_bases(DATE_ISO_BASE_PATH)
paths += tz_object_bases(TIMEZONE_BASE_PATH)
paths += tz_object_bases(TIMEZONE_BASE_PATH_BY_OFFSET)
print("\n".join(f"<mountpoint>{p}" for p in paths))

# pwd = PurePosixPath("/")
# ROOT = PurePosixPath("/")


# def chdir(path: str):
#     global pwd
#     new_path = PurePosixPath(path)
#     if not new_path.is_absolute():
#         new_path = pwd / new_path
#     pwd = new_path.resolve()


# def getcwd() -> str:
#     return str(pwd)


# def resolve_path(path: str | PurePosixPath) -> PurePosixPath:
#     if isinstance(path, PurePosixPath):
#         return path
#     if path == "":
#         return pwd
#     p = PurePosixPath(path)
#     if not p.is_absolute():
#         p = pwd / p
#     return p


# def is_root(path: str | PurePosixPath) -> bool:
#     return resolve_path(path) == ROOT


# def ls(path: str | PurePosixPath | None = None) -> list[str]:
#     if path is None:
#         new_path = pwd
#     else:
#         new_path = resolve_path(path)
#     if is_root(new_path):
#         return ["by-unixtime"]
#     if is_root(new_path.parent) and new_path.name == "by-unixtime":
#         return []
#     elif len(new_path.parts) > 2 and new_path.parts[1] == "by-unixtime":
#         return ["isodate", "date", "month", "year", "hour", "minute", "second", "in-timezones"]
#     return []

# print(ls("/by-unixtime/111111111"))
