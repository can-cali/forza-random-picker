from forza_picker.car import Car
import random


def filter_cars(
    cars: list[Car],
    car_class: str | None = None,
    country: str | None = None,
    car_type: str | None = None,
    make: str | None = None,
    is_in_autoshow: bool | None = None,
    dlcs: set[str | None] | None = None,
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

        if (
            is_in_autoshow is not None
            and car.is_in_autoshow != is_in_autoshow
        ):
            continue

        if dlcs is not None and car.dlc not in dlcs:
            continue

        result.append(car)

    return result


def pick_random_car(cars: list[Car]) -> Car | None:
    if not cars:
        return None

    return random.choice(cars)
