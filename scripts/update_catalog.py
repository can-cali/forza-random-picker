import json
from dataclasses import asdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from car import Car

FORZA_CAR_LIST_URL = "https://forza.net/fh6cars"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "data" / "cars.json"


def fetch_car_list_page() -> str:
    response = requests.get(
        FORZA_CAR_LIST_URL,
        timeout=10,
    )

    response.raise_for_status()

    return response.text


def parse_car_row(values: list[str]) -> Car:
    make = values[0]
    full_name = values[1]
    car_type = values[2]
    class_data = values[3]
    country = values[4]
    collection = values[5]
    add_ons = values[6]

    dlc = add_ons.strip() or None

    year = int(full_name[:4])

    prefix = f"{year} {make} "
    model = full_name.removeprefix(prefix)

    pi_text, car_class = class_data.split(maxsplit=1)
    pi = int(pi_text)

    is_in_autoshow = "Autoshow" in collection

    return Car(
        make=make,
        model=model,
        year=year,
        pi=pi,
        car_class=car_class,
        country=country,
        car_type=car_type,
        is_in_autoshow=is_in_autoshow,
        dlc=dlc,
        ordinal=None,
    )

def save_catalog(cars: list[Car], file_path: str | Path) -> None:
    car_data = [asdict(car) for car in cars]

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(
            car_data,
            file,
            indent=4,
            ensure_ascii=False,
        )

def main():
    html = fetch_car_list_page()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    if table is None:
        print("No table found")
        return

    rows = table.find_all("tr")

    cars: list[Car] = []
    for row in rows[1:]:
        cells = row.find_all("td")
        values = [cell.get_text(strip=True) for cell in cells]

        car = parse_car_row(values)
        cars.append(car)

        print(f"Successfully parsed {len(cars)} cars")

    save_catalog(cars, CATALOG_PATH)
    print(f"Saved catalog to {CATALOG_PATH}")

if __name__ == "__main__":
    main()