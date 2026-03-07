import os
from enum import IntFlag


class OpenFlags(IntFlag):
    O_APPEND = os.O_APPEND
    O_ASYNC = os.O_ASYNC
    O_CLOEXEC = os.O_CLOEXEC
    O_CREAT = os.O_CREAT
    O_DIRECT = os.O_DIRECT
    O_DIRECTORY = os.O_DIRECTORY
    O_DSYNC = os.O_DSYNC
    O_EXCL = os.O_EXCL
    O_FSYNC = os.O_FSYNC
    O_LARGEFILE = os.O_LARGEFILE
    O_NDELAY = os.O_NDELAY
    O_NOATIME = os.O_NOATIME
    O_NOCTTY = os.O_NOCTTY
    O_NOFOLLOW = os.O_NOFOLLOW
    O_NONBLOCK = os.O_NONBLOCK
    O_PATH = os.O_PATH
    O_RSYNC = os.O_RSYNC
    O_SYNC = os.O_SYNC
    O_TMPFILE = os.O_TMPFILE
    O_TRUNC = os.O_TRUNC


class AccessMode(IntFlag):
    O_RDONLY = os.O_RDONLY
    O_WRONLY = os.O_WRONLY
    O_RDWR = os.O_RDWR


O_ACCMODE = os.O_ACCMODE


def parse_open_flags(flags: int) -> tuple[OpenFlags, AccessMode]:
    access_mode = flags & O_ACCMODE
    access = AccessMode(access_mode)
    other_flags = OpenFlags(flags & ~O_ACCMODE)
    return other_flags, access
