# import mediawiki_dump
# import mediawiki_dump.dumps
# import mediawiki_dump.reader

import polars as pl

import mwxml
from tqdm import tqdm
import wikitextparser as wtp

path = "fandom-youtube_pages_current-2025-10-27-191530.xml"
d = mwxml.Dump.from_file(path)
records = []
for p in tqdm(d.pages):
    if p.namespace not in (0, 14):
        continue
    r: mwxml.Revision = next(iter(p))
    # print("reading:", p.title)
    categories = []
    pp = wtp.parse(r.text)
    for link in pp.wikilinks:
        ns, _, link = link.title.partition(":")
        if ns == "Category":
            categories.append(link)
    records.append({"title": p.title, "text": r.text, "categories": categories, "namespace": p.namespace})
df = pl.DataFrame(records)
df.write_parquet("fandom-youtube-articles.parquet")

# lfd = mediawiki_dump.dumps.LocalFileDump(path)
# reader = mediawiki_dump.reader.DumpReader().read(lfd)
# for i in reader:
#     print(i)
