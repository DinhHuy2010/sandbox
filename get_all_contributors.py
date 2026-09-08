import fileinput
import json
import sys
from collections import Counter

from tqdm import tqdm

authors_and_counters = Counter()

with fileinput.input(mode="rb") as f:
    for line in tqdm(f, desc="Counting authors"):
        name, email = line.strip().split(b"\0")
        authors_and_counters[(name.decode("utf-8"), email.decode("utf-8"))] += 1

json.dump(
    [
        {"name": key[0], "email": key[1], "count": value}
        for key, value in authors_and_counters.most_common()
    ],
    sys.stdout,
    indent=2,
    sort_keys=True,
)
