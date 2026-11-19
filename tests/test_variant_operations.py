"""Тести операції варіанта 12: сортування за датою модифікації (▲/▼) та фільтр «усі / .java / .png»;
перегляд вмісту .xml (текст) / .png (зображення)."""
import pytest

from cloudfolder.core import variant
from cloudfolder.core.variant import PreviewKind, SortOrder, filter_files, preview_kind, sort_and_filter, sort_files
from tests.conftest import make_record

FILES = [
    make_record(1, "Main.java", minutes=30),
    make_record(2, "logo.png", minutes=10),
    make_record(3, "config.xml", minutes=50),
    make_record(4, "notes.txt", minutes=20),
    make_record(5, "Util.JAVA", minutes=40),
    make_record(6, "diagram.png", minutes=0),
]


def names(files):
    return [f.name for f in files]


def test_variant_sort_attribute_is_modification_date():
    assert variant.VARIANT_SORT_ATTRIBUTE == "modified_at"


def test_sort_by_modified_ascending():
    result = sort_files(FILES, "modified_at", SortOrder.ASC)
    assert names(result) == ["diagram.png", "logo.png", "notes.txt", "Main.java", "Util.JAVA", "config.xml"]


def test_sort_by_modified_descending():
    result = sort_files(FILES, "modified_at", "desc")
    assert names(result) == ["config.xml", "Util.JAVA", "Main.java", "notes.txt", "logo.png", "diagram.png"]


def test_sort_none_keeps_original_order():
    assert names(sort_files(FILES, "modified_at", SortOrder.NONE)) == names(FILES)


def test_sort_ties_are_broken_by_name():
    tie = [make_record(1, "b.png", minutes=5), make_record(2, "A.png", minutes=5)]
    assert names(sort_files(tie, "modified_at", "asc")) == ["A.png", "b.png"]


def test_filter_all_returns_everything():
    assert len(filter_files(FILES, "all")) == len(FILES)
    assert len(filter_files(FILES, None)) == len(FILES)


def test_filter_java_is_case_insensitive():
    assert names(filter_files(FILES, ".java")) == ["Main.java", "Util.JAVA"]


def test_filter_png():
    assert names(filter_files(FILES, "png")) == ["logo.png", "diagram.png"]


def test_filter_rejects_types_outside_variant():
    with pytest.raises(ValueError):
        filter_files(FILES, ".xml")


def test_filter_and_sort_compose():
    result = sort_and_filter(FILES, ".png", "modified_at", SortOrder.DESC)
    assert names(result) == ["logo.png", "diagram.png"]


def test_sort_order_cycles():
    assert SortOrder.NONE.next() is SortOrder.ASC
    assert SortOrder.ASC.next() is SortOrder.DESC
    assert SortOrder.DESC.next() is SortOrder.NONE


@pytest.mark.parametrize(
    "name,kind",
    [
        ("pom.xml", PreviewKind.TEXT),
        ("LAYOUT.XML", PreviewKind.TEXT),
        ("photo.png", PreviewKind.IMAGE),
        ("Main.java", PreviewKind.NONE),
        ("photo.jpg", PreviewKind.NONE),
        ("xml", PreviewKind.NONE),
    ],
)
def test_preview_kind(name, kind):
    assert preview_kind(name) is kind
