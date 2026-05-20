from dataclasses import dataclass, field
from typing import Generator, Iterable

from dulwich import pack
from dulwich.object_format import SHA1, SHA256, ObjectFormat
import httpx

from breader import BReader


@dataclass
class PktStream:
    _buf: bytearray = field(default_factory=bytearray, init=False, repr=False)

    def feed(self, data: bytes) -> Generator[bytearray, None, None]:
        self._buf.extend(data)

        while True:
            if len(self._buf) < 4:
                return

            size = int(self._buf[:4], 16)

            if size == 0:
                # flush packet
                del self._buf[:4]
                continue

            if len(self._buf) < size:
                return

            payload = self._buf[4:size]
            del self._buf[:size]

            yield payload


def process_pkt_stream(byte_iter: Iterable[bytes]):
    pkt = PktStream()

    for chunk in byte_iter:
        for payload in pkt.feed(chunk):
            if not payload:
                continue

            # skip NAK
            if payload.startswith(b"NAK"):
                continue

            band = payload[0]
            data = payload[1:]

            if band == 1:
                # pack data
                yield data

            elif band == 2:
                # progress
                print(data.decode(errors="ignore"), end="")

            elif band == 3:
                raise RuntimeError(data.decode(errors="ignore"))

            else:
                raise ValueError(f"unknown band {band}")


def stream_git_response(bytes_iter: Iterable[bytes]):
    first = True
    buffer = bytearray()

    for chunk in bytes_iter:
        buffer.extend(chunk)

        if first:
            first = False

            # Case 1: raw pack
            if buffer.startswith(b"PACK"):
                yield buffer
                buffer.clear()
                for c in bytes_iter:
                    yield c
                return

            # Case 2: NAK + raw pack
            if buffer.startswith(b"0008NAK\nPACK"):
                yield buffer[8:]
                buffer.clear()
                for c in bytes_iter:
                    yield c
                return

        # otherwise: side-band → fall back
        process_pkt_stream([bytes(buffer)])
        buffer.clear()


PKT_FLUSH = b"0000"


def pkt_line(text: str) -> bytes:
    payload = text.encode("utf-8")
    total = len(payload) + 4
    return f"{total:04x}".encode("ascii") + payload


@dataclass(frozen=True)
class Refs:
    refs: dict[str, str]
    capibilities: dict[str, str | bool]

    def find_head(self) -> str:
        try:
            return self.refs["HEAD"]
        except KeyError:
            symref = self.capibilities.get("symref", "")
            _, branch = symref.split(":", 1)
            try:
                return self.refs[branch.strip()]
            except KeyError:
                raise RuntimeError("HEAD not found") from None


client = httpx.Client(timeout=60)


def discover_refs(clone_url: str) -> Refs:
    with client.stream(
        "GET", clone_url + "/info/refs?service=git-upload-pack"
    ) as response:
        stream = PktStream()
        caps: dict[str, str | bool] = {}
        refs: dict[str, str] = {}

        for chunk in response.iter_bytes():
            for payload in stream.feed(chunk):
                if payload.startswith(b"#"):
                    continue
                payload = bytes(payload)
                oid, ref = payload.split(b" ", 1)
                ref, *fcaps = ref.split(b"\0")
                refs[ref.decode().strip()] = oid.decode()
                if fcaps:
                    # caps.extend(fcaps[0].split(b" "))
                    for cap in fcaps[0].split(b" "):
                        if b"=" in cap:
                            k, v = cap.split(b"=", 1)
                            caps[k.decode().strip()] = v.decode().strip()
                        else:
                            caps[cap.decode().strip()] = True
        return Refs(refs, caps)


def perform_negotiation(clone_url: str, oid: str, capibilities: dict[str, str | bool]):
    caps = []
    for cap, val in capibilities.items():
        if val is True:
            caps.append(cap)
        else:
            caps.append(f"{cap}={val}")
    payload = (
        pkt_line(f"want {oid}\0{' '.join(caps)}\n")
        + PKT_FLUSH
        + pkt_line("done\n")
        + PKT_FLUSH
    )
    headers = {
        "Content-Type": "application/x-git-upload-pack-request",
        "Accept": "application/x-git-upload-pack-result",
    }
    with client.stream(
        "POST", clone_url + "/git-upload-pack", content=payload, headers=headers
    ) as response:
        for chunk in stream_git_response(response.iter_bytes()):
            yield chunk


def get_object_format(format: str) -> ObjectFormat:
    if format == "sha1":
        return SHA1
    elif format == "sha256":
        return SHA256
    else:
        raise ValueError(f"unknown object format {format}")


# url = "https://github.com/nedbat/byterun.git"
url = "https://github.com/python/cpython.git"
# out = discover_refs(url)
out = Refs({}, {"object-format": "sha1"})
# oid = out.find_head()
oid = "ad7d3616c6cc21c5ec032a726e4c5e819628aa6e"
print(f"HEAD: {oid}")
caps = {"side-band-64k": True, "ofs-delta": True, "agent": "git/2.43.0"}
f = perform_negotiation(url, oid, caps)
object_format = get_object_format(out.capibilities["object-format"])
hf = BReader(f)
with pack.PackData.from_file(hf, object_format) as pdata:
    for obj in pdata.iter_unpacked():
        print(obj)
