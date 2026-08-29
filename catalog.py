import json
from pathlib import Path

from car import Car


def load_cars(file_path: str | Path) -> list[Car]:
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    cars = []

    for car_data in data:
        car = Car(**car_data)
        cars.append(car)

    return cars