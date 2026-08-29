import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from forza_picker.catalog import load_cars
from forza_picker.main_window import MainWindow


def main():
    base_dir = Path(__file__).resolve().parent
    catalog_path = base_dir / "data" / "cars.json"

    cars = load_cars(catalog_path)

    app = QApplication(sys.argv)

    window = MainWindow(cars)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()