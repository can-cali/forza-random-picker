import hashlib
from urllib.parse import quote, urlsplit
from contextlib import contextmanager

import os
import tempfile
import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PySide6.QtGui import QImage
from pathlib import Path
import re
import unicodedata
import json
from forza_picker.car import Car
from forza_picker.image_aliases import IMAGE_ALIASES




PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_CACHE_DIR = PROJECT_ROOT / "cache" / "car_images"
FANDOM_API_URL = "https://forza.fandom.com/api.php"


_sessions = threading.local()


def http_session():
    """Reuse connections per worker; retry only transient, idempotent GETs."""
    if not hasattr(_sessions, "session"):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5,
                      status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=frozenset({"GET"}), respect_retry_after_header=True)
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.headers["User-Agent"] = "ForzaRandomPicker/1.0 (desktop car catalog)"
        _sessions.session = session
    return _sessions.session


class PhotoProviderChallenge(RuntimeError):
    """A provider requires browser verification, not another filename guess."""
    def __init__(self, host):
        self.host = host
        super().__init__(f"Photo provider {host} requires browser verification (Cloudflare challenge).")


@contextmanager
def photo_request_scope():
    """A host circuit breaker scoped to one update, not a permanent blacklist."""
    previous = getattr(_sessions, 'blocked_hosts', None)
    _sessions.blocked_hosts = set()
    try:
        yield
    finally:
        if previous is None:
            del _sessions.blocked_hosts
        else:
            _sessions.blocked_hosts = previous


def photo_get(url, **kwargs):
    host = urlsplit(url).hostname
    blocked = getattr(_sessions, 'blocked_hosts', set())
    if host in blocked:
        raise PhotoProviderChallenge(host)
    response = http_session().get(url, **kwargs)
    if getattr(response, 'headers', {}).get('cf-mitigated', '').lower() == 'challenge':
        blocked.add(host)
        raise PhotoProviderChallenge(host)
    return response


def is_valid_image(path: Path) -> bool:
    return path.is_file() and not QImage(str(path)).isNull()


def get_wiki_image_url(file_name: str) -> str | None:
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url",
        "titles": file_name,
    }

    response = photo_get(
        FANDOM_API_URL,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()
    if "error" in data:
        raise ValueError(f"Wiki API error: {data['error']}")

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
        response = photo_get(
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
    title = re.sub(r"\.(png|jpe?g|webp)$", "", title, flags=re.IGNORECASE)

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
    # Explicit exceptions and exact year variants take priority over generic names.
    alias = IMAGE_ALIASES.get(car_alias_key(car))
    if alias:
        return alias
    candidates = (
        normalize_car_name_with_year(car),
        normalize_name(f"{car.year} {car.make} {car.model}"),
        normalize_car_name(car),
    )
    for key in candidates:
        if key in wiki_lookup:
            return wiki_lookup[key]

    return None


def download_image(
    image_url: str,
    destination: Path,
) -> None:
    response = photo_get(
        image_url,
        timeout=15,
    )

    response.raise_for_status()

    if QImage.fromData(response.content).isNull():
        raise ValueError("The server returned an unreadable image")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Each worker owns its temporary file, including when two request the same car.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(response.content)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def get_cached_image_path(file_name: str) -> Path:
    if Path(file_name).name != file_name or "\\" in file_name:
        raise ValueError("Invalid image filename")
    return IMAGE_CACHE_DIR / file_name


def direct_cdn_url(wiki_title: str) -> str:
    """MediaWiki hashes the canonical, UTF-8 filename, before URL encoding."""
    filename = cache_file_name_from_wiki_title(wiki_title).replace(" ", "_")
    digest = hashlib.md5(filename.encode("utf-8"), usedforsecurity=False).hexdigest()
    return (f"https://static.wikia.nocookie.net/forzamotorsport/images/"
            f"{digest[0]}/{digest[:2]}/{quote(filename, safe='')}/revision/latest")


def candidate_wiki_titles(car: Car) -> list[str]:
    """Bounded exact-name variants; never guess a different model or year."""
    name = f"{car.make} {car.model}"
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    names = list(dict.fromkeys([name, plain, plain.replace("#", "").replace("'", "")]))
    titles = []
    for variant in names:
        for label in (f"{variant} {car.year}", variant, f"{car.year} {variant}"):
            title = f"File:FH6 {label}.png"
            # Some wiki names contain slashes; don't construct unsafe local paths.
            filename = cache_file_name_from_wiki_title(title)
            if "/" not in filename and "\\" not in filename:
                titles.append(title)
    return list(dict.fromkeys(titles))


def get_or_download_wiki_image(wiki_title: str, *, api_fallback: bool = True) -> Path | None:
    destination = get_cached_image_path(cache_file_name_from_wiki_title(wiki_title))
    if is_valid_image(destination):
        return destination
    direct_error = None
    try:
        download_image(direct_cdn_url(wiki_title), destination)
        return destination
    except requests.HTTPError as exc:
        if not api_fallback:
            if exc.response is not None and exc.response.status_code == 404:
                return None
            raise
        direct_error = exc
    except (requests.RequestException, ValueError) as exc:
        if not api_fallback:
            raise
        direct_error = exc
    try:
        image_url = get_wiki_image_url(wiki_title)
        if image_url is None:
            return None
        download_image(image_url, destination)
        return destination
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"Direct CDN: {direct_error}; API fallback: {exc}") from exc


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

    if not is_valid_image(image_path):
        return None

    return image_path
