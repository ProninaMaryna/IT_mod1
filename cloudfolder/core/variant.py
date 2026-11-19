"""Операції, що визначаються варіантом завдання (варіант 12).

* Перша цифра (1) -> типи файлів для перегляду вмісту: ``.xml`` (як текст) та ``.png`` (як зображення).
* Друга цифра (2) -> операція: сортування за атрибутом №2 (дата модифікації) за зростанням/спаданням
  та фільтрація «усі файли» / лише файли типів ``.java``, ``.png`` (як указано в операції №2).

Порядок атрибутів у завданні: 0 — ім'я, 1 — дата створення, 2 — дата модифікації,
3 — хто вивантажив, 4 — хто редагував.
"""
from __future__ import annotations

from enum import Enum
from typing import Iterable, Sequence

from .models import FileRecord

VARIANT = "12"

#: Типи, вміст яких показується при кліку (перша цифра варіанта).
PREVIEW_TEXT_EXTENSIONS: tuple[str, ...] = (".xml",)
PREVIEW_IMAGE_EXTENSIONS: tuple[str, ...] = (".png",)

#: Типи для фільтра за операцією №2: «усі файли» або лише .java, .png.
FILTER_EXTENSIONS: tuple[str, ...] = (".java", ".png")

#: Атрибут сортування за варіантом (друга цифра -> атрибут №2).
VARIANT_SORT_ATTRIBUTE = "modified_at"

SORTABLE_ATTRIBUTES: tuple[str, ...] = (
    "name",
    "created_at",
    "modified_at",
    "uploaded_by",
    "edited_by",
    "size",
)


class SortOrder(str, Enum):
    NONE = "none"
    ASC = "asc"
    DESC = "desc"

    def next(self) -> "SortOrder":
        """Циклічне перемикання при кліку на заголовок стовпця: none -> asc -> desc -> none."""
        return {SortOrder.NONE: SortOrder.ASC, SortOrder.ASC: SortOrder.DESC, SortOrder.DESC: SortOrder.NONE}[self]


class PreviewKind(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    NONE = "none"


def extension_of(name: str) -> str:
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def preview_kind(name: str) -> PreviewKind:
    ext = extension_of(name)
    if ext in PREVIEW_TEXT_EXTENSIONS:
        return PreviewKind.TEXT
    if ext in PREVIEW_IMAGE_EXTENSIONS:
        return PreviewKind.IMAGE
    return PreviewKind.NONE


def _sort_key(attribute: str):
    if attribute not in SORTABLE_ATTRIBUTES:
        raise ValueError(f"Невідомий атрибут сортування: {attribute}")

    def key(f: FileRecord):
        value = getattr(f, attribute)
        if isinstance(value, str):
            return (value.casefold(), f.name.casefold())
        return (value, f.name.casefold())

    return key


def sort_files(
    files: Iterable[FileRecord],
    attribute: str = VARIANT_SORT_ATTRIBUTE,
    order: SortOrder | str = SortOrder.ASC,
) -> list[FileRecord]:
    """Сортує файли за атрибутом. ``SortOrder.NONE`` зберігає початковий порядок.

    Сортування стабільне; рядки порівнюються без урахування регістру,
    рівні значення впорядковуються за іменем файлу.
    """
    order = SortOrder(order)
    items = list(files)
    if order is SortOrder.NONE:
        return items
    return sorted(items, key=_sort_key(attribute), reverse=order is SortOrder.DESC)


def filter_files(files: Iterable[FileRecord], extension: str | None = None) -> list[FileRecord]:
    """Фільтр «усі файли» (``None``/``"all"``) або лише файли заданого типу з варіанта."""
    if extension in (None, "", "all"):
        return list(files)
    ext = extension.lower()
    if not ext.startswith("."):
        ext = "." + ext
    if ext not in FILTER_EXTENSIONS:
        raise ValueError(f"Тип {ext} не передбачено варіантом; дозволено: {', '.join(FILTER_EXTENSIONS)}")
    return [f for f in files if f.extension == ext]


def sort_and_filter(
    files: Sequence[FileRecord],
    extension: str | None = None,
    attribute: str = VARIANT_SORT_ATTRIBUTE,
    order: SortOrder | str = SortOrder.ASC,
) -> list[FileRecord]:
    return sort_files(filter_files(files, extension), attribute, order)
