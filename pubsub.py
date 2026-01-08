import json
import secrets
import uuid
from base64 import b64decode, b64encode
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from email import message_from_bytes
from email.message import Message
from email.mime.application import MIMEApplication
from typing import Any, Callable, NewType

MessageQueue = NewType("MessageQueue", str)
type SubscriberCallable = Callable[[MessageQueue, Message], None]


def generate_id() -> str:
    return str(uuid.uuid4())


@dataclass
class PBMessage:
    message_id: str
    subscriber_id: str
    queue: MessageQueue
    message: Message

    def build_json_payload(self) -> str:
        msg = {
            "message_id": self.message_id,
            "subscriber_id": self.subscriber_id,
            "queue": self.queue,
            "message": b64encode(self.message.as_bytes()).decode("utf-8"),
        }
        return json.dumps(msg)

    def build_message(self) -> Message:
        msg = Message()
        msg.set_type("application/vnd.pubsub.pbmessage+json")
        msg["X-Pubsub-Message-ID"] = self.message_id
        msg["X-Pubsub-Subscriber-ID"] = self.subscriber_id
        msg["X-Pubsub-Queue"] = self.queue
        msg.set_payload(self.build_json_payload())
        return msg

    @classmethod
    def from_message(cls, msg: Message) -> "PBMessage":
        if msg.get_content_type() != "application/vnd.pubsub.pbmessage+json":
            raise ValueError(
                "Invalid message content type: expected PBMessage type (application/vnd.pubsub.pbmessage+json)"
            )
        payload = json.loads(msg.get_payload())  # type: ignore
        raw_message = b64decode(payload["message"])
        message = message_from_bytes(raw_message)
        return cls(
            message_id=payload["message_id"],
            subscriber_id=payload["subscriber_id"],
            queue=payload["queue"],
            message=message,
        )


@dataclass
class Subscriber:
    id: str
    function: SubscriberCallable
    queues: list[MessageQueue] | None = field(default=None)

    def should_receive(self, queue: MessageQueue) -> bool:
        return self.queues is None or queue in self.queues

    def receive_message(self, queue: MessageQueue, message: Message) -> None:
        if self.should_receive(queue):
            self.function(queue, message)


class SubscriberManager:
    def __init__(self) -> None:
        self.subscribers: dict[str, Subscriber] = {}

    def add_subscriber(self, subscriber: Subscriber) -> None:
        self.subscribers[subscriber.id] = subscriber

    def remove_subscriber(self, subscriber_id: str) -> None:
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]

    def get_subscribers_for_queue(self, queue: MessageQueue) -> list[Subscriber]:
        return [
            subscriber
            for subscriber in self.subscribers.values()
            if subscriber.should_receive(queue)
        ]


def _message_delivery(msg: PBMessage, subscriber_manager: SubscriberManager) -> None:
    subscriber = subscriber_manager.subscribers.get(msg.subscriber_id)
    if subscriber:
        subscriber.receive_message(msg.queue, msg.message)


class MessagerService:
    def __init__(self, subscriber_manager: SubscriberManager, workers: int) -> None:
        self.subscriber_manager = subscriber_manager
        self.messages: dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def store_message(self, msg: PBMessage) -> None:
        future = self.executor.submit(_message_delivery, msg, self.subscriber_manager)
        self.messages[msg.message_id] = {"msg": msg, "future": future}

    def shutdown(self, *, force: bool = False) -> None:
        if force:
            self.executor.shutdown(wait=False, cancel_futures=True)
        else:
            self.executor.shutdown(wait=True)


class Broker:
    def __init__(self, sub: SubscriberManager, workers: int = 4) -> None:
        self.subscriber_manager = sub
        self.messager = MessagerService(self.subscriber_manager, workers)

    def subscribe(
        self, function: SubscriberCallable, queues: list[MessageQueue] | None = None
    ) -> str:
        subscriber_id = generate_id()
        subscriber = Subscriber(id=subscriber_id, function=function, queues=queues)
        self.subscriber_manager.add_subscriber(subscriber)
        return subscriber_id

    def publish(self, queue: MessageQueue, message: Message) -> None:
        subscribers = self.subscriber_manager.get_subscribers_for_queue(queue)
        for subscriber in subscribers:
            pb_message = PBMessage(
                message_id=generate_id(),
                subscriber_id=subscriber.id,
                queue=queue,
                message=message,
            )
            self.messager.store_message(pb_message)

    def shutdown(self) -> None:
        self.messager.shutdown()

    def force_shutdown(self) -> None:
        self.messager.shutdown(force=True)


# Example usage
def main():
    def sample_subscriber(queue: MessageQueue, message: Message) -> None:
        print(f"Received message on {queue}: {message.get_payload()}")

    def build_messages(n: int) -> list[Message]:
        messages: list[Message] = []
        for _ in range(n):
            msg = MIMEApplication(secrets.token_bytes(128))
            messages.append(msg)
        return messages

    sub = SubscriberManager()
    broker = Broker(sub, workers=4)
    _ = broker.subscribe(sample_subscriber, [MessageQueue("test_queue")])

    for msg in build_messages(1024):
        broker.publish(MessageQueue("test_queue"), msg)


if __name__ == "__main__":
    main()
