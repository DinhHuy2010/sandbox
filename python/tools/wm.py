import bz2
import urllib.request
from typing import cast

import mwxml

url = "https://dumps.wikimedia.org/other/mediawiki_content_history/enwiki/2026-04-01/xml/bzip2/enwiki-2026-04-01-p15615269p15666446.xml.bz2"

with urllib.request.urlopen(url) as response:
    with bz2.BZ2File(response) as file:
        dump = mwxml.Dump.from_file(file)
        for page in dump:
            page = cast(mwxml.Page, page)
            print(f"Title: {page.title}")
            # for revision in page:
            #     revision = cast(mwxml.Revision, revision)
            #     print(
            #         f"  Revision ID: {revision.id}, Timestamp: {revision.timestamp.to_json()}"
            #     )
