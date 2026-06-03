"""Image handling utilities"""
from pathlib import Path
from PySide6.QtGui import QPixmap, QImage
from utils.constants import SUPPORTED_FORMATS
import logging

logger = logging.getLogger(__name__)


class ImageHandler:
    """Handle image loading and processing"""

    @staticmethod
    def load_image(file_path):
        """Load image from file path"""
        try:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                logger.error(f"Failed to load image: {file_path}")
                return None
            return pixmap
        except Exception as e:
            logger.exception(f"Error loading image: {file_path}")
            return None

    @staticmethod
    def load_image_as_qimage(file_path):
        """Load image as QImage to get format information"""
        try:
            image = QImage(file_path)
            if image.isNull():
                logger.error(f"Failed to load image: {file_path}")
                return None
            return image
        except Exception as e:
            logger.exception(f"Error loading image: {file_path}")
            return None

    @staticmethod
    def get_images_from_folder(folder_path):
        """Get all images from a folder"""
        try:
            folder = Path(folder_path)
            images = []

            for file_path in sorted(folder.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS:
                    images.append(str(file_path))

            return images
        except Exception as e:
            logger.exception(f"Error reading folder: {folder_path}")
            return []

    @staticmethod
    def is_supported_format(file_path):
        """Check if file is a supported image format"""
        return Path(file_path).suffix.lower() in SUPPORTED_FORMATS
