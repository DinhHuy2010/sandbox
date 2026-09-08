import orjson
from compression import zstd
from tqdm import tqdm


def get_possible_paths(d, prefix=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from get_possible_paths(v, prefix + k + ".")
        elif isinstance(v, list):
            known_keys = set()
            for item in v:
                if isinstance(item, dict):
                    known_keys.update(get_possible_paths(item, prefix + k + "[]."))
            yield from known_keys
        else:
            yield (prefix + k)

known_keys = set()
with zstd.ZstdFile("packages.nixpkgs-26.05pre906997.a672be65651c.jsonl.zst", "rb") as f:
    for line in tqdm(map(orjson.loads, f)):
        known_keys.update(get_possible_paths(line))
for key in sorted(known_keys):
    print(key)
