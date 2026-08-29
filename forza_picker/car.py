from dataclasses import dataclass


@dataclass
class Car:
    make: str
    model: str
    year: int

    pi: int
    car_class: str

    country: str
    car_type: str
    
    is_in_autoshow: bool
    dlc: str | None = None

    # For future garage/save-file integration.
    ordinal: int | None = None     