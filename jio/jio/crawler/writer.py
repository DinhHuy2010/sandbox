import os
from pathlib import Path
from tempfile import mkstemp

import anyio
import msgspec

from jio.crawler.config import Config
from jio.crawler.models import DataResponse


class Writer:
    def __init__(self, config: Config):
        self.config = config

    async def ensure(self) -> None:
        await self.config.ensure()

    async def write(self, resp: DataResponse) -> None:
        # Write the raw data to a file
        raw_data_file = (
            self.config.data_dir
            / f"channel_id={resp.about.channel_id}/month={resp.about.date_requested.strftime('%Y-%m')}/{resp.about.date_requested.isoformat()}.json"
        )
        await raw_data_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = mkstemp(dir=str(raw_data_file.parent), suffix=".atomic_pending")
        tp = anyio.Path(tmp_path)
        try:
            async with await anyio.open_file(fd, "wb") as f:
                s = msgspec.json.encode(resp)
                await f.write(s)
            os.replace(tmp_path, raw_data_file)
        finally:
            await tp.unlink(missing_ok=True)
