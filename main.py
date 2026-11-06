import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QStandardPaths
from forza_picker.updates import load_snapshot

from forza_picker.catalog import load_cars
from forza_picker.main_window import MainWindow
from forza_picker.wiki_images import load_image_map


def main():
    base_dir = Path(__file__).resolve().parent
    catalog_path = base_dir / "data" / "cars.json"
    image_map_path = base_dir / "data" / "image_map.json"

    cars = load_cars(catalog_path)
    image_map = load_image_map(image_map_path)

    app = QApplication(sys.argv)

    app.setOrganizationName("ForzaRandomPicker")
    app.setApplicationName("ForzaRandomPicker")
    snapshot = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "catalog.json"
    try:
        cars, image_map = load_snapshot(snapshot)
    except (OSError, ValueError, TypeError, KeyError):
        pass  # The bundled catalog remains available if local data is damaged.

    window = MainWindow(cars, image_map)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()