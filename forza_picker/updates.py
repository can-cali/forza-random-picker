"""Background catalog updates, stored separately from the bundled catalog."""
import json
import os
from dataclasses import asdict
from pathlib import Path

from bs4 import BeautifulSoup
from PySide6.QtCore import QObject, QRunnable, Signal

from forza_picker.car import Car
from forza_picker.wiki_images import (
    PhotoProviderChallenge, photo_request_scope,
    car_image_key, cache_file_name_from_wiki_title, find_wiki_title_for_car,
    get_base_thumbnail_titles, get_fh6_thumbnail_titles,
    get_or_download_wiki_image, normalize_wiki_title, get_cached_image_path, is_valid_image, candidate_wiki_titles,
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
    def __init__(self, cars, image_map, snapshot_path, photos_only=False):
        super().__init__()
        self.photos_only = photos_only
        self.cars = list(cars)
        self.image_map = dict(image_map)
        self.snapshot_path = snapshot_path
        self.signals = UpdateSignals()

    def run(self):
        with photo_request_scope():
            self._run_update()

    def _run_update(self):
        try:
            self.signals.progress.emit('Checking missing photos…' if self.photos_only else 'Checking the official car list…')
            fetched = [] if self.photos_only else parse_catalog(fetch_car_list_page())
            merged = {car_image_key(car): car for car in self.cars}
            added = sum(car_image_key(car) not in merged for car in fetched)
            merged.update({car_image_key(car): car for car in fetched})
            cars = list(merged.values())
            images = dict(self.image_map)
            report = {"cached": 0, "downloaded": 0, "unmatched": [], "failed": [], "lookup_error": None, "unmatched_attempts": {}, "blocked": [], "blocked_providers": {}}
            missing = []
            for car in cars:
                filename = images.get(car_image_key(car))
                if filename and is_valid_image(get_cached_image_path(filename)):
                    report["cached"] += 1
                else:
                    missing.append(car)
            lookup = {}
            if missing:
                try:
                    self.signals.progress.emit('Looking up missing car photos…')
                    lookup = {normalize_wiki_title(title): title for title in
                              get_base_thumbnail_titles(get_fh6_thumbnail_titles())}
                except PhotoProviderChallenge as exc:
                    report["lookup_error"] = str(exc)
                    report["blocked_providers"][exc.host] = str(exc)
                except Exception as exc:
                    report["lookup_error"] = str(exc)
            for index, car in enumerate(missing, 1):
                key = car_image_key(car)
                if 'static.wikia.nocookie.net' in report['blocked_providers']:
                    report['blocked'].append(key)
                    continue
                # Try the saved filename even when the category API is unavailable.
                titles = []
                if key in images:
                    titles.append(f'File:{images[key]}')
                matched = find_wiki_title_for_car(car, lookup)
                if matched and matched not in titles:
                    titles.append(matched)
                known_titles = set(titles)
                titles.extend(title for title in candidate_wiki_titles(car) if title not in known_titles)
                self.signals.progress.emit(f'Downloading missing photo {index}/{len(missing)}…')
                errors = []
                absent = []
                for title in titles:
                    try:
                        if title in known_titles:
                            path = get_or_download_wiki_image(title)
                        else:
                            path = get_or_download_wiki_image(title, api_fallback=False)
                        if path is None:
                            absent.append(title)
                            continue
                        images[key] = cache_file_name_from_wiki_title(title)
                        report["downloaded"] += 1
                        break
                    except PhotoProviderChallenge as exc:
                        report["blocked_providers"][exc.host] = str(exc)
                        # An API challenge does not imply the CDN is blocked.
                        # A CDN challenge stops all further filename probes.
                        if exc.host == 'static.wikia.nocookie.net':
                            report['blocked'].append(key)
                            break
                        errors.append(str(exc))
                    except Exception as exc:
                        errors.append(f'{title}: {exc}')
                else:
                    if errors:
                        report["failed"].append({"car": key, "errors": errors, "not_found": absent})
                    else:
                        report["unmatched"].append(key)
                        report["unmatched_attempts"][key] = absent
            save_snapshot(self.snapshot_path, cars, images)
            report_path = self.snapshot_path.with_name('photo-report.json')
            message = (f'Catalog updated: {added} new cars. Photos: {report["cached"]} cached, '
                       f'{report["downloaded"]} downloaded, {len(report["unmatched"])} unmatched, '
                       f'{len(report["failed"])} failed, {len(report["blocked"])} blocked.')
            try:
                report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            except OSError as exc:
                message += f' Could not save photo report: {exc}'
            if report['blocked_providers']:
                message = 'Photo provider requires browser verification; requests to challenged hosts stopped. ' + message
            if report["lookup_error"]:
                message += ' Wiki lookup unavailable; existing mappings were still tried.'
            self.signals.completed.emit(cars, images, message)
        except Exception as exc:
            self.signals.failed.emit(f'Update failed. Your existing catalog is unchanged.\n{exc}')
