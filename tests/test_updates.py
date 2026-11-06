from dataclasses import replace

import pytest

from forza_picker.car import Car
from forza_picker import updates


@pytest.fixture
def car():
    return Car('Ferrari', 'F40', 1987, 800, 'A', 'Italy', 'Retro Supercars', True)


def test_parse_catalog():
    html = '<table><tr><th>Make</th></tr><tr>' + ''.join(
        f'<td>{v}</td>' for v in ['Ferrari', '1987 Ferrari F40', 'Retro Supercars', '800 A', 'Italy', 'Autoshow', '']
    ) + '</tr></table>'
    cars = updates.parse_catalog(html)
    assert cars[0].model == 'F40'
    assert cars[0].is_in_autoshow


@pytest.mark.parametrize('html', ['unavailable', '<table></table>', '<table><tr><td>bad</td></tr></table>'])
def test_invalid_catalog_rejected(html):
    with pytest.raises(ValueError):
        updates.parse_catalog(html)


def test_snapshot_roundtrip(tmp_path, car):
    path = tmp_path / 'nested/catalog.json'
    updates.save_snapshot(path, [car], {'key': 'photo.png'})
    assert updates.load_snapshot(path) == ([car], {'key': 'photo.png'})
    assert not path.with_suffix('.tmp').exists()


def test_photo_failure_still_saves_catalog(monkeypatch, tmp_path, car):
    new = replace(car, model='New car')
    monkeypatch.setattr(updates, 'fetch_car_list_page', lambda: 'html')
    monkeypatch.setattr(updates, 'parse_catalog', lambda html: [new])
    def unavailable():
        raise RuntimeError('offline')
    monkeypatch.setattr(updates, 'get_fh6_thumbnail_titles', unavailable)
    worker = updates.CatalogUpdateWorker([car], {}, tmp_path / 'catalog.json')
    completed = []
    worker.signals.completed.connect(lambda *args: completed.append(args))
    worker.run()
    assert len(completed) == 1
    assert completed[0][0] == [car, new]
    assert '1 new cars' in completed[0][2]
    assert updates.load_snapshot(tmp_path / 'catalog.json')[0] == [car, new]


def test_failed_fetch_preserves_snapshot(monkeypatch, tmp_path, car):
    path = tmp_path / 'catalog.json'
    updates.save_snapshot(path, [car], {})
    before = path.read_bytes()
    def unavailable():
        raise RuntimeError('offline')
    monkeypatch.setattr(updates, 'fetch_car_list_page', unavailable)
    worker = updates.CatalogUpdateWorker([car], {}, path)
    failures = []
    worker.signals.failed.connect(failures.append)
    worker.run()
    assert failures and 'offline' in failures[0]
    assert path.read_bytes() == before


def test_photo_downloads_and_mapping_are_saved(monkeypatch, tmp_path, car):
    monkeypatch.setattr(updates, 'fetch_car_list_page', lambda: 'html')
    monkeypatch.setattr(updates, 'parse_catalog', lambda html: [car])
    title = 'File:FH6 Ferrari F40.png'
    monkeypatch.setattr(updates, 'get_fh6_thumbnail_titles', lambda: [title])
    requested = []
    def download(value):
        requested.append(value)
        return tmp_path / 'photo.png'
    monkeypatch.setattr(updates, 'get_or_download_wiki_image', download)
    path = tmp_path / 'catalog.json'
    worker = updates.CatalogUpdateWorker([car], {}, path)
    worker.run()
    assert requested == [title]
    assert updates.load_snapshot(path)[1] == {'1987|Ferrari|F40': 'FH6 Ferrari F40.png'}
