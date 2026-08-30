from pathlib import Path
from difflib import get_close_matches

from forza_picker.catalog import load_cars
from forza_picker.wiki_images import (
    get_fh6_thumbnail_titles,
    get_base_thumbnail_titles,
    normalize_car_name,
    normalize_car_name_with_year,
    normalize_wiki_title,
    find_wiki_title_for_car
)
from forza_picker.image_aliases import IMAGE_ALIASES
from forza_picker.wiki_images import car_alias_key


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

    matched = []
    unmatched = []

    for car in cars:
        title = find_wiki_title_for_car(car, wiki_lookup)

        if title is not None:
            matched.append(car)
        else:
            unmatched.append(car)

    print(f"Catalog cars: {len(cars)}")
    print(f"Wiki thumbnails: {len(base_thumbnails)}")
    print(f"Matched: {len(matched)}")
    print(f"Unmatched: {len(unmatched)}")

    print("\nUnmatched cars:")

    print("\nPossible matches for unmatched cars:")

    for car in unmatched:
        key = normalize_car_name(car)

        candidates = get_close_matches(
            key,
            wiki_lookup.keys(),
            n=3,
            cutoff = 0.5,
        )

        print()
        print(f"{car.year} {car.make} {car.model}")

        for candidate in candidates:
            print(f"  -> {wiki_lookup[candidate]}")


if __name__ == "__main__":
    main()