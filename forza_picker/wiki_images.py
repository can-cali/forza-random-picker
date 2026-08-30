import requests
from forza_picker.car import Car
import re
import unicodedata
from forza_picker.image_aliases import IMAGE_ALIASES





FANDOM_API_URL = "https://forza.fandom.com/api.php"


def get_wiki_image_url(file_name: str) -> str | None:
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url",
        "titles": file_name,
    }

    response = requests.get(
        FANDOM_API_URL,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    pages = data["query"]["pages"]
    page = next(iter(pages.values()))

    if "imageinfo" not in page:
        return None

    return page["imageinfo"][0]["url"]

def get_car_image_url(car: Car) -> str | None:
    file_name = f"File:FH6 {car.make} {car.model}.png"

    return get_wiki_image_url(file_name)

def get_fh6_thumbnail_titles() -> list[str]:
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": "Category:Thumbnails (FH6)",
        "cmtype": "file",
        "cmlimit": 500,
    }

    titles = []

    while True:
        response = requests.get(
            FANDOM_API_URL,
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        members = data["query"]["categorymembers"]

        for member in members:
            titles.append(member["title"])

        if "continue" not in data:
            break

        params["cmcontinue"] = data["continue"]["cmcontinue"]
        

    return titles


def get_base_thumbnail_titles(titles: list[str]) -> list[str]:
    return [
        title
        for title in titles
        if not title.startswith("File:FH6 Aftermarket ")
    ]


def normalize_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)

    name = name.encode("ascii", "ignore").decode("ascii")

    name = name.lower()

    return re.sub(r"[^a-z0-9]", "", name)


def normalize_wiki_title(title: str) -> str:
    title = title.removeprefix("File:FH6 ")
    title = title.removesuffix(".png")

    return normalize_name(title)


def normalize_car_name(car: Car) -> str:
    return normalize_name(
        f"{car.make} {car.model}"
    )

# For same car models with multiple different chassis years
def normalize_car_name_with_year(car: Car) -> str:
    return normalize_name(
        f"{car.make} {car.model} {car.year}"
    )

def car_alias_key(car: Car) -> tuple[int, str, str]:
    return (
        car.year,
        car.make,
        car.model,
    )

def find_wiki_title_for_car(
    car: Car,
    wiki_lookup: dict[str, str],
) -> str | None:
    key = normalize_car_name(car)

    if key in wiki_lookup:
        return wiki_lookup[key]

    key_with_year = normalize_car_name_with_year(car)

    if key_with_year in wiki_lookup:
        return wiki_lookup[key_with_year]

    alias_key = car_alias_key(car)

    if alias_key in IMAGE_ALIASES:
        return IMAGE_ALIASES[alias_key]

    return None