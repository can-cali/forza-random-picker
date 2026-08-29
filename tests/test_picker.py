import pytest
from forza_picker.car import Car
from forza_picker.picker import filter_cars, pick_random_car


@pytest.fixture
def cars():
    return [
        Car(
            make="Ferrari",
            model="F40",
            year=1987,
            pi=800,
            car_class="A",
            country="Italy",
            car_type="Retro Supercars",
            is_in_autoshow=True,
        ),
        Car(
            make="Subaru",
            model="Impreza WRX STI",
            year=2005,
            pi=650,
            car_class="B",
            country="Japan",
            car_type="Modern Rally",
            is_in_autoshow=True,
        ),
        Car(
            make="Ferrari",
            model="458 Speciale",
            year=2013,
            pi=768,
            car_class="S1",
            country="Italy",
            car_type="Track Toys",
            is_in_autoshow=True,
        ),
    ]

def test_filter_by_make(cars):
    result = filter_cars(cars, make="Ferrari")

    assert len(result) == 2
    assert result[0].make == "Ferrari"

def test_no_filters_returns_all_cars(cars):
    result = filter_cars(cars)
    assert len(result) == 3


def test_filter_by_class(cars):
    result = filter_cars(cars, car_class="B")

    assert len(result) == 1
    assert result[0].make == "Subaru"    


def test_filter_by_country(cars):
    result = filter_cars(cars, country="Italy")

    assert len(result) == 2
    assert result[0].make == "Ferrari"


def test_filter_by_type(cars):
    result = filter_cars(cars, car_type="Modern Rally")

    assert len(result) == 1
    assert result[0].make == "Subaru"


def test_multiple_filters_are_combined(cars):
    result = filter_cars(cars, make="Ferrari", car_class="S1")

    assert len(result) == 1
    assert result[0].make == "Ferrari"


def test_no_matching_cars_returns_empty_list(cars):
    result = filter_cars(cars, car_type="Retro Rally")

    assert len(result) == 0

def test_pick_random_car_from_empty_list_returns_none():
    result = pick_random_car([])

    assert result is None


def test_pick_random_car_from_single_car_returns_that_car(cars):
    result = pick_random_car([cars[0]])

    assert result == cars[0]


def test_pick_random_car_returns_a_car_from_input(cars):
    result = pick_random_car(cars)

    assert result in cars