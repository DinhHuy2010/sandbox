from typing import Any, Callable

INBOX_SUCCESS = "88f96d4b4f8a5c3e617803d4143aff96"
INBOX_ERROR = "7cb19b4ad7b01920220e475ff22a13dd"
INBOX_REQUEST = "d1c9e5b8a2f4e6c9b7a3d8f0e5a1c2b3"

type Event = tuple[str, dict[str, Any]]
type Inbox = Callable[[Event], None]
type Agent = Callable[[str, dict[str, Any]], Any]


def create_inbox() -> Inbox:
    def inbox(event: Event) -> None:
        event_type, event_data = event
        if event_type == INBOX_SUCCESS:
            print(f"Success: {event_data}")
        elif event_type == INBOX_ERROR:
            print(f"Error: {event_data}")
        else:
            print(f"Unknown event type: {event_type} with data: {event_data}")

    return inbox


def discover_inbox(agent: Agent):
    inboxes: list[Inbox] = []

    def on_inbox(inbox: Inbox) -> None:
        inboxes.append(inbox)

    status, context = agent(
        INBOX_REQUEST, {"action": "inbox_discovery", "handler": on_inbox}
    )
    if status == INBOX_SUCCESS:
        print("Inbox discovery successful.")
    else:
        print(f"Inbox discovery failed with error: {context.get('error')}")

    return inboxes


def send_message_to_inbox(inbox: Inbox, data: dict[str, Any]):
    inbox(("message", data))
    return INBOX_SUCCESS, None


def send_message_to_agent(agent: Agent, data: dict[str, Any]):
    status, context = agent("message", data)
    if status == INBOX_SUCCESS:
        print("Message sent successfully.")
    else:
        print(f"Failed to send message with error: {context.get('error')}")
    return status, context


def create_agent(inboxes: list[Inbox]) -> Agent:
    def agent(event_type: str, event_data: dict[str, Any]) -> Any:
        if event_type == INBOX_REQUEST:
            handler = event_data.get("handler")
            if callable(handler):
                for inbox in inboxes:
                    handler(inbox)
                return INBOX_SUCCESS, None
            else:
                print("Invalid handler provided for inbox discovery.")
                return INBOX_ERROR, {"error": "invalid_handler"}
        else:
            print(
                f"Agent received unknown event type: {event_type} with data: {event_data}"
            )
            return INBOX_ERROR, {"error": "unknown_event_type"}

    return agent


agent = create_agent([create_inbox(), create_inbox()])
print(discover_inbox(agent))
