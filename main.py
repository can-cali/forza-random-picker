from pathlib import Path

from catalog import load_cars


def main():
    base_dir = Path(__file__).resolve().parent
    catalog_path = base_dir / "data" / "cars.json"

    cars = load_cars(catalog_path)

    print(f"Loaded {len(cars)} cars")

    for car in cars:
        print(car)


if __name__ == "__main__":
    main()