import zoneinfo
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5
from warnings import warn

import msgspec
import orjson
from tqdm import tqdm

RAW_DIRECTORY = Path("out/raw").resolve()
PROCESSED_DIRECTORY = Path("out/processed").resolve()
TODAY = date.today()
LOCAL_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")


class BroadcastEntry(msgspec.Struct):
    pid: UUID
    """A unique identifier for the program, generated using UUID5."""
    channel_id: str
    """The channel ID the program broadcasts on."""
    start: datetime
    """The start time of the program, represented as an aware datetime object."""
    end: datetime
    """The end time of the program, represented as an aware datetime object."""
    title: str
    """The title of the program."""
    alt: str | None = None
    """An alternative title for the program, if available."""

    @property
    def duration(self) -> int:
        """Compute the duration of the program in seconds."""
        if self.end < self.start:
            warn(
                f"Entry {self.pid} end time {self.end} is before start time {self.start}. Setting duration to 0.",
                UserWarning,
            )
            return 0
        return int((self.end - self.start).total_seconds())


class ChannelEntry(msgspec.Struct, frozen=True):
    channel_id: str
    """The unique identifier for the channel."""
    name: str
    """The name of the channel."""


PID_NAMESPACE = UUID("eb02c617-5231-4d7f-89bb-ff97f0c70ddb")


class Ingestor:
    def __init__(self):
        self.channels: dict[str, ChannelEntry] = {}
        self.entries: dict[date, list[BroadcastEntry]] = {}

    def _build_pid(
        self, channel_id: str, start: str, end: str, title: str, alt: str | None = None
    ):
        """Build a unique PID for a broadcast entry."""
        return uuid5(
            namespace=PID_NAMESPACE,
            name=f"{channel_id}-{start}-{end}-{title}{f'-{alt}' if alt else ''}",
        )

    def add_channel(self, channel_id: str, channel_title: str) -> None:
        """Add a channel entry to the ingestor."""
        if channel_id not in self.channels:
            self.channels[channel_id] = ChannelEntry(
                channel_id=channel_id, name=channel_title
            )

    def add_entry(
        self,
        broadcast_date: date,
        channel_id: str,
        start: str,
        end: str,
        title: str,
        alt: str | None = None,
    ) -> None:
        """Add a broadcast entry to the ingestor."""
        if broadcast_date not in self.entries:
            self.entries[broadcast_date] = []
        self.entries[broadcast_date].append(
            BroadcastEntry(
                pid=self._build_pid(channel_id, start, end, title, alt),
                channel_id=channel_id,
                # Assuming two dates are UTC
                start=datetime.fromisoformat(start).astimezone(LOCAL_TZ),
                end=datetime.fromisoformat(end).astimezone(LOCAL_TZ),
                title=title,
                alt=alt,
            )
        )

    def ingest(self, broadcast_date: date, raw_data: Any) -> None:
        """
        Ingest the raw data for the given broadcast date.
        This function can be customized to include any processing logic needed.
        """

        data = raw_data["data"]
        for channel in data:
            channel_id = channel["channel_id"]
            channel_title = channel["channel_title"]
            self.add_channel(channel_id, channel_title)
            for entry in channel["items"]:
                self.add_entry(
                    broadcast_date=broadcast_date,
                    channel_id=channel_id,
                    start=entry["start"],
                    end=entry["end"],
                    title=entry["title"],
                    alt=entry.get("episode"),
                )

    def stat(self):
        """Return statistics about the ingested data."""
        channels = len(self.channels)
        total_entries = 0
        stat_per_day = {}

        for broadcast_date, entries in self.entries.items():
            total_entries += len(entries)
            stat_per_day[broadcast_date.isoformat()] = {
                "entries": len(entries),
                "channels": len({entry.channel_id for entry in entries}),
                "should_likely_refetch": broadcast_date > TODAY,
            }

        return {
            "channels": channels,
            "total_entries": total_entries,
            "stat_per_day": stat_per_day,
        }

    def ingest_all(self, raw_directory: Path = RAW_DIRECTORY) -> None:
        """Ingest all raw JSON files in the raw directory."""
        for raw_file in tqdm(
            sorted(raw_directory.glob("*.json")),
            # desc="Ingesting raw JSON files",
            unit="file",
        ):
            broadcast_date = date.fromisoformat(raw_file.stem)
            with raw_file.open("rb") as f:
                raw_data = orjson.loads(f.read())
            self.ingest(broadcast_date, raw_data)


class Digestor:
    def __init__(
        self, ingestor: Ingestor, processed_directory: Path = PROCESSED_DIRECTORY
    ):
        self.ingestor = ingestor
        self.processed_directory = processed_directory
        self.last_updated = datetime.now(tz=LOCAL_TZ)

    def dump_metadata(self):
        print("--> Dumping metadata...")
        stat = self.ingestor.stat()
        metadata = {"statistics": stat, "last_updated": self.last_updated}
        metadata_file = self.processed_directory / "metadata.json"
        with metadata_file.open("wb") as f:
            f.write(
                orjson.dumps(
                    metadata, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
                )
            )

    def dump_channels(self):
        print("--> Dumping channels...")
        channels_file = self.processed_directory / "channels.json"
        with channels_file.open("wb") as f:
            f.write(
                orjson.dumps(
                    msgspec.to_builtins(self.ingestor.channels),
                    option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
                )
            )

    def dump_entries(self):
        print("--> Dumping entries...")
        for broadcast_date, entries in tqdm(self.ingestor.entries.items()):
            month_dir = (
                self.processed_directory
                / "entries"
                / f"month={broadcast_date.strftime('%Y-%m')}"
            )
            month_dir.mkdir(parents=True, exist_ok=True)
            entries_file = month_dir / f"{broadcast_date.strftime('%d')}.json"
            entries.sort(key=lambda e: e.start)  # Sort entries by start time
            with entries_file.open("wb") as f:
                f.write(msgspec.json.encode(entries))

    def dump_all(self):
        """Dump all processed data to the processed directory."""
        self.dump_metadata()
        self.dump_channels()
        self.dump_entries()


def read_raw_jsons(directory: Path) -> dict[date, Any]:
    print(f"--> Reading raw JSON files from {directory}...")
    out = {}
    for raw_file in tqdm(sorted(directory.glob("*.json"))):
        broadcast_date = date.fromisoformat(raw_file.stem)
        with raw_file.open("rb") as f:
            raw_data = orjson.loads(f.read())
        out[broadcast_date] = raw_data
    return out


def process_raw_jsons(raw_data: dict[date, Any]) -> Ingestor:
    print("--> Processing raw JSON data...")
    ingestor = Ingestor()
    for broadcast_date, data in tqdm(raw_data.items()):
        ingestor.ingest(broadcast_date, data)
    return ingestor


def main():
    """
    Main function to process all raw JSON files in the RAW_DIRECTORY.
    """
    # Ensure the processed directory exists
    PROCESSED_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Step 1: Read raw JSON files
    raw_data = read_raw_jsons(RAW_DIRECTORY)

    # Step 2: Process raw JSON data
    ingestor = process_raw_jsons(raw_data)

    # Step 3: Dump processed data
    digestor = Digestor(ingestor)
    digestor.dump_all()

    print("--> Processing complete. Processed files are saved in:", PROCESSED_DIRECTORY)


if __name__ == "__main__":
    main()
