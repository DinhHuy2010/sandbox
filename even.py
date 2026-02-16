import datetime
import random

from pydantic import Field, JsonValue, BaseModel


rand = random.SystemRandom()


class Event(BaseModel):
    name: str = Field(..., min_length=1, pattern=r"^[a-z0-9_-]+(\.[a-z0-9_-]+)+$")
    created: datetime.datetime
    data: JsonValue = Field(default=None)

    @classmethod
    def create(cls, name: str, data: JsonValue = None) -> "Event":
        return cls(
            name=name, created=datetime.datetime.now(datetime.timezone.utc), data=data
        )


def rand_sum_sequence(
    result: int, *, max_value: int | None = None, max_elements: int | None = None
):
    yield Event.create(
        "rand_sum_sequence.start",
        {
            "result": result,
            "max_value": max_value,
            "max_elements": max_elements,
        },
    )
    if result <= 0:
        yield Event.create(
            "rand_sum_sequence.error",
            {"message": "Result must be positive", "result": result},
        )
        return
    if max_elements is not None and max_value is not None:
        if max_elements * max_value < result:
            yield Event.create(
                "rand_sum_sequence.error",
                {
                    "message": "Impossible to reach result with given constraints",
                    "result": result,
                    "max_value": max_value,
                    "max_elements": max_elements,
                },
            )
            return

    remaining = result
    elements = 0
    while remaining > 0:
        if max_elements is not None and elements >= max_elements - 1:
            yield Event.create(
                "rand_sum_sequence.pick",
                {
                    "pick": remaining,
                    "remaining": remaining,
                    "elements": elements,
                },
            )
            break
        if max_value is not None:
            max_pick = min(remaining, max_value)
        else:
            max_pick = remaining
        pick = rand.randint(1, max_pick)
        yield Event.create(
            "rand_sum_sequence.pick",
            {
                "pick": pick,
                "remaining": remaining - pick,
                "elements": elements + 1,
            },
        )
        remaining -= pick
        elements += 1

    yield Event.create(
        "rand_sum_sequence.end",
        {"total_elements": elements},
    )

for e in rand_sum_sequence(10, max_value=4, max_elements=5):
    print(e.model_dump_json())
