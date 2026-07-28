from decimal import Decimal
from pydantic import BaseModel, computed_field


class Point(BaseModel):
    x: Decimal
    y: Decimal
    z: Decimal = Decimal(0)

    @computed_field
    @property
    def path(self) -> str:
        return f"/points/{self.x},{self.y},{self.z}"

    @computed_field
    @property
    def uri(self) -> str:
        return f"points://{self.x},{self.y},{self.z}"

    @computed_field
    @property
    def coordinates(self) -> tuple[Decimal, Decimal, Decimal]:
        return (self.x, self.y, self.z)
