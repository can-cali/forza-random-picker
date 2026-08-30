from forza_picker.car import Car
from forza_picker.wiki_images import find_wiki_title_for_car


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