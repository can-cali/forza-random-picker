from pathlib import Path

from catalog import load_cars
from picker import filter_cars, pick_random_car


def main():
    base_dir = Path(__file__).resolve().parent
    catalog_path = base_dir / "data" / "cars.json"

    cars = load_cars(catalog_path)

    filtered_cars = filter_cars(
        cars,
        car_class="X",
        country="Italy",
    )

    print(f"Total cars: {len(cars)}")
    print(f"Matching cars: {len(filtered_cars)}")

    for car in filtered_cars:
        print(car)

    selected_car = pick_random_car(filtered_cars)

    if selected_car is None:
        print("No cars match these filters.")
    else:
        print("Random car:")
        print(selected_car)


if __name__ == "__main__":
    main()