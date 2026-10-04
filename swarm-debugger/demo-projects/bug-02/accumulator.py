class QueryBuilder:
    """
    SQL-like query filter builder.
    BUG: Default mutable argument filters=[] retains filter state across calls.
    """
    def __init__(self, table_name: str, filters: list = []):
        self.table_name = table_name
        self.filters = filters

    def add_filter(self, column: str, value: str):
        self.filters.append(f"{column} = '{value}'")
        return self

    def build(self) -> str:
        base = f"SELECT * FROM {self.table_name}"
        if self.filters:
            return f"{base} WHERE " + " AND ".join(self.filters)
        return base
