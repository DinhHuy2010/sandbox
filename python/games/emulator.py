import re
from abc import ABC, abstractmethod
from collections.abc import Sequence

from pydantic import JsonValue


def title_to_slug(title: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")


class BaseField(ABC):
    @abstractmethod
    def ask(self) -> tuple[str, JsonValue]: ...


class BasicField(BaseField):
    def __init__(self, name: str, prompt: str | None = None):
        self.name = name
        self.prompt = prompt or name

    def ask(self) -> tuple[str, JsonValue]:
        value = input(f"{self.prompt}: ").strip()
        return self.name, value


class IntField(BaseField):
    def __init__(
        self,
        name: str,
        prompt: str | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
    ):
        self.name = name
        self.prompt = prompt or f"{name} (integer)"
        self.min_value = min_value
        self.max_value = max_value

    def ask(self) -> tuple[str, JsonValue]:
        while True:
            raw = input(f"{self.prompt}: ").strip()
            try:
                val = int(raw)
            except ValueError:
                print("  x Invalid integer. Please try again.")
                continue

            if self.min_value is not None and val < self.min_value:
                print(f"  x Value must be at least {self.min_value}.")
                continue
            if self.max_value is not None and val > self.max_value:
                print(f"  x Value must be at most {self.max_value}.")
                continue

            return self.name, val


class EmailField(BaseField):
    EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, name: str, prompt: str | None = None):
        self.name = name
        self.prompt = prompt or f"{name} (email)"

    def ask(self) -> tuple[str, JsonValue]:
        while True:
            raw = input(f"{self.prompt}: ").strip()
            if self.EMAIL_REGEX.match(raw):
                return self.name, raw
            print("  x Invalid email address. Example: user@example.com")


class ChoiceField(BaseField):
    def __init__(
        self,
        name: str,
        choices: Sequence[str],
        prompt: str | None = None,
    ):
        self.name = name
        self.choices = choices
        self.prompt = prompt or f"{name}"

    def ask(self) -> tuple[str, JsonValue]:
        print(f"{self.prompt}:")
        for idx, choice in enumerate(self.choices, 1):
            print(f"  {idx}. {choice}")

        while True:
            raw = input("Select an option (number or exact text): ").strip()

            # Handle selection by numeric index (1-based)
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(self.choices):
                    return self.name, self.choices[idx]

            # Handle selection by exact choice text matching (case-insensitive)
            for choice in self.choices:
                if choice.lower() == raw.lower():
                    return self.name, choice

            print(
                f"  x Invalid choice. Enter 1–{len(self.choices)} or exact option text."
            )


class Form(BaseField):
    def __init__(
        self, title: str, fields: list[BaseField], subform_key: str | None = None
    ):
        self.title = title
        self.fields = fields
        self.subform_key = subform_key or title_to_slug(title)

    def ask(self) -> tuple[str, JsonValue]:
        print(f"\n=== {self.title} ===")
        responses = {}
        for field in self.fields:
            name, value = field.ask()
            responses[name] = value
        return self.subform_key, responses


def ask_form(form: Form) -> dict[str, JsonValue]:
    key, responses = form.ask()
    return {key: responses}


# Example Usage
form = Form(
    "User Registration",
    [
        BasicField("Name"),
        EmailField("Email"),
        IntField("Age", min_value=13, max_value=120),
        ChoiceField("Account Type", choices=["Free", "Pro", "Enterprise"]),
        Form(
            "Shipping Address",
            [
                BasicField("Street"),
                BasicField("City"),
                IntField("Postal Code"),
            ],
        ),
    ],
)

out = ask_form(form)
print("\nCollected Form Data:")
print(out)
