from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QRectF, Qt, Signal, QVariantAnimation
from PySide6.QtGui import (
    QColor,
    QIcon,
    QImageReader,
    QPainter,
    QPixmap,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QStyle,
)


class GraphView(QGraphicsView):
    pass


class ImageCanvas(GraphView):
    """Image viewport with zoom, pan and rotation support."""

    zoom_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem()
        self._pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self._scene.addItem(self._pixmap_item)
        self._transition_item = QGraphicsPixmapItem()
        self._transition_item.setTransformationMode(Qt.SmoothTransformation)
        self._transition_item.setOpacity(0.0)
        self._transition_item.setVisible(False)
        self._scene.addItem(self._transition_item)
        self._empty_state_item = QGraphicsPixmapItem()
        self._empty_state_item.setOpacity(0.25)
        self._empty_state_item.setAcceptedMouseButtons(Qt.NoButton)
        self._empty_state_item.setFlag(QGraphicsPixmapItem.ItemIgnoresTransformations, True)
        self._scene.addItem(self._empty_state_item)
        self.setScene(self._scene)

        self._image_path: Path | None = None
        self._scale_factor = 1.0
        self._rotation_angle = 0
        self._fit_mode = True
        self._theme = "light"
        self._last_mouse_pos = QPoint()
        self._panning = False
        self._transition_anim: QVariantAnimation | None = None

        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(Qt.white)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setAlignment(Qt.AlignCenter)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._init_empty_state()
        self._update_empty_state()

    @property
    def image_path(self) -> Path | None:
        return self._image_path

    @property
    def scale_factor(self) -> float:
        return self._scale_factor

    def has_image(self) -> bool:
        return not self._pixmap_item.pixmap().isNull()

    def load_image(self, image_path: Path) -> bool:
        reader = QImageReader(str(image_path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            return False

        pixmap = QPixmap.fromImage(image)
        self._image_path = image_path
        self._set_centered_pixmap(self._pixmap_item, pixmap)
        self._transition_item.setVisible(False)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._rotation_angle = 0
        self._scale_factor = 1.0
        self.resetTransform()
        self._apply_rotation()
        self._set_initial_view()
        self._update_empty_state()
        return True

    def transition_to_image(self, image_path: Path, duration_ms: int = 220) -> bool:
        reader = QImageReader(str(image_path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            return False

        pixmap = QPixmap.fromImage(image)
        if not self.has_image():
            self._image_path = image_path
            self._set_centered_pixmap(self._pixmap_item, pixmap)
            self._pixmap_item.setOpacity(1.0)
            self._scene.setSceneRect(self._pixmap_item.boundingRect())
            self._rotation_angle = 0
            self._scale_factor = 1.0
            self.resetTransform()
            self._apply_rotation()
            self._set_initial_view()
            self._update_empty_state()
            return True

        if self._transition_anim is not None:
            self._transition_anim.stop()
            self._transition_anim = None

        old_pixmap = self._pixmap_item.pixmap()
        self._image_path = image_path
        self._rotation_angle = 0
        self._scale_factor = 1.0

        self._set_centered_pixmap(self._transition_item, old_pixmap)
        self._transition_item.setOpacity(1.0)
        self._transition_item.setVisible(True)
        self._set_centered_pixmap(self._pixmap_item, pixmap)
        self._pixmap_item.setOpacity(0.0)
        self._scene.setSceneRect(
            self._pixmap_item.boundingRect().united(self._transition_item.boundingRect())
        )
        self.resetTransform()
        self._apply_rotation()
        self._set_initial_view()
        self._update_empty_state()

        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(max(60, int(duration_ms)))
        anim.setEasingCurve(QEasingCurve.InOutCubic)

        def _on_value(value: object) -> None:
            v = float(value)
            self._pixmap_item.setOpacity(v)
            self._transition_item.setOpacity(1.0 - v)

        def _on_finished() -> None:
            self._pixmap_item.setOpacity(1.0)
            self._transition_item.setVisible(False)
            self._transition_item.setPixmap(QPixmap())
            self._scene.setSceneRect(self._pixmap_item.boundingRect())
            self.centerOn(self._pixmap_item)
            self._transition_anim = None

        anim.valueChanged.connect(_on_value)
        anim.finished.connect(_on_finished)
        self._transition_anim = anim
        anim.start()
        return True

    def clear_image(self) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._transition_item.setVisible(False)
        self._transition_item.setPixmap(QPixmap())
        self._image_path = None
        self._rotation_angle = 0
        self._scale_factor = 1.0
        self._fit_mode = False
        self.resetTransform()
        self._update_empty_state()
        self.zoom_changed.emit(self._scale_factor)

    def set_theme(self, theme: str) -> None:
        self._theme = "dark" if theme == "dark" else "light"
        if self._theme == "dark":
            background = QColor(24, 24, 24)
            empty_opacity = 0.22
        else:
            background = QColor(Qt.white)
            empty_opacity = 0.25

        self.setBackgroundBrush(background)
        self._empty_state_item.setOpacity(empty_opacity)
        self._init_empty_state()
        self._update_empty_state()

    def zoom_in(self) -> None:
        self.set_zoom(self._scale_factor * 1.25)

    def zoom_out(self) -> None:
        self.set_zoom(self._scale_factor / 1.25)

    def set_zoom(self, scale_factor: float) -> None:
        if not self.has_image():
            return

        new_scale = max(0.05, min(scale_factor, 20.0))
        self._fit_mode = False
        self._scale_factor = new_scale
        self._rebuild_transform()

    def fit_to_window(self) -> None:
        if not self.has_image():
            return

        self._fit_mode = True
        self.resetTransform()
        self._apply_rotation()
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
        self._scale_factor = self._current_transform_scale()
        self.zoom_changed.emit(self._scale_factor)

    def actual_size(self) -> None:
        self.set_zoom(1.0)

    def rotate_left(self) -> None:
        self._rotation_angle = (self._rotation_angle - 90) % 360
        self._rebuild_transform()

    def rotate_right(self) -> None:
        self._rotation_angle = (self._rotation_angle + 90) % 360
        self._rebuild_transform()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit_mode and self.has_image():
            self.fit_to_window()
        if not self.has_image():
            self._update_empty_state()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.has_image():
            super().wheelEvent(event)
            return

        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return

        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.has_image():
            self._panning = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _rebuild_transform(self) -> None:
        transform = QTransform()
        transform.rotate(self._rotation_angle)
        transform.scale(self._scale_factor, self._scale_factor)
        self.setTransform(transform)
        self.zoom_changed.emit(self._scale_factor)

    def _apply_rotation(self) -> None:
        transform = QTransform()
        transform.rotate(self._rotation_angle)
        self.setTransform(transform)

    def _current_transform_scale(self) -> float:
        transform = self.transform()
        return math.hypot(transform.m11(), transform.m12())

    def _set_centered_pixmap(self, item: QGraphicsPixmapItem, pixmap: QPixmap) -> None:
        item.setPixmap(pixmap)
        if pixmap.isNull():
            item.setOffset(0, 0)
            return
        item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)

    def _set_initial_view(self) -> None:
        if not self.has_image():
            return

        viewport_size = self.viewport().size()
        pixmap_size = self._pixmap_item.pixmap().size()
        if pixmap_size.width() <= viewport_size.width() and pixmap_size.height() <= viewport_size.height():
            self.actual_size()
            return

        self.fit_to_window()

    def _init_empty_state(self) -> None:
        app = QApplication.instance()
        icon = QIcon()
        if app is not None:
            icon = app.style().standardIcon(QStyle.SP_FileDialogContentsView)
        pixmap = icon.pixmap(128, 128)
        if pixmap.isNull():
            pixmap = QPixmap(128, 128)
            pixmap.fill(Qt.lightGray)
        pixmap = self._tint_pixmap(
            pixmap,
            QColor(218, 218, 218) if self._theme == "dark" else QColor(150, 150, 150),
        )
        self._empty_state_item.setPixmap(pixmap)
        self._empty_state_item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)

    def _update_empty_state(self) -> None:
        if self.has_image():
            self._empty_state_item.setVisible(False)
            return

        rect = self.viewport().rect()
        self._scene.setSceneRect(QRectF(0, 0, rect.width(), rect.height()))
        self._empty_state_item.setPos(self.mapToScene(rect.center()))
        self._empty_state_item.setVisible(True)

    def _tint_pixmap(self, pixmap: QPixmap, color: QColor) -> QPixmap:
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return tinted
