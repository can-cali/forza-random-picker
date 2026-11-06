from forza_picker.car import Car
from forza_picker.wiki_images import find_wiki_title_for_car
from forza_picker.wiki_images import get_local_car_image_path


def test_find_wiki_title_by_normalized_name():
    car = Car(
        make="Abarth",
        model="595 esseesse",
        year=1968,
        pi=100,
        car_class="D",
        country="Italy",
        car_type="Cult Cars",
        is_in_autoshow=True,
    )

    wiki_lookup = {
        "abarth595esseesse": "File:FH6 Abarth 595 esseesse.png"
    }

    result = find_wiki_title_for_car(car, wiki_lookup)

    assert result == "File:FH6 Abarth 595 esseesse.png"

def test_find_wiki_title_by_alias():
    car = Car(
        make="Mazda",
        model="#55 Mazda 787B",
        year=1991,
        pi=900,
        car_class="S1",
        country="Japan",
        car_type="Race Cars",
        is_in_autoshow=False,
    )

    result = find_wiki_title_for_car(
        car,
        wiki_lookup={},
    )

    assert result == "File:FH6 Mazda 55 787B.png"

def test_find_wiki_title_returns_none_when_unknown():
    car = Car(
        make="Fake",
        model="Imaginary Car",
        year=2026,
        pi=500,
        car_class="B",
        country="Nowhere",
        car_type="Unknown",
        is_in_autoshow=False,
    )

    result = find_wiki_title_for_car(
        car,
        wiki_lookup={},
    )

    assert result is None

def test_get_local_car_image_path_returns_none_when_not_mapped():
    car = Car(
        make="Fake",
        model="Imaginary Car",
        year=2026,
        pi=500,
        car_class="B",
        country="Nowhere",
        car_type="Unknown",
        is_in_autoshow=False,
    )

    result = get_local_car_image_path(
        car,
        image_map={},
    )

    assert result is None

def sample_car():
    return Car('Ferrari', 'F40', 1987, 800, 'A', 'Italy', 'Retro Supercars', True)


def test_year_match_wins_over_generic():
    car = sample_car()
    assert find_wiki_title_for_car(car, {
        'ferrarif40': 'File:generic.png',
        'ferrarif401987': 'File:year.png',
    }) == 'File:year.png'


def test_year_prefix_match():
    assert find_wiki_title_for_car(sample_car(), {
        '1987ferrarif40': 'File:year.png',
    }) == 'File:year.png'


def test_corrupt_cached_image_is_replaced(monkeypatch, tmp_path):
    from forza_picker import wiki_images as images
    monkeypatch.setattr(images, 'IMAGE_CACHE_DIR', tmp_path)
    destination = tmp_path / 'FH6 Ferrari F40.png'
    destination.write_bytes(b'broken')
    monkeypatch.setattr(images, 'get_wiki_image_url', lambda title: 'https://example.com/photo')
    def download(url, path):
        path.write_bytes((__import__('pathlib').Path(__file__).parents[1] / 'assets/car_placeholder.png').read_bytes())
    monkeypatch.setattr(images, 'download_image', download)
    assert images.get_or_download_wiki_image('File:FH6 Ferrari F40.png') == destination
    assert images.is_valid_image(destination)


def test_valid_cache_needs_no_network(monkeypatch, tmp_path):
    from pathlib import Path
    from forza_picker import wiki_images as images
    monkeypatch.setattr(images, 'IMAGE_CACHE_DIR', tmp_path)
    path = tmp_path / 'photo.png'
    path.write_bytes((Path(__file__).parents[1] / 'assets/car_placeholder.png').read_bytes())
    def unexpected(*args):
        raise AssertionError('Network should not be used')
    monkeypatch.setattr(images, 'get_wiki_image_url', unexpected)
    assert images.get_or_download_wiki_image('File:photo.png') == path


def test_download_retries_transient_http_failure(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from pathlib import Path
    from threading import Thread
    from forza_picker import wiki_images as images
    payload = (Path(__file__).parents[1] / 'assets/car_placeholder.png').read_bytes()
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(1)
            self.send_response(503 if len(calls) == 1 else 200)
            self.end_headers()
            self.wfile.write(b'temporary failure' if len(calls) == 1 else payload)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    session = images.http_session()
    adapter = session.get_adapter('https://example.com')
    session.mount('http://127.0.0.1', adapter)
    try:
        path = tmp_path / 'photo.png'
        images.download_image(f'http://127.0.0.1:{server.server_port}/photo', path)
        assert images.is_valid_image(path)
        assert len(calls) == 2
        assert list(tmp_path.iterdir()) == [path]
    finally:
        session.adapters.pop('http://127.0.0.1')
        server.shutdown()
        server.server_close()
        thread.join()


def test_invalid_download_does_not_replace_cache(monkeypatch, tmp_path):
    import pytest
    from forza_picker import wiki_images as images
    class Response:
        content = b'<html>Access denied</html>'
        def raise_for_status(self):
            pass
    class Session:
        def get(self, *args, **kwargs):
            return Response()
    monkeypatch.setattr(images, 'http_session', lambda: Session())
    path = tmp_path / 'photo.png'
    path.write_bytes(b'original')
    with pytest.raises(ValueError, match='unreadable image'):
        images.download_image('https://example.com/photo', path)
    assert path.read_bytes() == b'original'
    assert list(tmp_path.iterdir()) == [path]


def test_worker_emits_completion_when_lookup_fails(monkeypatch):
    from forza_picker import image_worker
    def fail(title):
        raise RuntimeError('API unavailable')
    monkeypatch.setattr(image_worker, 'get_or_download_wiki_image', fail)
    worker = image_worker.ImageDownloadWorker('car', 'File:photo.png')
    finished = []
    worker.signals.image_ready.connect(lambda *args: finished.append(args))
    worker.run()
    assert finished == [('car', None)]


def test_normalization_supports_other_image_formats():
    from forza_picker.wiki_images import normalize_wiki_title
    assert normalize_wiki_title('File:FH6 Ferrari F40.JPG') == 'ferrarif40'
    assert normalize_wiki_title('File:FH6 Ferrari F40.webp') == 'ferrarif40'
