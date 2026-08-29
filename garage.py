from pathlib import Path
import re


CAR_PATTERN = re.compile(r"BaseLivery_(\d+)_", re.IGNORECASE)  #Owned cars are being fetched with this filter


def get_owned_car_ids(save_folder: str) -> set[int]:
    save_path = Path(save_folder)

    if not save_path.exists():
        raise FileNotFoundError(f"Save folder not found: {save_folder}")

    owned_ids = set()

    for item in save_path.rglob("*"):
        match = CAR_PATTERN.search(item.name)

        if match:
            car_id = int(match.group(1))
            owned_ids.add(car_id)

    return owned_ids