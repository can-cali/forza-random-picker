import requests
from pathlib import Path
import re
import unicodedata
import json
from forza_picker.car import Car
from forza_picker.image_aliases import IMAGE_ALIASES




PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_CACHE_DIR = PROJECT_ROOT / "cache" / "car_images"
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


def download_image(
    image_url: str,
    destination: Path,
) -> None:
    response = requests.get(
        image_url,
        timeout=15,
    )

    response.raise_for_status()

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(response.content)


def get_cached_image_path(file_name: str) -> Path:
    return IMAGE_CACHE_DIR / file_name


def get_or_download_wiki_image(
    wiki_title: str,
) -> Path | None:
    file_name = cache_file_name_from_wiki_title(wiki_title)
    destination = get_cached_image_path(file_name)

    if destination.exists():
        return destination

    image_url = get_wiki_image_url(wiki_title)

    if image_url is None:
        return None

    try:
        download_image(
            image_url,
            destination,
        )
    except requests.RequestException:
        return None

    return destination

def cache_file_name_from_wiki_title(wiki_title: str) -> str:
    return wiki_title.removeprefix("File:")

def car_image_key(car: Car) -> str:
    return f"{car.year}|{car.make}|{car.model}"

def load_image_map(file_path: str | Path) -> dict[str, str]:
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def get_local_car_image_path(
        car : Car,
        image_map : dict[str, str],
) -> Path | None:
    key = car_image_key(car)

    file_name = image_map.get(key)

    if file_name is None:
        return None

    image_path = get_cached_image_path(file_name)

    if not image_path.exists():
        return None

    return image_path