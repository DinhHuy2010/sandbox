import json
import httpx
# import gzip

# from breader import BReader

client = httpx.Client()


def pull_manifest():
    url = "https://openalex.s3.amazonaws.com/data/works/manifest"
    response = client.get(url)
    response.raise_for_status()
    manifest = response.json()
    return manifest


manifest = pull_manifest()
for entry in manifest["entries"]:
    s3_url = entry["url"]
    content_length = entry["meta"]["content_length"]
    total_records = entry["meta"]["record_count"]
    print(f"{s3_url} ({content_length:,} bytes, {total_records:,} records)")
full_length = manifest["meta"]["content_length"]
total_records = manifest["meta"]["record_count"]
print(f"Total: {full_length:,} bytes, {total_records:,} records")

