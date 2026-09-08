from __future__ import annotations

import mailbox
from email.message import Message
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path("apache-mailing-list-mbox")
OUTPUT = Path("apache-mailing-list.parquet")

BATCH_SIZE = 10_000


SCHEMA = pa.schema(
    [
        ("domain", pa.string()),
        ("list", pa.string()),
        ("archive_month", pa.string()),
        ("source_file", pa.string()),
        ("message_id", pa.string()),
        ("date", pa.string()),
        ("from", pa.string()),
        ("to", pa.string()),
        ("cc", pa.string()),
        ("reply_to", pa.string()),
        ("subject", pa.string()),
        ("in_reply_to", pa.string()),
        ("references", pa.string()),
        ("content_type", pa.string()),
        ("charset", pa.string()),
        ("body_text", pa.large_string()),
        ("body_html", pa.large_string()),
        ("raw_size", pa.int64()),
    ]
)


def header(msg: Message, name: str) -> str | None:
    value = msg.get(name)
    return str(value) if value is not None else None


def decode_part(part: Message) -> str | None:
    try:
        payload = part.get_payload(decode=True)

        if payload is None:
            value = part.get_payload()
            return value if isinstance(value, str) else None

        charset = part.get_content_charset() or "utf-8"

        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")

    except Exception:
        return None


def extract_bodies(msg: Message) -> tuple[str | None, str | None]:
    text_parts = []
    html_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue

            disposition = part.get_content_disposition()

            # Don't turn attachments into message bodies.
            if disposition == "attachment":
                continue

            content_type = part.get_content_type()

            if content_type == "text/plain":
                value = decode_part(part)
                if value:
                    text_parts.append(value)

            elif content_type == "text/html":
                value = decode_part(part)
                if value:
                    html_parts.append(value)

    else:
        value = decode_part(msg)

        if msg.get_content_type() == "text/plain":
            if value:
                text_parts.append(value)

        elif msg.get_content_type() == "text/html":
            if value:
                html_parts.append(value)

    return (
        "\n".join(text_parts) or None,
        "\n".join(html_parts) or None,
    )


def convert_message(
    msg: Message,
    *,
    domain: str,
    list_name: str,
    month: str,
    source_file: str,
) -> dict:
    text, html = extract_bodies(msg)

    try:
        raw_size = len(msg.as_bytes())
    except Exception:
        raw_size = None

    return {
        "domain": domain,
        "list": list_name,
        "archive_month": month,
        "source_file": source_file,
        "message_id": header(msg, "Message-ID"),
        "date": header(msg, "Date"),
        "from": header(msg, "From"),
        "to": header(msg, "To"),
        "cc": header(msg, "Cc"),
        "reply_to": header(msg, "Reply-To"),
        "subject": header(msg, "Subject"),
        "in_reply_to": header(msg, "In-Reply-To"),
        "references": header(msg, "References"),
        "content_type": msg.get_content_type(),
        "charset": msg.get_content_charset(),
        "body_text": text,
        "body_html": html,
        "raw_size": raw_size,
    }


def flush(writer: pq.ParquetWriter, rows: list[dict]) -> None:
    if not rows:
        return

    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    writer.write_table(table)
    rows.clear()


def main() -> None:
    files = sorted(ROOT.glob("*/*/*.mbox"))

    print(f"Found {len(files):,} mbox files")

    rows = []
    messages = 0
    failures = 0

    with pq.ParquetWriter(
        OUTPUT,
        SCHEMA,
        compression="zstd",
    ) as writer:
        for number, path in enumerate(files, 1):
            relative = path.relative_to(ROOT)

            domain = relative.parts[0]
            list_name = relative.parts[1]
            month = path.stem

            try:
                box = mailbox.mbox(
                    path,
                    create=False,
                )

                for msg in box:
                    try:
                        rows.append(
                            convert_message(
                                msg,
                                domain=domain,
                                list_name=list_name,
                                month=month,
                                source_file=str(relative),
                            )
                        )

                        messages += 1

                        if len(rows) >= BATCH_SIZE:
                            flush(writer, rows)

                    except Exception as exc:
                        failures += 1
                        print(f"\nMESSAGE ERROR {path}: {type(exc).__name__}: {exc}")

            except Exception as exc:
                failures += 1
                print(f"\nMBOX ERROR {path}: {type(exc).__name__}: {exc}")

            print(
                # f"\r"
                f"[{number:,}/{len(files):,}] "
                f"{messages:,} messages | "
                f"{failures:,} errors | "
                f"{path}",
                # end="",
                flush=True,
            )

        flush(writer, rows)

    print()
    print()
    print(f"Messages : {messages:,}")
    print(f"Errors   : {failures:,}")
    print(f"Output   : {OUTPUT}")
    print(f"Size     : {OUTPUT.stat().st_size / 1024**3:.2f} GiB")


if __name__ == "__main__":
    main()
