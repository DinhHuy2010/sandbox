import argparse
from typing import cast

import htmllistparse

parser = argparse.ArgumentParser(
    description="Fetch and display HTML listing from a URL"
)
parser.add_argument("url", type=str, help="URL to fetch the listing from")
args = parser.parse_args()

cwd, listing = htmllistparse.fetch_listing(args.url)
for item in cast(list[htmllistparse.FileEntry], listing):
    print(item.name, item.size)
