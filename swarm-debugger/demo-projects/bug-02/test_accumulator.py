import pytest
from accumulator import QueryBuilder


def test_first_query():
    q1 = QueryBuilder("users")
    q1.add_filter("active", "true")
    assert q1.build() == "SELECT * FROM users WHERE active = 'true'"


def test_consecutive_isolated_query():
    # Calling QueryBuilder again should NOT inherit previous filters from test_first_query
    q2 = QueryBuilder("orders")
    assert q2.build() == "SELECT * FROM orders"
