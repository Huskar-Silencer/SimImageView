"""Image viewer widget for displaying and manipulating images"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QApplication
from PySide6.QtGui import QPixmap, QPainter, QTransform
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QRect
import logging

logger = logging.getLogger(__name__)


class ImageCanvas(QWidget):
    """Canvas widget for rendering images"""

    def __init__(self):
        super().__init__()
        self.pixmap = None
        self.transformed_pixmap = None
        self.zoom_factor = 1.0
        self.rotation_angle = 0
        self.pan_offset = QPoint(0, 0)
        self.is_panning = False
        self.pan_start = QPoint(0, 0)

        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)

    def set_image(self, pixmap):
        """Set the image to display"""
        self.pixmap = pixmap
        self.zoom_factor = 1.0
        self.rotation_angle = 0
        self.pan_offset = QPoint(0, 0)
        self.update_transformed_pixmap()
        self.update()

    def update_transformed_pixmap(self):
        """Update the transformed pixmap based on zoom and rotation"""
        if not self.pixmap:
            return

        # Apply rotation
        transform = QTransform()
        transform.rotate(self.rotation_angle)
        rotated = self.pixmap.transformed(transform, Qt.SmoothTransformation)

        # Apply zoom
        new_size = rotated.size() * self.zoom_factor
        self.transformed_pixmap = rotated.scaledToWidth(
            max(int(new_size.width()), 1),
            Qt.SmoothTransformation
        )

    def set_zoom(self, zoom_factor):
        """Set zoom level"""
        self.zoom_factor = max(0.1, min(zoom_factor, 10.0))
        self.update_transformed_pixmap()
        self.update()

    def zoom_in(self):
        """Zoom in by 20%"""
        self.set_zoom(self.zoom_factor * 1.2)

    def zoom_out(self):
        """Zoom out by 20%"""
        self.set_zoom(self.zoom_factor / 1.2)

    def rotate(self, angle):
        """Rotate image by angle degrees"""
        self.rotation_angle = (self.rotation_angle + angle) % 360
        self.update_transformed_pixmap()
        self.update()

    def fit_to_window(self):
        """Fit image to window size"""
        if not self.pixmap:
            return

        # Get current widget size
        widget_size = self.size()
        pixmap_size = self.pixmap.size()

        # Calculate zoom factor
        width_ratio = widget_size.width() / pixmap_size.width()
        height_ratio = widget_size.height() / pixmap_size.height()
        self.zoom_factor = min(width_ratio, height_ratio)

        self.pan_offset = QPoint(0, 0)
        self.update_transformed_pixmap()
        self.update()

    def paintEvent(self, event):
        """Paint the image on the canvas"""
        if not self.transformed_pixmap:
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.gray)
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "No image loaded\nDrag and drop an image here"
            )
            return

        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)

        # Calculate position to center the image
        x = (self.width() - self.transformed_pixmap.width()) // 2 + self.pan_offset.x()
        y = (self.height() - self.transformed_pixmap.height()) // 2 + self.pan_offset.y()

        painter.drawPixmap(x, y, self.transformed_pixmap)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def mousePressEvent(self, event):
        """Handle mouse press for panning"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        """Handle mouse move for panning"""
        if self.is_panning:
            delta = event.pos() - self.pan_start
            self.pan_offset += delta
            self.pan_start = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release for panning"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)

    def copy_to_clipboard(self):
        """Copy the current pixmap to clipboard"""
        if self.pixmap:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.pixmap)


class ImageViewerWidget(QWidget):
    """Main image viewer widget"""

    image_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.canvas = ImageCanvas()
        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(False)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #f0f0f0;
                border: none;
            }
        """)

        layout.addWidget(scroll_area)
        self.setLayout(layout)

    def set_image(self, pixmap):
        """Set image to display"""
        self.canvas.set_image(pixmap)
        self.canvas.fit_to_window()

    def fit_to_window(self):
        """Fit image to window"""
        self.canvas.fit_to_window()

    def set_zoom(self, zoom_factor):
        """Set zoom level"""
        self.canvas.set_zoom(zoom_factor)

    def zoom_in(self):
        """Zoom in"""
        self.canvas.zoom_in()

    def zoom_out(self):
        """Zoom out"""
        self.canvas.zoom_out()

    def rotate(self, angle):
        """Rotate image"""
        self.canvas.rotate(angle)

    def copy_to_clipboard(self):
        """Copy image to clipboard"""
        self.canvas.copy_to_clipboard()

    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle drop event"""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.image_dropped.emit(file_path)
