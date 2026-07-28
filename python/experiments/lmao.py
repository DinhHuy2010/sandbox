from hashlib import sha256
import json
from uuid import uuid4


def hash_request(request):
    p = json.dumps(request).encode("utf-8")
    return sha256(p).hexdigest()


def echo(request):
    return {
        "envelope": "1.0",
        "type": "response",
        "payload": {"message": request["payload"]["message"]},
        "ctx": {"request_id": request["id"], "request_hash": hash_request(request)},
        "id": str(uuid4()),
    }


envelope = {
    "envelope": "1.0",
    "id": str(uuid4()),
    "type": "request",
    "payload": {"message": "Hello, World!"},
}

print(echo(envelope))
