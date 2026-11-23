from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import anyio
import msgspec

from vtvcab_data.lib import DataResponse


class Reader:
    def __init__(self, root: Path):
        self.root = root

    @property
    def data_dir(self) -> Path:
        return self.root / "raw"

    async def read(self, date: date) -> DataResponse:
        """
        Read a DataResponse object from the appropriate file.

        Raises FileNotFoundError if the file does not exist.
        """
        path = (
            self.data_dir
            / f"month={date.strftime('%Y-%m')}/{date.strftime('%Y-%m-%d')}.json"
        )
        async with await anyio.open_file(path, "rb") as f:
            return msgspec.json.decode(await f.read(), type=DataResponse)

    async def should_refresh(self, date: date) -> bool:
        """
        Check if the data for the given date should be refreshed.
        """
        try:
            d = await self.read(date)
        except FileNotFoundError:
            return True
        else:
            now = datetime.now(tz=UTC)
            age_cutoff_before_refresh = now - timedelta(days=30)
            if d.requested_date_listing <= age_cutoff_before_refresh.date():
                # date requested is older than 30 days, no need to refresh
                return False
            return (now - d.requested_at) > timedelta(days=1)

    async def list_dates(self) -> list[date]:
        """
        List all dates for which data is available.
        """

        async def async_list_month_dirs():
            dd = anyio.Path(self.data_dir)
            async for month_dir in dd.iterdir():
                if (await month_dir.is_dir()) and month_dir.name.startswith("month="):
                    yield month_dir

        async def async_list_date_files(month_dir: Path):
            md = anyio.Path(month_dir)
            async for date_file in md.iterdir():
                if (await date_file.is_file()) and date_file.suffix == ".json":
                    yield date_file

        dates = []
        async for month_dir in async_list_month_dirs():
            async for date_file in async_list_date_files(month_dir):
                date_str = date_file.stem
                try:
                    d = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                dates.append(d)
        return sorted(dates)
