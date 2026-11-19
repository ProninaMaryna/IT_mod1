"""Тести view-моделі десктоп-клієнта: стовпці, сортування кліком по заголовку, фільтр, операції."""
import pytest

from cloudfolder.core.variant import SortOrder
from cloudfolder.desktop.viewmodel import COLUMNS, FILTER_OPTIONS, FilesViewModel


@pytest.fixture
def vm(fake_api):
    for name in ["a.java", "b.png", "c.xml"]:
        fake_api.upload(name, name.encode())
    model = FilesViewModel(fake_api)
    model.refresh()
    return model


def test_name_column_cannot_be_hidden(vm):
    assert "size" in [c.key for c in COLUMNS]  # усі стовпці, крім імені, приховувані
    vm.set_all_optional_columns(False)
    assert vm.is_column_visible("name")
    assert all(not vm.is_column_visible(c.key) for c in COLUMNS if c.key != "name")
    vm.set_all_optional_columns(True)
    assert all(vm.is_column_visible(c.key) for c in COLUMNS)


def test_header_click_cycles_sort(vm):
    assert vm.sort_order is SortOrder.NONE
    assert vm.toggle_sort("modified_at") is SortOrder.ASC
    assert vm.toggle_sort("modified_at") is SortOrder.DESC
    assert vm.toggle_sort("modified_at") is SortOrder.NONE
    assert vm.toggle_sort("name") is SortOrder.ASC  # новий стовпець починає з ▲


def test_filter_options_follow_variant(vm):
    assert [v for v, _ in FILTER_OPTIONS] == ["all", ".java", ".png"]
    vm.set_filter(".png")
    assert [f.name for f in vm.displayed_files] == ["b.png"]
    with pytest.raises(ValueError):
        vm.set_filter(".xml")


def test_upload_and_delete_refresh_list(vm, fake_api):
    vm.upload("d.png", b"x")
    assert len(vm.files) == 4
    vm.delete(next(f for f in vm.files if f.name == "a.java"))
    assert sorted(f.name for f in vm.files) == ["b.png", "c.xml", "d.png"]
    assert ("delete", "a.java") in fake_api.calls
