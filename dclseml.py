# from email.message import EmailMessage, Message
# from email.mime.application import MIMEApplication
# import secrets


# def attach_messages(*msgs: Message) -> Message:
#     """Attach multiple email Messages into a single MIMEApplication."""
#     combined = EmailMessage()
#     for msg in msgs:
#         combined.add_attachment(
#             msg.as_bytes(),
#             maintype="message",
#             subtype="rfc822",
#             filename=f"attachment_{secrets.token_hex(8)}.eml",
#         )
#     return combined


# msgs: list[Message] = []
# for _ in range(3):
#     msg = MIMEApplication(secrets.token_bytes(64))
#     msgs.append(msg)
# combined_msg = attach_messages(*msgs)
# print(combined_msg.as_string())

from email.message import Message
import json


def add(payload: Message) -> Message:
    ctype = payload.get_content_type()
    if ctype != "application/vnd.dclseml.functions.add+json":
        raise ValueError(f"Invalid content type: {ctype}")
    p = json.loads(payload.get_payload(decode=True))  # type: ignore
    result = p["parameters"]["left"] + p["parameters"]["right"]
    resp = {
        "result": result,
    }
    msg = Message()
    msg.set_type("application/vnd.dclseml.functions.add.response+json")
    msg.set_payload(json.dumps(resp))
    return msg

msg = Message()
msg.set_type("application/vnd.dclseml.functions.add+json")
payload = {
    "parameters": {
        "left": 5,
        "right": 7,
    },
}
msg.set_payload(json.dumps(payload))
print(add(msg))  # type: ignore
    
