import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

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

    window = MainWindow(cars, image_map)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()