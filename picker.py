from car import Car
import random


def filter_cars(
    cars: list[Car],
    car_class: str | None = None,
    country: str | None = None,
    car_type: str | None = None,
    make: str | None = None,
) -> list[Car]:
    result = []

    for car in cars:
        if car_class is not None and car.car_class != car_class:
            continue

        if country is not None and car.country != country:
            continue

        if car_type is not None and car.car_type != car_type:
            continue

        if make is not None and car.make != make:
            continue

        result.append(car)

    return result


def pick_random_car(cars: list[Car]) -> Car | None:
    if not cars:
        return None

    return random.choice(cars)