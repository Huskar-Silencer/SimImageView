from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QFontMetrics,
    QIcon,
    QImageReader,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QToolBar,
)

from canvas import ImageCanvas


SUPPORTED_SUFFIXES = {
    ".bmp",
    ".dib",
    ".gif",
    ".heic",
    ".ico",
    ".jpeg",
    ".jpg",
    ".jfif",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
}


class ThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, icon_size: QSize, grid_size: QSize, parent=None) -> None:
        super().__init__(parent)
        self._icon_size = icon_size
        self._grid_size = grid_size
        self._padding = 8
        self._gap = 6

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(self._grid_size)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        rect = option.rect
        selected = bool(option.state & QStyle.State_Selected)

        painter.save()
        painter.setClipRect(rect)
        if selected:
            painter.fillRect(rect, option.palette.highlight())
            text_color = option.palette.highlightedText().color()
        else:
            painter.fillRect(rect, option.palette.base())
            text_color = option.palette.text().color()

        border_color = option.palette.mid().color()
        painter.setPen(QPen(border_color, 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        text = str(index.data(Qt.DisplayRole) or "")
        fm = QFontMetrics(option.font)
        text_height = fm.height() + 2
        text_y = rect.y() + rect.height() - self._padding - text_height
        text_rect = QRect(
            rect.x() + self._padding,
            text_y,
            rect.width() - self._padding * 2,
            text_height,
        )

        icon_top = rect.y() + self._padding
        icon_bottom = text_y - self._gap
        icon_height = max(1, icon_bottom - icon_top)
        icon_width = max(1, rect.width() - self._padding * 2)

        source_pixmap = index.data(Qt.UserRole)
        if not isinstance(source_pixmap, QPixmap) or source_pixmap.isNull():
            icon_value = index.data(Qt.DecorationRole)
            icon = icon_value if isinstance(icon_value, QIcon) else QIcon()
            source_pixmap = icon.pixmap(self._icon_size)

        scaled = source_pixmap.scaled(
            QSize(icon_width, icon_height),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        icon_x = rect.x() + (rect.width() - scaled.width()) // 2
        icon_y = icon_top + (icon_height - scaled.height()) // 2
        painter.drawPixmap(icon_x, icon_y, scaled)

        elided = fm.elidedText(text, Qt.ElideRight, text_rect.width())
        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, elided)
        painter.restore()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PySide6 Image Viewer")
        self.resize(1400, 900)
        self.setAcceptDrops(True)

        app = QApplication.instance()
        self._theme = "light"
        self._light_palette = QPalette(app.palette()) if app is not None else QPalette()
        self._dark_palette = self._build_dark_palette()

        self.canvas = ImageCanvas()
        self.setCentralWidget(self.canvas)

        self.image_paths: list[Path] = []
        self.current_index = -1
        self.current_dir: Path | None = None

        self.thumbnail_icon_size = QSize(120, 120)
        self.thumbnail_grid_size = QSize(160, 170)

        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(self.thumbnail_icon_size)
        self.thumbnail_list.setGridSize(self.thumbnail_grid_size)
        self.thumbnail_list.setItemDelegate(
            ThumbnailDelegate(self.thumbnail_icon_size, self.thumbnail_grid_size, self.thumbnail_list)
        )
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setMovement(QListWidget.Static)
        self.thumbnail_list.setSpacing(0)
        self.thumbnail_list.setUniformItemSizes(True)
        self.thumbnail_list.setWordWrap(False)
        self.thumbnail_list.setTextElideMode(Qt.ElideRight)
        self.thumbnail_list.setSelectionMode(QListWidget.SingleSelection)
        self.thumbnail_list.currentRowChanged.connect(self._on_thumbnail_selected)

        self.thumbnail_dock = QDockWidget("Thumbnails", self)
        self.thumbnail_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.thumbnail_dock.setMinimumWidth(220)
        self.thumbnail_dock.setMaximumWidth(520)
        self.thumbnail_dock.setWidget(self.thumbnail_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.thumbnail_dock)
        self.thumbnail_dock.setVisible(False)

        self._slideshow_interval_ms = 3000
        self._slideshow_timer = QTimer(self)
        self._slideshow_timer.timeout.connect(self._slideshow_next)

        self.path_label = QLabel("No image opened")
        self.path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.info_label = QLabel("")

        status_bar = QStatusBar(self)
        status_bar.addWidget(self.path_label, 1)
        status_bar.addPermanentWidget(self.info_label)
        self.setStatusBar(status_bar)

        self._create_actions()
        self._create_menus()
        self._create_toolbar()

        self.canvas.zoom_changed.connect(self._update_status)
        self.set_theme(self._theme)
        self._update_actions()

    def _create_actions(self) -> None:
        style = self.style()

        self.open_file_action = QAction(
            style.standardIcon(QStyle.SP_DialogOpenButton),
            "Open Image",
            self,
        )
        self.open_file_action.setShortcut(QKeySequence.Open)
        self.open_file_action.triggered.connect(self.open_file)

        self.open_folder_action = QAction("Open Folder", self)
        self.open_folder_action.setShortcut("Ctrl+Shift+O")
        self.open_folder_action.triggered.connect(self.open_folder)

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)

        self.prev_action = QAction(
            style.standardIcon(QStyle.SP_ArrowBack),
            "Previous",
            self,
        )
        self.prev_action.setShortcut(QKeySequence(Qt.Key_Left))
        self.prev_action.triggered.connect(self.show_previous_image)

        self.next_action = QAction(
            style.standardIcon(QStyle.SP_ArrowForward),
            "Next",
            self,
        )
        self.next_action.setShortcut(QKeySequence(Qt.Key_Right))
        self.next_action.triggered.connect(self.show_next_image)

        self.zoom_in_action = QAction("Zoom In", self)
        self.zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        self.zoom_in_action.triggered.connect(self.canvas.zoom_in)

        self.zoom_out_action = QAction("Zoom Out", self)
        self.zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        self.zoom_out_action.triggered.connect(self.canvas.zoom_out)

        self.fit_action = QAction("Fit to Window", self)
        self.fit_action.setShortcut("Ctrl+0")
        self.fit_action.triggered.connect(self.canvas.fit_to_window)

        self.actual_size_action = QAction("Actual Size", self)
        self.actual_size_action.setShortcut("Ctrl+1")
        self.actual_size_action.triggered.connect(self.canvas.actual_size)

        self.rotate_left_action = QAction("Rotate Left 90°", self)
        self.rotate_left_action.setShortcut("Ctrl+L")
        self.rotate_left_action.triggered.connect(self.canvas.rotate_left)

        self.rotate_right_action = QAction("Rotate Right 90°", self)
        self.rotate_right_action.setShortcut("Ctrl+R")
        self.rotate_right_action.triggered.connect(self.canvas.rotate_right)

        self.fullscreen_action = QAction("Fullscreen", self)
        self.fullscreen_action.setShortcut(QKeySequence.FullScreen)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)

        self.slideshow_action = QAction("Slideshow", self)
        self.slideshow_action.setShortcut("F5")
        self.slideshow_action.setCheckable(True)
        self.slideshow_action.toggled.connect(self._toggle_slideshow)

        self.slideshow_interval_action = QAction("Slideshow Interval...", self)
        self.slideshow_interval_action.triggered.connect(self._set_slideshow_interval)

        self.toggle_sidebar_action = QAction("Show Thumbnails Pane", self)
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(False)
        self.toggle_sidebar_action.toggled.connect(self.thumbnail_dock.setVisible)
        self.thumbnail_dock.visibilityChanged.connect(
            self.toggle_sidebar_action.setChecked
        )

        self.theme_toggle_action = QAction("Dark Theme", self)
        self.theme_toggle_action.triggered.connect(self._toggle_theme)

        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)

        self.light_theme_action = QAction("Light", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.triggered.connect(
            lambda checked=False: self.set_theme("light")
        )
        self.theme_action_group.addAction(self.light_theme_action)

        self.dark_theme_action = QAction("Dark", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.triggered.connect(
            lambda checked=False: self.set_theme("dark")
        )
        self.theme_action_group.addAction(self.dark_theme_action)

        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.show_about_dialog)

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.open_file_action)
        file_menu.addAction(self.open_folder_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.prev_action)
        view_menu.addAction(self.next_action)
        view_menu.addSeparator()
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.fit_action)
        view_menu.addAction(self.actual_size_action)
        view_menu.addSeparator()
        view_menu.addAction(self.rotate_left_action)
        view_menu.addAction(self.rotate_right_action)
        view_menu.addSeparator()
        view_menu.addAction(self.toggle_sidebar_action)
        view_menu.addAction(self.slideshow_action)
        view_menu.addAction(self.slideshow_interval_action)
        view_menu.addAction(self.fullscreen_action)

        theme_menu = view_menu.addMenu("Theme")
        theme_menu.addAction(self.light_theme_action)
        theme_menu.addAction(self.dark_theme_action)

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction(self.about_action)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        toolbar.addAction(self.open_file_action)
        toolbar.addAction(self.open_folder_action)
        toolbar.addSeparator()
        toolbar.addAction(self.prev_action)
        toolbar.addAction(self.next_action)
        toolbar.addSeparator()
        toolbar.addAction(self.zoom_in_action)
        toolbar.addAction(self.zoom_out_action)
        toolbar.addAction(self.fit_action)
        toolbar.addAction(self.actual_size_action)
        toolbar.addSeparator()
        toolbar.addAction(self.rotate_left_action)
        toolbar.addAction(self.rotate_right_action)
        toolbar.addSeparator()
        toolbar.addAction(self.slideshow_action)
        toolbar.addAction(self.fullscreen_action)
        toolbar.addSeparator()
        toolbar.addAction(self.theme_toggle_action)
        toolbar.addAction(self.about_action)

    def open_file(self) -> None:
        filters = self._build_file_dialog_filter()
        start_dir = str(self.current_dir or Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            start_dir,
            filters,
        )
        if file_path:
            self.load_from_path(Path(file_path))

    def open_folder(self) -> None:
        start_dir = str(self.current_dir or Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", start_dir)
        if not folder:
            return

        directory = Path(folder)
        image_paths = self._collect_images(directory)
        if not image_paths:
            QMessageBox.information(
                self,
                "No Images",
                "No supported image files were found in this folder.",
            )
            return

        self._set_image_list(image_paths, 0)

    def load_from_path(self, path: Path) -> None:
        if path.is_dir():
            image_paths = self._collect_images(path)
            if image_paths:
                self._set_image_list(image_paths, 0)
            else:
                QMessageBox.information(
                    self,
                    "No Images",
                    "No supported image files were found in this folder.",
                )
            return

        if not path.exists():
            QMessageBox.warning(self, "File Not Found", f"Cannot find file:\n{path}")
            return

        siblings = self._collect_images(path.parent)
        if path in siblings:
            self._set_image_list(siblings, siblings.index(path))
        else:
            self._set_image_list([path], 0)

    def show_previous_image(self) -> None:
        if self.current_index > 0:
            self._show_image_at_index(self.current_index - 1)

    def show_next_image(self) -> None:
        if 0 <= self.current_index < len(self.image_paths) - 1:
            self._show_image_at_index(self.current_index + 1)

    def toggle_fullscreen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _toggle_slideshow(self, enabled: bool) -> None:
        if enabled:
            if not self.image_paths:
                self.slideshow_action.setChecked(False)
                return
            self._slideshow_timer.start(self._slideshow_interval_ms)
            return

        self._slideshow_timer.stop()

    def _set_slideshow_interval(self) -> None:
        value, ok = QInputDialog.getInt(
            self,
            "Slideshow Interval",
            "Interval (seconds):",
            max(1, int(round(self._slideshow_interval_ms / 1000))),
            1,
            3600,
            1,
        )
        if not ok:
            return

        self._slideshow_interval_ms = value * 1000
        if self.slideshow_action.isChecked():
            self._slideshow_timer.start(self._slideshow_interval_ms)

    def _toggle_theme(self) -> None:
        next_theme = "dark" if self._theme == "light" else "light"
        self.set_theme(next_theme)

    def set_theme(self, theme: str) -> None:
        normalized_theme = "dark" if theme == "dark" else "light"
        if self._theme == normalized_theme and hasattr(self, "theme_toggle_action"):
            self._sync_theme_actions()
            self.canvas.set_theme(normalized_theme)
            return

        self._theme = normalized_theme
        app = QApplication.instance()
        if app is not None:
            if normalized_theme == "dark":
                app.setPalette(self._dark_palette)
                app.setStyleSheet(
                    """
                    QToolTip {
                        color: #f5f5f5;
                        background-color: #2b2b2b;
                        border: 1px solid #575757;
                    }
                    """
                )
            else:
                app.setPalette(self._light_palette)
                app.setStyleSheet("")

        self.canvas.set_theme(normalized_theme)
        self._sync_theme_actions()
        self.thumbnail_list.viewport().update()

    def _sync_theme_actions(self) -> None:
        is_dark = self._theme == "dark"
        self.light_theme_action.setChecked(not is_dark)
        self.dark_theme_action.setChecked(is_dark)
        self.theme_toggle_action.setText("Light Theme" if is_dark else "Dark Theme")

    def _build_dark_palette(self) -> QPalette:
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(37, 37, 38))
        palette.setColor(QPalette.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ToolTipBase, QColor(43, 43, 43))
        palette.setColor(QPalette.ToolTipText, QColor(245, 245, 245))
        palette.setColor(QPalette.Text, QColor(230, 230, 230))
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, QColor(235, 235, 235))
        palette.setColor(QPalette.BrightText, Qt.white)
        palette.setColor(QPalette.Highlight, QColor(58, 129, 240))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        palette.setColor(QPalette.Link, QColor(90, 170, 255))
        palette.setColor(QPalette.Mid, QColor(70, 70, 70))
        palette.setColor(QPalette.Dark, QColor(20, 20, 20))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(130, 130, 130))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(130, 130, 130))
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(130, 130, 130))
        return palette

    def show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            "About PySide6 Image Viewer",
            (
                "PySide6 Image Viewer\n\n"
                "A desktop image viewer built with PySide6.\n\n"
                "Features:\n"
                "- Folder browsing and thumbnails\n"
                "- Smooth slideshow transitions\n"
                "- Zoom, rotate, fullscreen and drag-and-drop\n"
                "- Light and dark themes"
            ),
        )

    def _slideshow_next(self) -> None:
        if not self.image_paths:
            self.slideshow_action.setChecked(False)
            return

        if self.current_index < 0:
            self._show_image_at_index(0, animated=True)
            return

        next_index = self.current_index + 1
        if next_index >= len(self.image_paths):
            next_index = 0
        self._show_image_at_index(next_index, animated=True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return

        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            super().dropEvent(event)
            return

        local_path = Path(urls[0].toLocalFile())
        if local_path.exists():
            self.load_from_path(local_path)
            event.acceptProposedAction()
            return

        super().dropEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.fullscreen_action.setChecked(False)
            self.showNormal()
            event.accept()
            return

        if event.key() in {Qt.Key_Space, Qt.Key_Down, Qt.Key_PageDown}:
            self.show_next_image()
            event.accept()
            return

        if event.key() in {Qt.Key_Up, Qt.Key_PageUp, Qt.Key_Backspace}:
            self.show_previous_image()
            event.accept()
            return

        super().keyPressEvent(event)

    def _build_file_dialog_filter(self) -> str:
        suffixes = " ".join(f"*{suffix}" for suffix in sorted(SUPPORTED_SUFFIXES))
        return f"Images ({suffixes});;All Files (*)"

    def _collect_images(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []

        files = [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        ]
        return sorted(files, key=lambda item: item.name.lower())

    def _set_image_list(self, image_paths: list[Path], index: int) -> None:
        self.image_paths = image_paths
        self.current_dir = image_paths[0].parent if image_paths else None
        self._populate_thumbnails()
        self._show_image_at_index(index)

        if not self.image_paths and self.slideshow_action.isChecked():
            self.slideshow_action.setChecked(False)

    def _populate_thumbnails(self) -> None:
        self.thumbnail_list.blockSignals(True)
        self.thumbnail_list.clear()

        for image_path in self.image_paths:
            item = QListWidgetItem(image_path.name)
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(
                    self.thumbnail_icon_size.width(),
                    self.thumbnail_icon_size.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                item.setData(Qt.UserRole, thumbnail)
                item.setIcon(QIcon(thumbnail))
            item.setToolTip(str(image_path))
            self.thumbnail_list.addItem(item)

        self.thumbnail_list.blockSignals(False)

    def _show_image_at_index(self, index: int, animated: bool = False) -> None:
        if not (0 <= index < len(self.image_paths)):
            return

        image_path = self.image_paths[index]
        ok = (
            self.canvas.transition_to_image(image_path)
            if animated
            else self.canvas.load_image(image_path)
        )
        if not ok:
            QMessageBox.warning(self, "Open Failed", f"Unable to read image:\n{image_path}")
            return

        self.current_index = index
        self.thumbnail_list.blockSignals(True)
        self.thumbnail_list.setCurrentRow(index)
        self.thumbnail_list.scrollToItem(self.thumbnail_list.item(index))
        self.thumbnail_list.blockSignals(False)
        self.path_label.setText(str(image_path))
        self._update_status()
        self._update_actions()

    def _on_thumbnail_selected(self, row: int) -> None:
        if row >= 0 and row != self.current_index:
            self._show_image_at_index(row)

    def _update_status(self) -> None:
        if not self.canvas.has_image() or self.current_index < 0:
            self.info_label.setText("")
            return

        path = self.image_paths[self.current_index]
        reader = QImageReader(str(path))
        size = reader.size()
        zoom_percent = int(round(self.canvas.scale_factor * 100))
        self.info_label.setText(
            f"{self.current_index + 1}/{len(self.image_paths)} | "
            f"{size.width()}x{size.height()} | "
            f"{zoom_percent}%"
        )

    def _update_actions(self) -> None:
        has_images = bool(self.image_paths)
        has_current = self.current_index >= 0

        self.prev_action.setEnabled(has_current and self.current_index > 0)
        self.next_action.setEnabled(
            has_current and self.current_index < len(self.image_paths) - 1
        )
        self.slideshow_action.setEnabled(has_images)
        self.slideshow_interval_action.setEnabled(True)

        for action in (
            self.zoom_in_action,
            self.zoom_out_action,
            self.fit_action,
            self.actual_size_action,
            self.rotate_left_action,
            self.rotate_right_action,
            self.fullscreen_action,
        ):
            action.setEnabled(has_images)


def create_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    app.setApplicationName("PySide6 Image Viewer")
    app.setOrganizationName("Trae")
    app.setStyle("Fusion")
    return app
