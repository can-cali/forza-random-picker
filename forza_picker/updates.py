"""Background catalog updates, stored separately from the bundled catalog."""
import json
import os
from dataclasses import asdict
from pathlib import Path

from bs4 import BeautifulSoup
from PySide6.QtCore import QObject, QRunnable, Signal

from forza_picker.car import Car
from forza_picker.wiki_images import (
    car_image_key, cache_file_name_from_wiki_title, find_wiki_title_for_car,
    get_base_thumbnail_titles, get_fh6_thumbnail_titles,
    get_or_download_wiki_image, normalize_wiki_title,
)
from scripts.update_catalog import fetch_car_list_page, parse_car_row


def parse_catalog(html: str) -> list[Car]:
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if table is None:
        raise ValueError('The car list page no longer contains a table.')
    cars = []
    for row in table.find_all('tr'):
        cells = row.find_all('td')
        if not cells:
            continue
        values = [cell.get_text(' ', strip=True) for cell in cells]
        if len(values) != 7:
            raise ValueError('The car list format has changed; existing data was preserved.')
        cars.append(parse_car_row(values))
    if not cars or len({car_image_key(car) for car in cars}) != len(cars):
        raise ValueError('The downloaded car list is empty or contains duplicates.')
    return cars


def save_snapshot(path: Path, cars: list[Car], image_map: dict[str, str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps({'cars': [asdict(car) for car in cars],
                                         'image_map': image_map}, ensure_ascii=False), encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_snapshot(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    cars = [Car(**item) for item in data['cars']]
    images = data['image_map']
    if not cars or not isinstance(images, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in images.items()
    ):
        raise ValueError('Invalid saved catalog')
    return cars, images


class UpdateSignals(QObject):
    progress = Signal(str)
    completed = Signal(object, object, str)
    failed = Signal(str)


class CatalogUpdateWorker(QRunnable):
    def __init__(self, cars, image_map, snapshot_path):
        super().__init__()
        self.cars = list(cars)
        self.image_map = dict(image_map)
        self.snapshot_path = snapshot_path
        self.signals = UpdateSignals()

    def run(self):
        try:
            self.signals.progress.emit('Checking the official car list…')
            fetched = parse_catalog(fetch_car_list_page())
            # A partial upstream list must never silently remove existing cars.
            merged = {car_image_key(car): car for car in self.cars}
            added = sum(car_image_key(car) not in merged for car in fetched)
            merged.update({car_image_key(car): car for car in fetched})
            cars = list(merged.values())
            images = dict(self.image_map)
            warnings = []
            downloaded = 0
            try:
                self.signals.progress.emit('Looking up car photos…')
                lookup = {normalize_wiki_title(title): title for title in
                          get_base_thumbnail_titles(get_fh6_thumbnail_titles())}
                for index, car in enumerate(cars, 1):
                    title = find_wiki_title_for_car(car, lookup)
                    key = car_image_key(car)
                    if title:
                        images[key] = cache_file_name_from_wiki_title(title)
                    elif key in images:
                        title = f'File:{images[key]}'
                    if not title:
                        continue
                    self.signals.progress.emit(f'Checking photo {index}/{len(cars)}…')
                    try:
                        if get_or_download_wiki_image(title) is None:
                            warnings.append(key)
                        else:
                            downloaded += 1
                    except Exception:
                        warnings.append(key)
            except Exception as exc:
                warnings.append(f'Photo lookup unavailable: {exc}')
            save_snapshot(self.snapshot_path, cars, images)
            message = f'Catalog updated: {added} new cars. {downloaded} photos available.'
            if warnings:
                message += f' Photos could not be retrieved for {len(warnings)} requests; you can retry later.'
            self.signals.completed.emit(cars, images, message)
        except Exception as exc:
            self.signals.failed.emit(f'Update failed. Your existing catalog is unchanged.\n{exc}')
