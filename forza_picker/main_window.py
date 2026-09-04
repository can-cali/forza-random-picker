from pathlib import Path

from PySide6.QtCore import (
    QPointF,
    QSignalBlocker,
    QThreadPool,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFontDatabase,
    QLinearGradient,
    QPainter,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from forza_picker.car import Car
from forza_picker.image_worker import ImageDownloadWorker
from forza_picker.picker import filter_cars, pick_random_car
from forza_picker.wiki_images import (
    car_image_key,
    get_local_car_image_path,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_PATH = PROJECT_ROOT / "assets" / "car_placeholder.png"

# FH6-inspired palette. These are intentionally close visual approximations,
# not official Microsoft/Playground design tokens.
HORIZON_TEAL = "#069790"
HORIZON_TEAL_DARK = "#046E70"
HORIZON_PINK = "#F70A82"
HORIZON_CYAN = "#22D6E5"
HORIZON_YELLOW = "#FFE400"
HORIZON_LIME = "#D9FF00"
HORIZON_BLACK = "#0A0A0B"
HORIZON_WHITE = "#F7F7F4"
HORIZON_SOFT_WHITE = "#E9E9E5"
HORIZON_GRAY = "#777774"

PI_CLASS_COLORS = {
    "D": "#22BBD6",
    "C": "#F4C62B",
    "B": "#F18925",
    "A": "#E94B3C",
    "S1": "#B14AC7",
    "S2": "#2877D7",
    "R": "#D637B7",
    "X": "#38A85B",
}


class HorizonBackground(QWidget):
    """Teal geometric background inspired by FH6 menu screens."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#08A49A"))
        gradient.setColorAt(0.55, QColor(HORIZON_TEAL))
        gradient.setColorAt(1.0, QColor(HORIZON_TEAL_DARK))
        painter.fillRect(self.rect(), gradient)

        # Deterministic triangle mesh: gives the flat/geometric Horizon menu feel
        # without bundling any game artwork.
        cell = 92
        rows = self.height() // cell + 2
        cols = self.width() // cell + 2

        for row in range(rows):
            for col in range(cols):
                x = col * cell
                y = row * cell
                alpha = 10 + ((row * 17 + col * 11) % 18)

                if (row + col) % 2 == 0:
                    color = QColor(255, 255, 255, alpha)
                else:
                    color = QColor(0, 34, 36, alpha)

                painter.setBrush(color)
                painter.setPen(Qt.NoPen)

                triangle = QPolygonF(
                    [
                        QPointF(x, y),
                        QPointF(x + cell, y),
                        QPointF(x + cell, y + cell),
                    ]
                )
                painter.drawPolygon(triangle)

        # Horizon-style diagonal accent slash.
        painter.setBrush(QColor(HORIZON_PINK))
        painter.setPen(Qt.NoPen)
        slash_width = 34
        x = self.width() - 118
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(x, 0),
                    QPointF(x + slash_width, 0),
                    QPointF(x - 44, 118),
                    QPointF(x - 44 - slash_width, 118),
                ]
            )
        )

        super().paintEvent(event)


class DlcMultiSelectButton(QToolButton):
    """A compact multi-select DLC picker using a persistent checkbox menu."""

    selectionChanged = Signal()

    def __init__(self, dlc_values: set[str], parent=None):
        super().__init__(parent)

        self.setObjectName("DlcButton")
        self.setPopupMode(QToolButton.InstantPopup)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._updating = False
        self._checkboxes: dict[str | None, QCheckBox] = {}

        self._menu = QMenu(self)
        self._menu.setObjectName("DlcMenu")
        self.setMenu(self._menu)

        panel = QWidget()
        panel.setObjectName("DlcMenuPanel")
        panel.setMinimumWidth(300)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(7)

        title = QLabel("DLC SOURCES")
        title.setObjectName("DlcMenuTitle")
        layout.addWidget(title)

        clear_button = QPushButton("ANY / CLEAR SELECTION")
        clear_button.setObjectName("DlcClearButton")
        clear_button.clicked.connect(self.clear_selection)
        layout.addWidget(clear_button)

        options: list[str | None] = [None]
        options.extend(sorted(dlc_values))

        for value in options:
            text = "BASE GAME / NO DLC" if value is None else value
            checkbox = QCheckBox(text)
            checkbox.setObjectName("DlcCheckBox")
            checkbox.stateChanged.connect(self._on_selection_changed)
            self._checkboxes[value] = checkbox
            layout.addWidget(checkbox)

        action = QWidgetAction(self._menu)
        action.setDefaultWidget(panel)
        self._menu.addAction(action)

        self._update_button_text()

    def selected_values(self) -> set[str | None] | None:
        selected = {
            value
            for value, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        }

        if not selected:
            return None

        return selected

    def clear_selection(self):
        self._updating = True

        try:
            for checkbox in self._checkboxes.values():
                checkbox.setChecked(False)
        finally:
            self._updating = False

        self._update_button_text()
        self.selectionChanged.emit()

    def set_available_options(self, available: set[str | None]) -> bool:
        """Disable impossible options and clear selected options that became invalid."""
        changed = False
        self._updating = True

        try:
            for value, checkbox in self._checkboxes.items():
                is_available = value in available

                if checkbox.isChecked() and not is_available:
                    checkbox.setChecked(False)
                    changed = True

                checkbox.setEnabled(is_available)
        finally:
            self._updating = False

        self._update_button_text()
        return changed

    def _on_selection_changed(self, _state):
        if self._updating:
            return

        self._update_button_text()
        self.selectionChanged.emit()

    def _update_button_text(self):
        selected = self.selected_values()

        if selected is None:
            self.setText("ANY DLC")
            return

        if len(selected) == 1:
            value = next(iter(selected))
            if value is None:
                self.setText("BASE GAME / NO DLC")
            else:
                self.setText(value.upper())
            return

        self.setText(f"{len(selected)} DLC SOURCES SELECTED")


class MainWindow(QMainWindow):
    def __init__(self, cars: list[Car], image_map: dict[str, str]):
        super().__init__()

        self.cars = cars
        self.image_map = image_map
        self._updating_filters = False

        self.current_car_key = None
        self.image_thread_pool = QThreadPool()
        self.image_thread_pool.setMaxThreadCount(3)
        self.downloading_car_keys = set()

        self.ui_font_family = self.resolve_ui_font_family()

        self.setWindowTitle("FH6 Random Car Picker")
        self.resize(1280, 780)
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(self.build_stylesheet())

        self.placeholder_pixmap = QPixmap(str(PLACEHOLDER_PATH))

        self.build_ui()
        self.connect_signals()
        self.update_filter_options()

    @staticmethod
    def resolve_ui_font_family() -> str:
        available = set(QFontDatabase.families())

        # FH6's UI is visually closest to Helvetica. Use it when the user owns
        # and has it installed; otherwise fall back to the Windows-safe Arial.
        for candidate in (
            "Helvetica Neue",
            "Helvetica",
            "Arial",
        ):
            if candidate in available:
                return candidate

        return "Sans Serif"

    def build_ui(self):
        background = HorizonBackground()
        root = QVBoxLayout(background)
        root.setContentsMargins(30, 22, 30, 28)
        root.setSpacing(18)

        root.addLayout(self.build_header())

        content = QHBoxLayout()
        content.setSpacing(22)

        content.addWidget(self.build_filter_panel())
        content.addWidget(self.build_result_panel(), 1)

        root.addLayout(content, 1)
        self.setCentralWidget(background)

    def build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(0)

        horizon_tag = QLabel("HORIZON")
        horizon_tag.setObjectName("HorizonTag")
        horizon_tag.setAlignment(Qt.AlignCenter)

        title = QLabel("RANDOM CAR")
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        subtitle = QLabel("FORZA HORIZON 6  /  CAR PICKER")
        subtitle.setObjectName("AppSubtitle")
        subtitle.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header.addWidget(horizon_tag)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(subtitle)

        return header

    def build_filter_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("FilterPanel")
        panel.setFixedWidth(330)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(8)

        title = QLabel("FILTERS")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        hint = QLabel("NARROW THE RANDOM POOL")
        hint.setObjectName("PanelHint")
        layout.addWidget(hint)
        layout.addSpacing(8)

        self.class_combo = self.create_combo(
            {car.car_class for car in self.cars}
        )
        self.make_combo = self.create_combo(
            {car.make for car in self.cars}
        )
        self.country_combo = self.create_combo(
            {car.country for car in self.cars}
        )
        self.type_combo = self.create_combo(
            {car.car_type for car in self.cars}
        )

        self.add_filter_field(layout, "CLASS", self.class_combo)
        self.add_filter_field(layout, "MANUFACTURER", self.make_combo)
        self.add_filter_field(layout, "COUNTRY", self.country_combo)
        self.add_filter_field(layout, "CAR TYPE", self.type_combo)

        autoshow_label = QLabel("AUTOSHOW")
        autoshow_label.setObjectName("FilterLabel")
        layout.addWidget(autoshow_label)

        autoshow_row = QHBoxLayout()
        autoshow_row.setSpacing(5)

        self.autoshow_group = QButtonGroup(self)
        self.autoshow_group.setExclusive(True)

        self.autoshow_any_button = self.create_autoshow_button("ANY")
        self.autoshow_yes_button = self.create_autoshow_button("YES")
        self.autoshow_no_button = self.create_autoshow_button("NO")

        self.autoshow_group.addButton(self.autoshow_any_button, 0)
        self.autoshow_group.addButton(self.autoshow_yes_button, 1)
        self.autoshow_group.addButton(self.autoshow_no_button, 2)
        self.autoshow_any_button.setChecked(True)

        autoshow_row.addWidget(self.autoshow_any_button)
        autoshow_row.addWidget(self.autoshow_yes_button)
        autoshow_row.addWidget(self.autoshow_no_button)
        layout.addLayout(autoshow_row)

        layout.addSpacing(4)

        dlc_label = QLabel("DLC")
        dlc_label.setObjectName("FilterLabel")
        layout.addWidget(dlc_label)

        dlc_values = {
            car.dlc
            for car in self.cars
            if car.dlc is not None
        }
        self.dlc_filter = DlcMultiSelectButton(dlc_values)
        layout.addWidget(self.dlc_filter)

        layout.addStretch(1)

        self.reset_button = QPushButton("RESET FILTERS")
        self.reset_button.setObjectName("ResetButton")
        layout.addWidget(self.reset_button)

        self.pick_button = QPushButton("PICK RANDOM CAR")
        self.pick_button.setObjectName("PickButton")
        self.pick_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.pick_button)

        return panel

    def build_result_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ResultPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hero = QFrame()
        hero.setObjectName("HeroArea")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 22, 28, 18)
        hero_layout.setSpacing(6)

        hero_top = QHBoxLayout()
        hero_top.addStretch(1)

        self.pi_label = QLabel("—")
        self.pi_label.setObjectName("PiBadge")
        self.pi_label.setAlignment(Qt.AlignCenter)
        self.pi_label.setFixedSize(120, 52)
        hero_top.addWidget(self.pi_label)

        hero_layout.addLayout(hero_top)

        self.image_label = QLabel()
        self.image_label.setObjectName("CarImage")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(390)
        self.image_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        hero_layout.addWidget(self.image_label, 1)

        info = QFrame()
        info.setObjectName("InfoCard")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(30, 20, 30, 24)
        info_layout.setSpacing(5)

        self.name_label = QLabel("NO CAR SELECTED")
        self.name_label.setObjectName("CarName")
        self.name_label.setWordWrap(True)

        self.type_label = QLabel("PICK A RANDOM CAR TO BEGIN")
        self.type_label.setObjectName("CarType")

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("CarMeta")

        self.dlc_label = QLabel("")
        self.dlc_label.setObjectName("DlcMeta")

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.type_label)
        info_layout.addSpacing(6)
        info_layout.addWidget(self.meta_label)
        info_layout.addWidget(self.dlc_label)

        layout.addWidget(hero, 1)
        layout.addWidget(info)

        self.show_placeholder()
        self.set_pi_badge(None, None)

        return panel

    def connect_signals(self):
        self.pick_button.clicked.connect(self.pick_car)
        self.reset_button.clicked.connect(self.reset_filters)

        for combo in (
            self.class_combo,
            self.make_combo,
            self.country_combo,
            self.type_combo,
        ):
            combo.currentTextChanged.connect(self.update_filter_options)

        for button in (
            self.autoshow_any_button,
            self.autoshow_yes_button,
            self.autoshow_no_button,
        ):
            button.clicked.connect(self.update_filter_options)

        self.dlc_filter.selectionChanged.connect(
            self.update_filter_options
        )

    def create_combo(self, options: set[str]) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("FilterCombo")
        combo.addItem("Any")
        combo.addItems(sorted(options))
        combo.setMinimumHeight(43)
        return combo

    @staticmethod
    def create_autoshow_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("AutoshowButton")
        button.setCheckable(True)
        button.setMinimumHeight(40)
        return button

    @staticmethod
    def add_filter_field(
        layout: QVBoxLayout,
        label_text: str,
        widget: QWidget,
    ):
        label = QLabel(label_text)
        label.setObjectName("FilterLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        layout.addSpacing(4)

    def pick_car(self):
        selected_class = self.combo_value(self.class_combo)
        selected_make = self.combo_value(self.make_combo)
        selected_country = self.combo_value(self.country_combo)
        selected_type = self.combo_value(self.type_combo)
        selected_autoshow = self.autoshow_value()
        selected_dlcs = self.dlc_filter.selected_values()

        filtered_cars = filter_cars(
            self.cars,
            car_class=selected_class,
            make=selected_make,
            country=selected_country,
            car_type=selected_type,
            is_in_autoshow=selected_autoshow,
            dlcs=selected_dlcs,
        )

        car = pick_random_car(filtered_cars)

        if car is None:
            self.current_car_key = None
            self.set_pi_badge(None, None)
            self.name_label.setText("NO MATCHING CARS")
            self.type_label.setText("CHANGE OR RESET YOUR FILTERS")
            self.meta_label.setText("")
            self.dlc_label.setText("")
            self.show_placeholder()
            return

        self.set_pi_badge(car.car_class, car.pi)
        self.name_label.setText(
            f"{car.year} {car.make} {car.model}".upper()
        )
        self.type_label.setText(car.car_type.upper())

        autoshow_text = (
            "AUTOSHOW"
            if car.is_in_autoshow
            else "NOT IN AUTOSHOW"
        )
        self.meta_label.setText(
            f"{car.country.upper()}   •   {autoshow_text}"
        )

        if car.dlc is None:
            self.dlc_label.setText("BASE GAME / NO DLC REQUIRED")
        else:
            self.dlc_label.setText(f"DLC  /  {car.dlc.upper()}")

        current_key = car_image_key(car)
        self.current_car_key = current_key

        image_path = get_local_car_image_path(
            car,
            self.image_map,
        )

        if image_path is None:
            self.show_placeholder()

            file_name = self.image_map.get(current_key)

            if file_name is not None:
                wiki_title = f"File:{file_name}"
                self.start_image_download(
                    current_key,
                    wiki_title,
                )
        else:
            self.show_image(image_path)

    def combo_value(self, combo: QComboBox) -> str | None:
        value = combo.currentText()

        if value == "Any":
            return None

        return value

    def autoshow_value(self) -> bool | None:
        checked_id = self.autoshow_group.checkedId()

        if checked_id == 1:
            return True

        if checked_id == 2:
            return False

        return None

    def set_combo_options(
        self,
        combo: QComboBox,
        options: set[str],
    ) -> bool:
        current_value = combo.currentText()
        changed = False

        blocker = QSignalBlocker(combo)

        combo.clear()
        combo.addItem("Any")
        combo.addItems(sorted(options))

        if current_value in options:
            combo.setCurrentText(current_value)
        elif current_value != "Any":
            changed = True

        del blocker
        return changed

    def set_autoshow_availability(
        self,
        available_values: set[bool],
    ) -> bool:
        current = self.autoshow_value()
        changed = False

        self.autoshow_yes_button.setEnabled(True in available_values)
        self.autoshow_no_button.setEnabled(False in available_values)

        if current is not None and current not in available_values:
            blockers = [
                QSignalBlocker(self.autoshow_any_button),
                QSignalBlocker(self.autoshow_yes_button),
                QSignalBlocker(self.autoshow_no_button),
            ]
            self.autoshow_any_button.setChecked(True)
            changed = True
            del blockers

        return changed

    def update_filter_options(self, _=None):
        if self._updating_filters:
            return

        self._updating_filters = True

        try:
            # A few deterministic passes let dependent filters settle if a
            # previously-selected option becomes impossible and is cleared.
            for _pass in range(4):
                selected_class = self.combo_value(self.class_combo)
                selected_make = self.combo_value(self.make_combo)
                selected_country = self.combo_value(self.country_combo)
                selected_type = self.combo_value(self.type_combo)
                selected_autoshow = self.autoshow_value()
                selected_dlcs = self.dlc_filter.selected_values()

                changed = False

                country_cars = filter_cars(
                    self.cars,
                    car_class=selected_class,
                    make=selected_make,
                    car_type=selected_type,
                    is_in_autoshow=selected_autoshow,
                    dlcs=selected_dlcs,
                )
                changed |= self.set_combo_options(
                    self.country_combo,
                    {car.country for car in country_cars},
                )

                make_cars = filter_cars(
                    self.cars,
                    car_class=selected_class,
                    country=selected_country,
                    car_type=selected_type,
                    is_in_autoshow=selected_autoshow,
                    dlcs=selected_dlcs,
                )
                changed |= self.set_combo_options(
                    self.make_combo,
                    {car.make for car in make_cars},
                )

                class_cars = filter_cars(
                    self.cars,
                    country=selected_country,
                    make=selected_make,
                    car_type=selected_type,
                    is_in_autoshow=selected_autoshow,
                    dlcs=selected_dlcs,
                )
                changed |= self.set_combo_options(
                    self.class_combo,
                    {car.car_class for car in class_cars},
                )

                type_cars = filter_cars(
                    self.cars,
                    car_class=selected_class,
                    country=selected_country,
                    make=selected_make,
                    is_in_autoshow=selected_autoshow,
                    dlcs=selected_dlcs,
                )
                changed |= self.set_combo_options(
                    self.type_combo,
                    {car.car_type for car in type_cars},
                )

                autoshow_cars = filter_cars(
                    self.cars,
                    car_class=selected_class,
                    country=selected_country,
                    car_type=selected_type,
                    make=selected_make,
                    dlcs=selected_dlcs,
                )
                changed |= self.set_autoshow_availability(
                    {car.is_in_autoshow for car in autoshow_cars}
                )

                dlc_cars = filter_cars(
                    self.cars,
                    car_class=selected_class,
                    country=selected_country,
                    car_type=selected_type,
                    make=selected_make,
                    is_in_autoshow=selected_autoshow,
                )
                changed |= self.dlc_filter.set_available_options(
                    {car.dlc for car in dlc_cars}
                )

                if not changed:
                    break
        finally:
            self._updating_filters = False

    def reset_filters(self):
        blockers = [
            QSignalBlocker(self.class_combo),
            QSignalBlocker(self.make_combo),
            QSignalBlocker(self.country_combo),
            QSignalBlocker(self.type_combo),
            QSignalBlocker(self.autoshow_any_button),
            QSignalBlocker(self.autoshow_yes_button),
            QSignalBlocker(self.autoshow_no_button),
        ]

        self.class_combo.setCurrentText("Any")
        self.make_combo.setCurrentText("Any")
        self.country_combo.setCurrentText("Any")
        self.type_combo.setCurrentText("Any")
        self.autoshow_any_button.setChecked(True)

        del blockers

        self.dlc_filter.clear_selection()
        self.update_filter_options()

    def set_pi_badge(
        self,
        car_class: str | None,
        pi: int | None,
    ):
        if car_class is None or pi is None:
            self.pi_label.setText("—")
            color = HORIZON_BLACK
        else:
            self.pi_label.setText(f"{car_class}  {pi}")
            color = PI_CLASS_COLORS.get(
                car_class.upper(),
                HORIZON_BLACK,
            )

        self.pi_label.setStyleSheet(
            f"""
            QLabel#PiBadge {{
                background-color: {color};
                color: white;
                border: 3px solid {HORIZON_WHITE};
                font-family: \"{self.ui_font_family}\";
                font-size: 22px;
                font-weight: 900;
                padding: 2px 8px;
            }}
            """
        )

    def show_placeholder(self):
        if self.placeholder_pixmap.isNull():
            self.image_label.clear()
            return

        pixmap = self.placeholder_pixmap.scaled(
            720,
            390,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(pixmap)

    def show_image(self, image_path):
        pixmap = QPixmap(str(image_path))

        if pixmap.isNull():
            self.show_placeholder()
            return

        pixmap = pixmap.scaled(
            760,
            410,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(pixmap)

    def start_image_download(
        self,
        car_key: str,
        wiki_title: str,
    ):
        if car_key in self.downloading_car_keys:
            return

        self.downloading_car_keys.add(car_key)

        worker = ImageDownloadWorker(
            car_key,
            wiki_title,
        )

        worker.signals.image_ready.connect(
            self.handle_downloaded_image
        )

        self.image_thread_pool.start(worker)

    def handle_downloaded_image(
        self,
        car_key: str,
        image_path,
    ):
        self.downloading_car_keys.discard(car_key)

        if image_path is None:
            return

        if car_key != self.current_car_key:
            return

        self.show_image(image_path)

    def build_stylesheet(self) -> str:
        font = self.ui_font_family

        return f"""
        QMainWindow {{
            background: {HORIZON_TEAL};
        }}

        QWidget {{
            font-family: \"{font}\";
        }}

        QLabel#HorizonTag {{
            background: {HORIZON_PINK};
            color: white;
            font-size: 17px;
            font-weight: 900;
            padding: 7px 13px 6px 13px;
        }}

        QLabel#AppTitle {{
            background: {HORIZON_BLACK};
            color: white;
            font-size: 29px;
            font-weight: 900;
            padding: 4px 18px 5px 14px;
        }}

        QLabel#AppSubtitle {{
            color: white;
            font-size: 12px;
            font-weight: 800;
            padding-right: 4px;
        }}

        QFrame#FilterPanel {{
            background-color: rgba(8, 12, 13, 235);
            border: none;
        }}

        QLabel#PanelTitle {{
            color: white;
            font-size: 31px;
            font-weight: 900;
        }}

        QLabel#PanelHint {{
            color: {HORIZON_CYAN};
            font-size: 11px;
            font-weight: 800;
        }}

        QLabel#FilterLabel {{
            color: {HORIZON_SOFT_WHITE};
            font-size: 11px;
            font-weight: 900;
            padding-top: 4px;
        }}

        QComboBox#FilterCombo {{
            background: {HORIZON_WHITE};
            color: {HORIZON_BLACK};
            border: 3px solid {HORIZON_WHITE};
            border-radius: 0px;
            padding: 7px 12px;
            font-size: 14px;
            font-weight: 800;
        }}

        QComboBox#FilterCombo:hover,
        QComboBox#FilterCombo:focus {{
            border: 3px solid {HORIZON_LIME};
        }}

        QComboBox#FilterCombo::drop-down {{
            border: none;
            width: 28px;
        }}

        QComboBox#FilterCombo QAbstractItemView {{
            background: {HORIZON_WHITE};
            color: {HORIZON_BLACK};
            border: 2px solid {HORIZON_BLACK};
            selection-background-color: {HORIZON_BLACK};
            selection-color: white;
            padding: 3px;
            outline: none;
            font-weight: 700;
        }}

        QPushButton#AutoshowButton {{
            background: {HORIZON_WHITE};
            color: {HORIZON_BLACK};
            border: 2px solid {HORIZON_WHITE};
            border-radius: 0px;
            font-size: 12px;
            font-weight: 900;
            padding: 7px 5px;
        }}

        QPushButton#AutoshowButton:hover {{
            border: 2px solid {HORIZON_LIME};
        }}

        QPushButton#AutoshowButton:checked {{
            background: {HORIZON_BLACK};
            color: white;
            border: 2px solid {HORIZON_LIME};
        }}

        QPushButton#AutoshowButton:disabled {{
            background: #555555;
            color: #8D8D8D;
            border: 2px solid #555555;
        }}

        QToolButton#DlcButton {{
            background: {HORIZON_WHITE};
            color: {HORIZON_BLACK};
            border: 3px solid {HORIZON_WHITE};
            border-radius: 0px;
            min-height: 27px;
            padding: 7px 12px;
            text-align: left;
            font-size: 12px;
            font-weight: 900;
        }}

        QToolButton#DlcButton:hover {{
            border: 3px solid {HORIZON_LIME};
        }}

        QMenu#DlcMenu {{
            background: {HORIZON_BLACK};
            border: 2px solid {HORIZON_LIME};
            padding: 0px;
        }}

        QWidget#DlcMenuPanel {{
            background: {HORIZON_BLACK};
        }}

        QLabel#DlcMenuTitle {{
            color: {HORIZON_CYAN};
            font-size: 11px;
            font-weight: 900;
        }}

        QCheckBox#DlcCheckBox {{
            color: white;
            font-size: 12px;
            font-weight: 700;
            spacing: 9px;
            min-height: 23px;
        }}

        QCheckBox#DlcCheckBox:disabled {{
            color: #5C5C5C;
        }}

        QCheckBox#DlcCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 2px solid white;
            background: transparent;
        }}

        QCheckBox#DlcCheckBox::indicator:checked {{
            background: {HORIZON_LIME};
            border: 2px solid {HORIZON_LIME};
        }}

        QPushButton#DlcClearButton {{
            background: {HORIZON_CYAN};
            color: {HORIZON_BLACK};
            border: none;
            border-radius: 0px;
            padding: 7px 8px;
            font-size: 11px;
            font-weight: 900;
        }}

        QPushButton#ResetButton {{
            background: transparent;
            color: white;
            border: 2px solid white;
            border-radius: 0px;
            min-height: 34px;
            font-size: 12px;
            font-weight: 900;
        }}

        QPushButton#ResetButton:hover {{
            color: {HORIZON_BLACK};
            background: white;
            border: 2px solid {HORIZON_LIME};
        }}

        QPushButton#PickButton {{
            background: {HORIZON_PINK};
            color: white;
            border: 3px solid {HORIZON_PINK};
            border-radius: 0px;
            min-height: 49px;
            font-size: 17px;
            font-weight: 900;
        }}

        QPushButton#PickButton:hover {{
            border: 3px solid {HORIZON_LIME};
        }}

        QPushButton#PickButton:pressed {{
            background: {HORIZON_CYAN};
            color: {HORIZON_BLACK};
            border: 3px solid {HORIZON_LIME};
        }}

        QFrame#ResultPanel {{
            background: transparent;
            border: none;
        }}

        QFrame#HeroArea {{
            background-color: rgba(0, 75, 75, 95);
            border: 1px solid rgba(255, 255, 255, 28);
        }}

        QLabel#CarImage {{
            background: transparent;
            border: none;
        }}

        QFrame#InfoCard {{
            background: {HORIZON_WHITE};
            border: none;
        }}

        QLabel#CarName {{
            color: {HORIZON_BLACK};
            font-size: 30px;
            font-weight: 900;
        }}

        QLabel#CarType {{
            color: {HORIZON_GRAY};
            font-size: 15px;
            font-weight: 800;
        }}

        QLabel#CarMeta {{
            color: {HORIZON_BLACK};
            font-size: 13px;
            font-weight: 800;
        }}

        QLabel#DlcMeta {{
            color: {HORIZON_PINK};
            font-size: 12px;
            font-weight: 900;
        }}
        """
