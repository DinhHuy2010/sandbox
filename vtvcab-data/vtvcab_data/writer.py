import os
import tempfile
from pathlib import Path

import anyio
import msgspec

from vtvcab_data.lib import DataResponse


class Writer:
    def __init__(self, root: Path):
        self.root = root

    def init(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def data_dir(self) -> Path:
        return self.root / "raw"

    async def ingest(self, response: DataResponse):
        """
        Ingest a DataResponse object and write it to the appropriate file.

        DOES NOT CHECK IS EXISTING FILE, WILL OVERWRITE IF EXISTS!
        """
        path = (
            self.data_dir
            / f"month={response.requested_date_listing.strftime('%Y-%m')}/{response.requested_date_listing.strftime('%Y-%m-%d')}.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, temp_filename = tempfile.mkstemp(dir=path.parent, suffix=".json.tmp")
            async with await anyio.open_file(fd, "wb") as f:
                await f.write(msgspec.json.encode(response))
            os.replace(temp_filename, path)
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
