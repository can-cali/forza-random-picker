from pathlib import Path
import json

from forza_picker.catalog import load_cars
from forza_picker.wiki_images import (
    get_fh6_thumbnail_titles,
    get_base_thumbnail_titles,
    normalize_wiki_title,
    find_wiki_title_for_car,
    get_cached_image_path,
    cache_file_name_from_wiki_title,
    get_or_download_wiki_image,
    car_image_key,
)


def main():
    project_root = Path(__file__).resolve().parent.parent
    catalog_path = project_root / "data" / "cars.json"

    cars = load_cars(catalog_path)

    titles = get_fh6_thumbnail_titles()
    base_thumbnails = get_base_thumbnail_titles(titles)

    wiki_lookup = {
        normalize_wiki_title(title): title
        for title in base_thumbnails
    }

    cached = []
    missing = []
    unmatched = []

    image_map = {}

    for car in cars:
        wiki_title = find_wiki_title_for_car(
            car,
            wiki_lookup,
        )

        if wiki_title is None:
            unmatched.append(car)
            continue

        file_name = cache_file_name_from_wiki_title(wiki_title)

        key = car_image_key(car)
        image_map[key] = file_name

        image_path = get_cached_image_path(
            file_name,
        )

        if image_path.exists():
            cached.append(car)
        else:
            missing.append(car)

    image_map_path = project_root / "data" / "image_map.json"

    with open(image_map_path, "w", encoding="utf-8") as file:
        json.dump(
            image_map,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"Catalog cars: {len(cars)}")
    print(f"Cached images: {len(cached)}")
    print(f"Missing images: {len(missing)}")
    print(f"Unmatched cars: {len(unmatched)}")

    print("\nDownloading missing images:")

    downloaded = []
    failed = []

    for car in missing:
        wiki_title = find_wiki_title_for_car(
            car,
            wiki_lookup,
        )

        if wiki_title is None:
            continue

        print(f"Downloading: {car.year} {car.make} {car.model}")

        image_path = get_or_download_wiki_image(
            wiki_title,
        )

        if image_path is None:
            failed.append(car)
            print("  FAILED")
        else:
            downloaded.append(car)
            print(f"  OK -> {image_path.name}")

    print("\nDownload summary:")
    print(f"Downloaded: {len(downloaded)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailed cars:")

        for car in failed:
            print(f"- {car.year} {car.make} {car.model}")


if __name__ == "__main__":
    main()