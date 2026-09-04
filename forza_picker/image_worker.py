from PySide6.QtCore import QObject, QRunnable, Signal

from forza_picker.wiki_images import get_or_download_wiki_image


class ImageDownloadSignals(QObject):
    image_ready = Signal(str, object)


class ImageDownloadWorker(QRunnable):
    def __init__(
        self,
        car_key: str,
        wiki_title: str,
    ):
        super().__init__()

        self.car_key = car_key
        self.wiki_title = wiki_title

        self.signals = ImageDownloadSignals()

    def run(self):
        image_path = get_or_download_wiki_image(
            self.wiki_title
        )

        self.signals.image_ready.emit(
            self.car_key,
            image_path,
        )