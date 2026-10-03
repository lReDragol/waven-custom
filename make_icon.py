"""Render our own simple icon for packaging."""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PIL import Image
from app import app_icon

application=QApplication([])
directory=Path(__file__).parent/'assets'
directory.mkdir(exist_ok=True)
image_path=directory/'waven-custom.png'
app_icon().pixmap(64,64).save(str(image_path))
with Image.open(image_path) as icon:
    icon.save(directory/'waven-custom.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64)])
