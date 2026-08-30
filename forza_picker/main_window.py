from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from forza_picker.car import Car
from forza_picker.picker import filter_cars, pick_random_car

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_PATH = PROJECT_ROOT / "assets" / "car_placeholder.png"



class MainWindow(QMainWindow):
    def __init__(self, cars: list[Car]):
        super().__init__()

        self.cars = cars

        self.setWindowTitle("Forza Random Car Picker")
        self.resize(500, 300)

        # Car Image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        placeholder_pixmap = QPixmap(str(PLACEHOLDER_PATH))
        placeholder_pixmap = placeholder_pixmap.scaled(
            500,
            280,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.image_label.setPixmap(placeholder_pixmap)

        # PI image
        self.pi_label = QLabel("-")
        self.pi_label.setAlignment(Qt.AlignCenter)

        # Name
        self.name_label = QLabel("No car selected")
        self.name_label.setAlignment(Qt.AlignCenter)

        # Car Type
        self.type_label = QLabel("")
        self.type_label.setAlignment(Qt.AlignCenter)

        # Class Selector
        self.class_combo = QComboBox()
        self.class_combo.addItem("Any")
        self.class_combo.addItems(
            sorted({car.car_class for car in cars})
        )

        # Manufacturer Selector
        self.make_combo = QComboBox()
        self.make_combo.addItem("Any")
        self.make_combo.addItems(
            sorted({car.make for car in cars})
        )

        # Country Selector
        self.country_combo = QComboBox()
        self.country_combo.addItem("Any")
        self.country_combo.addItems(
            sorted({car.country for car in cars})
        )

        # Car Type Selector
        self.type_combo = QComboBox()
        self.type_combo.addItem("Any")
        self.type_combo.addItems(
            sorted({car.car_type for car in cars})
        )
        '''
        self.make_combo.currentTextChanged.connect(
            self.on_make_changed
        )

        self.country_combo.currentTextChanged.connect(
            self.on_country_changed
        )
        '''
        self.pick_button = QPushButton("Pick Random Car")
        self.result_label = QLabel("No car selected")

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.pi_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.type_label)
        layout.addWidget(self.class_combo)
        layout.addWidget(self.make_combo)
        layout.addWidget(self.country_combo)
        layout.addWidget(self.type_combo)
        layout.addWidget(self.pick_button)
        layout.addWidget(self.result_label)
        

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

        self.pick_button.clicked.connect(self.pick_car)

        self.class_combo.currentTextChanged.connect(
            self.update_filter_options
        )

        self.make_combo.currentTextChanged.connect(
            self.update_filter_options
        )

        self.country_combo.currentTextChanged.connect(
            self.update_filter_options
        )

        self.type_combo.currentTextChanged.connect(
            self.update_filter_options
        )

    ''' # Disable country selection when a car manufacturer is already selected.
    def on_make_changed(self, selected_make: str):
        if selected_make == "Any":
            self.country_combo.setEnabled(True)
        else:
            self.country_combo.setCurrentText("Any")
            self.country_combo.setEnabled(False)
            '''
   
    ''' # Disable manufacturer selection when a Country is already selected. (might need improvement)
    def on_country_changed(self, selected_country: str):
            if selected_country == "Any":
                self.make_combo.setEnabled(True)
            else:
                self.make_combo.setCurrentText("Any")
                self.make_combo.setEnabled(False)
            '''
    def pick_car(self):
        selected_class = self.combo_value(self.class_combo)
        selected_make = self.combo_value(self.make_combo)
        selected_country = self.combo_value(self.country_combo)
        selected_type = self.combo_value(self.type_combo)

        filtered_cars = filter_cars(
            self.cars,
            car_class=selected_class,
            make=selected_make,
            country=selected_country,
            car_type=selected_type,
        )

        car = pick_random_car(filtered_cars)

        if car is None:
            self.pi_label.setText("-")
            self.name_label.setText("No matching cars found.")
            self.type_label.setText("")
            return

        self.pi_label.setText(
            f"{car.car_class} {car.pi}"
        )

        self.name_label.setText(
            f"{car.year} {car.make} {car.model}"
        )

        self.type_label.setText(
            car.car_type
        )

    # helper to not repeat combos for every filter 
    def combo_value(self, combo: QComboBox) -> str | None:
        value = combo.currentText()

        if value == "Any":
            return None

        return value
    
    def set_combo_options(
            self,
            combo: QComboBox,
            options: set[str],
            ):
        current_value = combo.currentText()

        blocker = QSignalBlocker(combo)

        combo.clear()
        combo.addItem("Any")
        combo.addItems(sorted(options))

        if current_value in options:
            combo.setCurrentText(current_value)

    def update_filter_options(self, _=None):
        selected_class = self.combo_value(self.class_combo)
        selected_make = self.combo_value(self.make_combo)
        selected_country = self.combo_value(self.country_combo)
        selected_type = self.combo_value(self.type_combo)

        # Countries available given every OTHER filter
        country_cars = filter_cars(
            self.cars,
            car_class=selected_class,
            make=selected_make,
            car_type=selected_type,
        )

        available_countries = {
            car.country for car in country_cars
        }

        self.set_combo_options(
            self.country_combo,
            available_countries,
        )

        # Update make options
        make_cars = filter_cars(
            self.cars,
            car_class=selected_class,
            country=selected_country,
            car_type=selected_type,
        )

        available_makes = {
            car.make for car in make_cars
        }

        self.set_combo_options(
            self.make_combo,
            available_makes,
        )

        # Update class options
        class_cars = filter_cars(
            self.cars,
            country=selected_country,
            make=selected_make,
            car_type=selected_type,
        )

        available_classes = {
            car.car_class for car in class_cars
        }

        self.set_combo_options(
            self.class_combo,
            available_classes,
        )

        # Update type options
        type_cars = filter_cars(
            self.cars,
            car_class=selected_class,
            country=selected_country,
            make=selected_make,
        )

        available_types = {
            car.car_type for car in type_cars
        }

        self.set_combo_options(
            self.type_combo,
            available_types
        )