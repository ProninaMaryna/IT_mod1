"""View-модель списку файлів (без залежності від Qt — тестується модульними тестами)."""
from __future__ import annotations

from dataclasses import dataclass

from ..core import variant
from ..core.models import FileRecord
from ..core.variant import SortOrder
from .api_client import ApiClientProtocol


@dataclass(frozen=True)
class Column:
    key: str
    title: str
    hideable: bool = True


COLUMNS: tuple[Column, ...] = (
    Column("name", "Ім'я", hideable=False),
    Column("created_at", "Створено"),
    Column("modified_at", "Змінено"),
    Column("uploaded_by", "Вивантажив"),
    Column("edited_by", "Редагував"),
    Column("size", "Розмір"),
)

FILTER_OPTIONS: tuple[tuple[str, str], ...] = (("all", "Усі файли"),) + tuple(
    (ext, f"Лише {ext}") for ext in variant.FILTER_EXTENSIONS
)


class FilesViewModel:
    def __init__(self, api: ApiClientProtocol):
        self.api = api
        self.files: list[FileRecord] = []
        self.sort_attribute: str = variant.VARIANT_SORT_ATTRIBUTE
        self.sort_order: SortOrder = SortOrder.NONE
        self.type_filter: str = "all"
        self.hidden_columns: set[str] = set()

    # ---------------------------------------------------------------- дані
    def refresh(self) -> None:
        self.files = self.api.list_files()

    @property
    def displayed_files(self) -> list[FileRecord]:
        return variant.sort_and_filter(self.files, self.type_filter, self.sort_attribute, self.sort_order)

    # ---------------------------------------------------------------- сортування / фільтр
    def toggle_sort(self, attribute: str) -> SortOrder:
        """Клік на заголовок: для того самого стовпця none -> asc -> desc -> none, для нового — asc."""
        if attribute not in variant.SORTABLE_ATTRIBUTES:
            raise ValueError(attribute)
        if attribute != self.sort_attribute:
            self.sort_attribute, self.sort_order = attribute, SortOrder.ASC
        else:
            self.sort_order = self.sort_order.next()
        return self.sort_order

    def set_sort(self, attribute: str, order: SortOrder | str) -> None:
        self.sort_attribute, self.sort_order = attribute, SortOrder(order)

    def set_filter(self, value: str) -> None:
        if value != "all" and value not in variant.FILTER_EXTENSIONS:
            raise ValueError(value)
        self.type_filter = value

    # ---------------------------------------------------------------- стовпці
    def set_column_visible(self, key: str, visible: bool) -> None:
        column = next(c for c in COLUMNS if c.key == key)
        if not column.hideable:
            return  # стовпець імені приховати неможливо
        if visible:
            self.hidden_columns.discard(key)
        else:
            self.hidden_columns.add(key)

    def is_column_visible(self, key: str) -> bool:
        return key not in self.hidden_columns

    def set_all_optional_columns(self, visible: bool) -> None:
        for c in COLUMNS:
            self.set_column_visible(c.key, visible)

    # ---------------------------------------------------------------- операції
    def upload(self, name: str, data: bytes) -> FileRecord:
        record = self.api.upload(name, data)
        self.refresh()
        return record

    def download(self, record: FileRecord) -> bytes:
        return self.api.download(record.id)

    def delete(self, record: FileRecord) -> None:
        self.api.delete(record.id)
        self.refresh()
