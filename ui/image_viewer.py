"""Image viewer widget for displaying and manipulating images"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QApplication
from PySide6.QtGui import QPixmap, QPainter, QTransform
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QRect, QSize, QPropertyAnimation, QEasingCurve, QEvent
import logging

logger = logging.getLogger(__name__)


class ImageCanvas(QWidget):
    """Canvas widget for rendering images"""
    
    zoom_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self.pixmap = None
        self.transformed_pixmap = None
        self.zoom_factor = 1.0
        self.target_zoom_factor = 1.0
        self.rotation_angle = 0
        self.pan_offset = QPoint(0, 0)
        self.target_pan_offset = QPoint(0, 0)
        self.is_panning = False
        self.pan_start = QPoint(0, 0)
        self.last_mouse_pos = QPoint(0, 0)
        
        # Animation
        self.zoom_animation = QPropertyAnimation(self, b"zoomFactor")
        self.zoom_animation.setDuration(200)
        self.zoom_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.pan_animation_x = QPropertyAnimation(self, b"panOffsetX")
        self.pan_animation_x.setDuration(200)
        self.pan_animation_x.setEasingCurve(QEasingCurve.OutCubic)
        
        self.pan_animation_y = QPropertyAnimation(self, b"panOffsetY")
        self.pan_animation_y.setDuration(200)
        self.pan_animation_y.setEasingCurve(QEasingCurve.OutCubic)
        
        self.setMinimumSize(QSize(400, 400))
        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)

    @property
    def zoomFactor(self):
        """Get zoom factor for animation"""
        return self.zoom_factor
    
    @zoomFactor.setter
    def zoomFactor(self, value):
        """Set zoom factor for animation"""
        self.zoom_factor = value
        self.update_transformed_pixmap()
        self.update()
        self.zoom_changed.emit(value)
    
    @property
    def panOffsetX(self):
        """Get pan offset X for animation"""
        return self.pan_offset.x()
    
    @panOffsetX.setter
    def panOffsetX(self, value):
        """Set pan offset X for animation"""
        self.pan_offset.setX(int(value))
        self.update()
    
    @property
    def panOffsetY(self):
        """Get pan offset Y for animation"""
        return self.pan_offset.y()
    
    @panOffsetY.setter
    def panOffsetY(self, value):
        """Set pan offset Y for animation"""
        self.pan_offset.setY(int(value))
        self.update()

    def set_image(self, pixmap):
        """Set the image to display"""
        self.pixmap = pixmap
        self.zoom_factor = 1.0
        self.target_zoom_factor = 1.0
        self.rotation_angle = 0
        self.pan_offset = QPoint(0, 0)
        self.target_pan_offset = QPoint(0, 0)
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

    def set_zoom(self, zoom_factor, animate=True, mouse_pos=None):
        """Set zoom level with optional animation and mouse position support"""
        new_zoom = max(0.1, min(zoom_factor, 10.0))
        
        if mouse_pos is None or not animate:
            # Button-based zoom or no animation - zoom from center
            if animate:
                self.zoom_animation.stop()
                self.zoom_animation.setStartValue(self.zoom_factor)
                self.zoom_animation.setEndValue(new_zoom)
                self.zoom_animation.start()
            else:
                self.zoomFactor = new_zoom
            return
        
        # Mouse wheel zoom - zoom from mouse position
        # Calculate the position of the mouse in the image before zoom
        old_zoom = self.zoom_factor
        
        # Stop any ongoing animations
        self.zoom_animation.stop()
        self.pan_animation_x.stop()
        self.pan_animation_y.stop()
        
        # Calculate offset to keep mouse position in same relative position
        canvas_center_x = self.width() / 2
        canvas_center_y = self.height() / 2
        
        # Offset from center in canvas coordinates
        offset_x_canvas = mouse_pos.x() - canvas_center_x
        offset_y_canvas = mouse_pos.y() - canvas_center_y
        
        # Calculate new pan offset
        zoom_ratio = new_zoom / old_zoom
        new_pan_x = self.pan_offset.x() * zoom_ratio + offset_x_canvas * (zoom_ratio - 1)
        new_pan_y = self.pan_offset.y() * zoom_ratio + offset_y_canvas * (zoom_ratio - 1)
        
        # Animate zoom
        self.zoom_animation.setStartValue(self.zoom_factor)
        self.zoom_animation.setEndValue(new_zoom)
        
        # Animate pan offset
        self.pan_animation_x.setStartValue(self.pan_offset.x())
        self.pan_animation_x.setEndValue(int(new_pan_x))
        
        self.pan_animation_y.setStartValue(self.pan_offset.y())
        self.pan_animation_y.setEndValue(int(new_pan_y))
        
        self.zoom_animation.start()
        self.pan_animation_x.start()
        self.pan_animation_y.start()

    def zoom_in(self, animate=True):
        """Zoom in by 20% from center"""
        self.set_zoom(self.zoom_factor * 1.2, animate=animate)

    def zoom_out(self, animate=True):
        """Zoom out by 20% from center"""
        self.set_zoom(self.zoom_factor / 1.2, animate=animate)

    def rotate(self, angle):
        """Rotate image by angle degrees"""
        self.rotation_angle = (self.rotation_angle + angle) % 360
        self.update_transformed_pixmap()
        self.update()

    def fit_to_window(self, animate=True):
        """Fit image to window size"""
        if not self.pixmap:
            return

        # Get current widget size
        widget_size = self.size()
        pixmap_size = self.pixmap.size()

        # Calculate zoom factor
        width_ratio = widget_size.width() / pixmap_size.width()
        height_ratio = widget_size.height() / pixmap_size.height()
        new_zoom = min(width_ratio, height_ratio)

        if animate:
            self.zoom_animation.stop()
            self.pan_animation_x.stop()
            self.pan_animation_y.stop()
            
            self.zoom_animation.setStartValue(self.zoom_factor)
            self.zoom_animation.setEndValue(new_zoom)
            
            self.pan_animation_x.setStartValue(self.pan_offset.x())
            self.pan_animation_x.setEndValue(0)
            
            self.pan_animation_y.setStartValue(self.pan_offset.y())
            self.pan_animation_y.setEndValue(0)
            
            self.zoom_animation.start()
            self.pan_animation_x.start()
            self.pan_animation_y.start()
        else:
            self.zoom_factor = new_zoom
            self.pan_offset = QPoint(0, 0)
            self.update_transformed_pixmap()
            self.update()

    def sizeHint(self):
        """Return preferred size"""
        if self.transformed_pixmap:
            return self.transformed_pixmap.size()
        return QSize(600, 600)

    def paintEvent(self, event):
        """Paint the image on the canvas"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)
        
        if not self.pixmap:
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "No image loaded\nDrag and drop an image here"
            )
            return

        if self.transformed_pixmap:
            # Calculate position to center the image
            x = (self.width() - self.transformed_pixmap.width()) // 2 + self.pan_offset.x()
            y = (self.height() - self.transformed_pixmap.height()) // 2 + self.pan_offset.y()
            painter.drawPixmap(x, y, self.transformed_pixmap)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming with mouse position"""
        self.last_mouse_pos = event.pos()
        
        if event.angleDelta().y() > 0:
            self.zoom_in(animate=True)
        else:
            self.zoom_out(animate=True)
        
        event.accept()

    def mousePressEvent(self, event):
        """Handle mouse press for panning"""
        if event.button() == Qt.LeftButton and self.zoom_factor > 1.0:
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
        if event.button() == Qt.LeftButton:
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignCenter)
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
        self.canvas.fit_to_window(animate=False)

    def fit_to_window(self):
        """Fit image to window"""
        self.canvas.fit_to_window(animate=True)

    def set_zoom(self, zoom_factor):
        """Set zoom level"""
        self.canvas.set_zoom(zoom_factor, animate=False)

    def zoom_in(self):
        """Zoom in"""
        self.canvas.zoom_in(animate=True)

    def zoom_out(self):
        """Zoom out"""
        self.canvas.zoom_out(animate=True)

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
