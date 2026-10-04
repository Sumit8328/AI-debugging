import pytest
from processor import slice_batch


def test_standard_batch():
    assert slice_batch([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_boundary_exact_match():
    # If items length is exactly multiple of batch_size, should have exactly 2 chunks, no trailing empty list
    result = slice_batch([1, 2, 3, 4, 5, 6], 3)
    assert result == [[1, 2, 3], [4, 5, 6]]


def test_empty_input():
    assert slice_batch([], 2) == []


def test_single_item():
    assert slice_batch([42], 5) == [[42]]


def test_zero_or_negative_batch_size():
    with pytest.raises(ValueError):
        slice_batch([1, 2, 3], batch_size=0)
