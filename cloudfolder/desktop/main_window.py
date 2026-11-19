"""Головне вікно десктоп-клієнта «Хмарне сховище» (PySide6)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QFont, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core import variant
from ..core.models import FileRecord
from ..core.variant import PreviewKind, SortOrder
from .api_client import ApiClient, ApiError
from .sync_engine import SyncEngine
from .viewmodel import COLUMNS, FILTER_OPTIONS, FilesViewModel

ARROWS = {SortOrder.ASC: " ▲", SortOrder.DESC: " ▼", SortOrder.NONE: ""}


def fmt_dt(dt) -> str:
    return dt.astimezone().strftime("%d.%m.%Y %H:%M:%S")


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} Б"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} КБ"
    return f"{n / (1024 * 1024):.1f} МБ"


class DropTable(QTableWidget):
    """Таблиця, що приймає файли, перетягнуті з провідника (drag-n-drop)."""

    files_dropped = Signal(list)

    def __init__(self, *args):
        super().__init__(*args)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            e.acceptProposedAction()


class PreviewPanel(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.default_text = (
            "Клікніть на файл, щоб переглянути вміст.\n\n"
            f"Підтримувані типи: {', '.join(variant.PREVIEW_TEXT_EXTENSIONS)} (текст), "
            f"{', '.join(variant.PREVIEW_IMAGE_EXTENSIONS)} (зображення)"
        )
        self.placeholder = QLabel(self.default_text)
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.placeholder.setStyleSheet("color: #777")
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.image)
        scroll.setWidgetResizable(True)
        self.addWidget(self.placeholder)
        self.addWidget(self.text)
        self.addWidget(scroll)
        self.scroll = scroll

    def show_placeholder(self, message: str | None = None):
        if message:
            self.placeholder.setText(message)
        self.setCurrentWidget(self.placeholder)

    def show_text(self, content: str):
        self.text.setPlainText(content)
        self.setCurrentWidget(self.text)

    def show_image(self, data: bytes) -> bool:
        pix = QPixmap()
        if not pix.loadFromData(data):
            return False
        if pix.width() > 900:
            pix = pix.scaledToWidth(900, Qt.SmoothTransformation)
        self.image.setPixmap(pix)
        self.setCurrentWidget(self.scroll)
        return True


class MainWindow(QMainWindow):
    def __init__(self, client: ApiClient):
        super().__init__()
        self.client = client
        self.vm = FilesViewModel(client)
        self.setWindowTitle(f"Хмарне сховище — {client.username} @ {client.base_url}")
        self.resize(1280, 780)

        self._build_toolbar()
        self._build_central()
        self._build_sync_panel()
        self.statusBar().showMessage("Готово")

        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self._schedule_sync)
        self.sync_debounce = QTimer(self, singleShot=True, interval=1500, timeout=self.sync_now)
        self.sync_poll = QTimer(self, interval=15000, timeout=self.sync_now)
        self._syncing = False

        self.refresh()

    # ================================================================ UI
    def _build_toolbar(self):
        tb = QToolBar("Дії")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        self.act_refresh = QAction("Оновити", self, triggered=self.refresh)
        self.act_upload = QAction("Вивантажити…", self, triggered=self.upload_dialog)
        self.act_download = QAction("Завантажити", self, triggered=self.download_selected)
        self.act_delete = QAction("Видалити", self, triggered=self.delete_selected)
        for a in (self.act_refresh, self.act_upload, self.act_download, self.act_delete):
            tb.addAction(a)
        tb.addSeparator()

        self.columns_menu = QMenu("Стовпці", self)
        self.column_actions: dict[str, QAction] = {}
        for col in COLUMNS:
            act = QAction(col.title, self, checkable=True, checked=True)
            act.setEnabled(col.hideable)
            act.toggled.connect(lambda on, k=col.key: self._toggle_column(k, on))
            self.columns_menu.addAction(act)
            self.column_actions[col.key] = act
        self.columns_menu.addSeparator()
        self.columns_menu.addAction("Показати всі", lambda: self._all_columns(True))
        self.columns_menu.addAction("Приховати всі, крім імені", lambda: self._all_columns(False))
        btn = QToolButton()
        btn.setText("Стовпці")
        btn.setMenu(self.columns_menu)
        btn.setPopupMode(QToolButton.InstantPopup)
        tb.addWidget(btn)
        tb.addSeparator()

        tb.addWidget(QLabel(" Фільтр: "))
        self.filter_combo = QComboBox()
        for value, title in FILTER_OPTIONS:
            self.filter_combo.addItem(title, value)
        self.filter_combo.currentIndexChanged.connect(self._filter_changed)
        tb.addWidget(self.filter_combo)
        tb.addSeparator()

        tb.addWidget(QLabel(" Сортування за датою зміни: "))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("без сортування", SortOrder.NONE.value)
        self.sort_combo.addItem("за зростанням ▲", SortOrder.ASC.value)
        self.sort_combo.addItem("за спаданням ▼", SortOrder.DESC.value)
        self.sort_combo.currentIndexChanged.connect(self._sort_combo_changed)
        tb.addWidget(self.sort_combo)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        tb.addWidget(QLabel(f"Користувач: {self.client.username}  "))
        tb.addAction(QAction("Вийти", self, triggered=self.logout))

    def _build_central(self):
        self.table = DropTable(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([c.title for c in COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.sectionClicked.connect(self._header_clicked)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.cellDoubleClicked.connect(lambda *_: self.download_selected())
        self.table.files_dropped.connect(self.upload_paths)

        hint = QLabel("Порада: перетягніть файли з провідника в таблицю, щоб вивантажити їх.")
        hint.setStyleSheet("color: #777")
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.table)
        lv.addWidget(hint)

        self.preview_title = QLabel("<b>Перегляд</b>")
        self.preview = PreviewPanel()
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(self.preview_title)
        rv.addWidget(self.preview)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setSizes([780, 480])

        self.central = QWidget()
        self.central_layout = QVBoxLayout(self.central)
        self.central_layout.addWidget(self.splitter, 1)
        self.setCentralWidget(self.central)

    def _build_sync_panel(self):
        box = QGroupBox("Синхронізація локальної папки")
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Оберіть локальну папку…")
        self.folder_edit.setReadOnly(True)
        choose = QPushButton("Обрати папку…", clicked=self.choose_folder)
        self.sync_btn = QPushButton("Синхронізувати зараз", clicked=self.sync_now)
        self.auto_sync = QCheckBox("Автоматично (відстеження змін + кожні 15 с)")
        self.auto_sync.toggled.connect(self._auto_sync_toggled)
        row = QHBoxLayout()
        row.addWidget(QLabel("Папка:"))
        row.addWidget(self.folder_edit, 1)
        row.addWidget(choose)
        row.addWidget(self.sync_btn)
        row.addWidget(self.auto_sync)
        self.sync_log = QPlainTextEdit()
        self.sync_log.setReadOnly(True)
        self.sync_log.setMaximumHeight(110)
        v = QVBoxLayout(box)
        v.addLayout(row)
        v.addWidget(self.sync_log)
        self.central_layout.addWidget(box)

    # ================================================================ дані
    def refresh(self):
        try:
            self.vm.refresh()
        except ApiError as exc:
            self._error(exc)
            return
        self.render_table()
        self.statusBar().showMessage(f"Файлів у папці: {len(self.vm.files)}")

    def render_table(self):
        previous = self.selected() if hasattr(self, "_rows") else None
        files = self.vm.displayed_files
        self._rows: list[FileRecord] = files
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.setRowCount(len(files))
        for r, f in enumerate(files):
            values = [f.name, fmt_dt(f.created_at), fmt_dt(f.modified_at), f.uploaded_by, f.edited_by, fmt_size(f.size)]
            for c, v in enumerate(values):
                item = QTableWidgetItem(v)
                if c == 5:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, item)
        for i, col in enumerate(COLUMNS):
            arrow = ARROWS[self.vm.sort_order] if self.vm.sort_attribute == col.key else ""
            self.table.horizontalHeaderItem(i).setText(col.title + arrow)
            self.table.setColumnHidden(i, not self.vm.is_column_visible(col.key))
        keep = next((r for r, f in enumerate(files) if previous and f.id == previous.id), None)
        if keep is not None:
            self.table.selectRow(keep)
        self.table.blockSignals(False)
        if keep is None:
            self.preview_title.setText("<b>Перегляд</b>")
            self.preview.show_placeholder(self.preview.default_text)

    def selected(self) -> FileRecord | None:
        rows = self.table.selectionModel().selectedRows()
        return self._rows[rows[0].row()] if rows else None

    # ================================================================ обробники
    def _header_clicked(self, index: int):
        if index >= len(COLUMNS):
            return
        self.vm.toggle_sort(COLUMNS[index].key)
        self._sync_sort_combo()
        self.render_table()

    def _sort_combo_changed(self):
        order = SortOrder(self.sort_combo.currentData())
        if order is SortOrder.NONE and self.vm.sort_attribute != variant.VARIANT_SORT_ATTRIBUTE:
            return
        self.vm.set_sort(variant.VARIANT_SORT_ATTRIBUTE, order)
        self.render_table()

    def _sync_sort_combo(self):
        value = self.vm.sort_order.value if self.vm.sort_attribute == variant.VARIANT_SORT_ATTRIBUTE else "none"
        self.sort_combo.blockSignals(True)
        self.sort_combo.setCurrentIndex(self.sort_combo.findData(value))
        self.sort_combo.blockSignals(False)

    def _filter_changed(self):
        self.vm.set_filter(self.filter_combo.currentData())
        self.render_table()

    def _toggle_column(self, key: str, visible: bool):
        self.vm.set_column_visible(key, visible)
        self.render_table()

    def _all_columns(self, visible: bool):
        for col in COLUMNS:
            if col.hideable:
                self.column_actions[col.key].setChecked(visible)

    def _selection_changed(self):
        f = self.selected()
        if not f:
            self.preview.show_placeholder()
            return
        kind = variant.preview_kind(f.name)
        self.preview_title.setText(f"<b>Перегляд:</b> {f.name}")
        if kind is PreviewKind.NONE:
            self.preview.show_placeholder(
                f"Перегляд вмісту для «{f.extension or 'без розширення'}» не підтримується.\n"
                "Файл можна завантажити (подвійний клік)."
            )
            return
        try:
            data = self.vm.download(f)
        except ApiError as exc:
            self._error(exc)
            return
        if kind is PreviewKind.TEXT:
            self.preview.show_text(data.decode("utf-8", errors="replace"))
        elif not self.preview.show_image(data):
            self.preview.show_placeholder("Не вдалося відкрити зображення")

    # ================================================================ файлові операції
    def upload_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Оберіть файли для вивантаження")
        if paths:
            self.upload_paths(paths)

    def upload_paths(self, paths: list[str]):
        done = 0
        for p in paths:
            path = Path(p)
            if not path.is_file():
                continue
            try:
                self.client.upload(path.name, path.read_bytes())
                done += 1
            except (ApiError, OSError) as exc:
                self._error(exc)
        self.refresh()
        self.statusBar().showMessage(f"Вивантажено файлів: {done}")

    def download_selected(self):
        f = self.selected()
        if not f:
            return
        target, _ = QFileDialog.getSaveFileName(self, "Зберегти файл як", str(Path.home() / "Downloads" / f.name))
        if not target:
            return
        try:
            Path(target).write_bytes(self.vm.download(f))
        except (ApiError, OSError) as exc:
            self._error(exc)
            return
        self.statusBar().showMessage(f"Збережено: {target}")

    def delete_selected(self):
        f = self.selected()
        if not f:
            return
        box = QMessageBox(
            QMessageBox.Question, "Видалення", f"Видалити файл «{f.name}» з віддаленої папки?",
            QMessageBox.Yes | QMessageBox.No, self,
        )
        box.button(QMessageBox.Yes).setText("Так, видалити")
        box.button(QMessageBox.No).setText("Скасувати")
        if box.exec() != QMessageBox.Yes:
            return
        try:
            self.vm.delete(f)
        except ApiError as exc:
            self._error(exc)
            return
        self.render_table()
        self.statusBar().showMessage(f"Видалено: {f.name}")

    # ================================================================ синхронізація
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Оберіть локальну папку для синхронізації")
        if folder:
            self.set_sync_folder(folder)

    def set_sync_folder(self, folder: str):
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())
        self.folder_edit.setText(folder)
        if self.auto_sync.isChecked():
            self.watcher.addPath(folder)

    def _auto_sync_toggled(self, on: bool):
        folder = self.folder_edit.text()
        if on and folder:
            self.watcher.addPath(folder)
            self.sync_poll.start()
            self.sync_now()
        else:
            if self.watcher.directories():
                self.watcher.removePaths(self.watcher.directories())
            self.sync_poll.stop()

    def _schedule_sync(self, *_):
        if not self._syncing:
            self.sync_debounce.start()

    def sync_now(self):
        folder = self.folder_edit.text()
        if not folder:
            self.statusBar().showMessage("Спочатку оберіть локальну папку")
            return
        if self._syncing:
            return
        self._syncing = True
        try:
            report = SyncEngine(self.client, folder).run_once()
        except (ApiError, OSError) as exc:
            self.sync_log.appendPlainText(f"Помилка: {exc}")
            return
        finally:
            self._syncing = False
        stamp = datetime.now().strftime("%H:%M:%S")
        self.sync_log.appendPlainText(f"[{stamp}] {report.summary()}")
        for a in report.actions:
            self.sync_log.appendPlainText(f"    {a}")
        for e in report.errors:
            self.sync_log.appendPlainText(f"    ПОМИЛКА {e}")
        if report.changed:
            self.refresh()

    # ================================================================ інше
    def logout(self):
        self.client.logout()
        self.close()
        self.logged_out = True

    def _error(self, exc: Exception):
        self.statusBar().showMessage(f"Помилка: {exc}")
        if isinstance(exc, ApiError) and exc.status == 401:
            QMessageBox.warning(self, "Сесія", str(exc))
