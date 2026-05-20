from cmath import cos, sin
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
        return f"points://coordinates/{self.x},{self.y},{self.z}"

    @computed_field
    @property
    def coordinates(self) -> tuple[Decimal, Decimal, Decimal]:
        return (self.x, self.y, self.z)


def move(point: Point, dx: Decimal, dy: Decimal, dz: Decimal = Decimal(0)) -> Point:
    return Point(x=point.x + dx, y=point.y + dy, z=point.z + dz)


def scale(point: Point, factor: Decimal) -> Point:
    return Point(x=point.x * factor, y=point.y * factor, z=point.z * factor)


def rotate(point: Point, angle: Decimal) -> Point:
    # Implement this
    rotated_x = point.x * cos(angle) - point.y * sin(angle)
    rotated_y = point.x * sin(angle) + point.y * cos(angle)
    return Point(x=rotated_x, y=rotated_y, z=point.z)


point = Point(x=Decimal(1), y=Decimal(2))
print(point.path)  # Output: /points/1,2,0
print(point.uri)  # Output: points://coordinates/1,2,0
print(point.coordinates)  # Output: (Decimal('1'), Decimal('2'), Decimal('0'))
# print(point.)  # Output: (Decimal('1'), Decimal('2'), Decimal('0'))
