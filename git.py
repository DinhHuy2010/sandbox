from __future__ import annotations

from io import BytesIO
import pathlib

import dulwich
from dulwich.object_format import SHA1
import dulwich.pack
import httpx


class PktStream:
    def __init__(self):
        self.buf = bytearray()

    def feed(self, data: bytes):
        self.buf.extend(data)

        while True:
            if len(self.buf) < 4:
                return

            size = int(self.buf[:4], 16)

            if size == 0:
                # flush packet
                del self.buf[:4]
                continue

            if len(self.buf) < size:
                return

            payload = self.buf[4:size]
            del self.buf[:size]

            yield payload


def process_pkt_stream(byte_iter, pack_writer):
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
                pack_writer.write(data)

            elif band == 2:
                # progress
                print(data.decode(errors="ignore"), end="")

            elif band == 3:
                raise RuntimeError(data.decode(errors="ignore"))

            else:
                raise ValueError(f"unknown band {band}")


def stream_git_response(bytes_iter, out_file):
    first = True
    buffer = bytearray()

    for chunk in bytes_iter:
        buffer.extend(chunk)

        if first:
            first = False

            # Case 1: raw pack
            if buffer.startswith(b"PACK"):
                out_file.write(buffer)
                buffer.clear()
                for c in bytes_iter:
                    out_file.write(c)
                return

            # Case 2: NAK + raw pack
            if buffer.startswith(b"0008NAK\nPACK"):
                out_file.write(buffer[8:])
                buffer.clear()
                for c in bytes_iter:
                    out_file.write(c)
                return

        # otherwise: side-band → fall back
        process_pkt_stream([bytes(buffer)], out_file)
        buffer.clear()


class MiniGitClone:
    def __init__(self, repo_url: str, dest: str, client: httpx.Client) -> None:
        self.repo_url = repo_url.rstrip("/")
        self.dest = pathlib.Path(dest)
        self.git_dir = self.dest / ".git"
        self.objects_dir = self.git_dir / "objects"
        self.refs_dir = self.git_dir / "refs"
        self.client = client

    def clone(self) -> None:
        self._init_dirs()
        refs = self._discover_refs()
        head_ref, head_oid = self._pick_head(refs)
        pack_data = self._fetch_pack(head_oid)
        self._store_pack_placeholder(pack_data)
        self._write_head(head_ref)
        print(f"Cloned HEAD {head_ref} -> {head_oid}")

    def _init_dirs(self) -> None:
        self.dest.mkdir(parents=True, exist_ok=True)
        (self.git_dir / "objects").mkdir(parents=True, exist_ok=True)
        (self.git_dir / "refs" / "heads").mkdir(parents=True, exist_ok=True)
        (self.git_dir / "refs" / "remotes" / "origin").mkdir(
            parents=True, exist_ok=True
        )

        (self.git_dir / "config").write_text(
            "[core]\n"
            "\trepositoryformatversion = 0\n"
            "\tfilemode = true\n"
            "\tbare = false\n"
            "\tlogallrefupdates = true\n"
            '[remote "origin"]\n'
            f"\turl = {self.repo_url}\n"
            "\tfetch = +refs/heads/*:refs/remotes/origin/*\n",
            encoding="utf-8",
        )

    def _discover_refs(self) -> dict[str, str]:
        url = f"{self.repo_url}/info/refs?service=git-upload-pack"
        resp = self.client.get(
            url,
            headers={"Accept": "*/*"},
        )
        resp.raise_for_status()
        data = resp.content

        return self._parse_pkt_advertisement(data)

    def _parse_pkt_advertisement(self, data: bytes) -> dict[str, str]:
        refs: dict[str, str] = {}
        i = 0

        def read_pkt(buf: bytes, pos: int) -> tuple[bytes | None, int]:
            if pos + 4 > len(buf):
                return None, len(buf)
            size_hex = buf[pos : pos + 4]
            size = int(size_hex, 16)
            pos += 4
            if size == 0:
                return b"", pos
            payload_len = size - 4
            payload = buf[pos : pos + payload_len]
            return payload, pos + payload_len

        first_ref_line = True
        while i < len(data):
            pkt, i = read_pkt(data, i)
            if pkt is None:
                break
            if pkt == b"":
                continue

            line = pkt.rstrip(b"\n")

            if line.startswith(b"# service="):
                continue

            if first_ref_line:
                # format: <oid> <ref>\0cap1 cap2 ...
                first_ref_line = False
                main, *_caps = line.split(b"\x00", 1)
                oid, ref = main.split(b" ", 1)
                refs[ref.decode()] = oid.decode()
            else:
                if b" " in line:
                    oid, ref = line.split(b" ", 1)
                    refs[ref.decode()] = oid.decode()

        return refs

    def _pick_head(self, refs: dict[str, str]) -> tuple[str, str]:
        for candidate in ("refs/heads/main", "refs/heads/master"):
            if candidate in refs:
                return candidate, refs[candidate]
        ref, oid = next(iter(refs.items()))
        return ref, oid

    def _fetch_pack(self, want_oid: str) -> bytes:
        flush = b"0000"
        body = (
            self._pkt_line(
                f"want {want_oid}\0side-band-64k ofs-delta agent=git/2.43.0\n"
            )
            + flush
            + self._pkt_line("done\n")
            + flush
        )

        url = f"{self.repo_url}/git-upload-pack"

        with self.client.stream(
            "POST",
            url,
            content=body,
            headers={
                "Content-Type": "application/x-git-upload-pack-request",
                "Accept": "application/x-git-upload-pack-result",
            },
        ) as resp:
            resp.raise_for_status()
            b = BytesIO()
            stream_git_response(resp.iter_bytes(), b)
            return b.getvalue()

    def _store_pack_placeholder(self, data: bytes) -> None:
        # For now, just save raw response so you can inspect protocol output.
        # Later replace this with real side-band parsing and pack unpacking.
        out = self.git_dir / "debug-upload-pack-response.bin"
        out.write_bytes(data)

    def _write_head(self, head_ref: str) -> None:
        (self.git_dir / "HEAD").write_text(f"ref: {head_ref}\n", encoding="utf-8")

    @staticmethod
    def _pkt_line(text: str) -> bytes:
        payload = text.encode("utf-8")
        total = len(payload) + 4
        return f"{total:04x}".encode("ascii") + payload


g = MiniGitClone(
    "https://github.com/nedbat/byterun.git",
    "/tmp/TEST-CLONE",
    httpx.Client(
        follow_redirects=True,
        timeout=30.0,
        headers={
            "User-Agent": "MiniGitClone/0.1",
        },
    ),
)
g.clone()
