from sqlalchemy import inspect, text
from sqlalchemy.exc import NoSuchTableError

from app.database.database import get_database_engine

_KEY_COLUMNS = """
    SELECT TABLE_SCHEMA AS source_schema,
           TABLE_NAME AS source_table,
           CONSTRAINT_NAME AS constraint_name,
           COLUMN_NAME AS source_column,
           REFERENCED_TABLE_SCHEMA AS target_schema,
           REFERENCED_TABLE_NAME AS target_table,
           REFERENCED_COLUMN_NAME AS target_column
    FROM information_schema.KEY_COLUMN_USAGE
"""
_KEY_ORDER = "ORDER BY TABLE_SCHEMA, TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION"

_DIRECT_RELATIONS = text(f"""
    {_KEY_COLUMNS}
    WHERE REFERENCED_TABLE_NAME IS NOT NULL
      AND (
          (TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name)
          OR (REFERENCED_TABLE_SCHEMA = :schema AND REFERENCED_TABLE_NAME = :table_name)
      )
    {_KEY_ORDER}
""")

_SCHEMA_KEYS = text(f"""
    {_KEY_COLUMNS}
    WHERE TABLE_SCHEMA = :schema
      AND (CONSTRAINT_NAME = 'PRIMARY' OR REFERENCED_TABLE_NAME IS NOT NULL)
    {_KEY_ORDER}
""")

_SCHEMA_COLUMNS = text("""
    SELECT TABLE_SCHEMA AS table_schema, TABLE_NAME AS table_name,
           COLUMN_NAME AS column_name, COLUMN_TYPE AS column_type
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = :schema
    ORDER BY TABLE_NAME, ORDINAL_POSITION
""")


def list_tables() -> dict:
    with get_database_engine().connect() as connection:
        inspector = inspect(connection)
        return {
            "database": inspector.default_schema_name,
            "tables": sorted(inspector.get_table_names()),
        }


def get_table_schema(name: str) -> dict:
    with get_database_engine().connect() as connection:
        inspector = inspect(connection)
        database = inspector.default_schema_name
        if name not in inspector.get_table_names():
            raise NoSuchTableError(name)
        columns = inspector.get_columns(name)
        primary_key = inspector.get_pk_constraint(name)["constrained_columns"]
        rows = connection.execute(_DIRECT_RELATIONS, {"schema": database, "table_name": name}).mappings()
        relations = _collect_relations(
            row for row in rows
            if (database, name) in (
                (row["source_schema"], row["source_table"]),
                (row["target_schema"], row["target_table"]),
            )
        )

    foreign_key_columns = {
        pair["source"]
        for relation in relations
        if relation["source"] == {"schema": database, "table": name}
        for pair in relation["columns"]
    }
    return {
        "database": database,
        "table": name,
        "columns": [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column["nullable"],
                "default": column.get("default"),
                "comment": column.get("comment"),
                "primaryKey": column["name"] in primary_key,
                "foreignKey": column["name"] in foreign_key_columns,
            }
            for column in columns
        ],
        "relations": relations,
    }


def get_schema_diagram() -> dict:
    with get_database_engine().connect() as connection:
        inspector = inspect(connection)
        database = inspector.default_schema_name
        tables = {name: {} for name in sorted(inspector.get_table_names())}
        if not tables:
            return {"database": database, "tables": [], "relations": []}

        params = {"schema": database}
        keys = connection.execute(_SCHEMA_KEYS, params).mappings()
        primary_keys = set()
        foreign_keys = set()
        local_foreign_keys = []
        for row in keys:
            if row["source_schema"] != database or row["source_table"] not in tables:
                continue
            field = (row["source_table"], row["source_column"])
            if row["target_table"] is None:
                primary_keys.add(field)
                continue
            foreign_keys.add(field)
            if row["target_schema"] == database and row["target_table"] in tables:
                local_foreign_keys.append(row)

        columns = connection.execute(_SCHEMA_COLUMNS, params).mappings()
        for row in columns:
            table, name = row["table_name"], row["column_name"]
            if row["table_schema"] == database and table in tables:
                tables[table][name] = {
                    "name": name,
                    "type": row["column_type"],
                    "primaryKey": (table, name) in primary_keys,
                    "foreignKey": (table, name) in foreign_keys,
                }

    relations = [
        relation for relation in _collect_relations(local_foreign_keys)
        if all(
            pair["source"] in tables[relation["source"]["table"]]
            and pair["target"] in tables[relation["target"]["table"]]
            for pair in relation["columns"]
        )
    ]
    return {
        "database": database,
        "tables": [{"name": name, "columns": list(fields.values())} for name, fields in tables.items()],
        "relations": relations,
    }


def _collect_relations(rows) -> list[dict]:
    relations = {}
    for row in rows:
        source = (row["source_schema"], row["source_table"])
        target = (row["target_schema"], row["target_table"])
        key = (*source, row["constraint_name"])
        if key not in relations:
            relations[key] = {
                "name": row["constraint_name"],
                "source": {"schema": source[0], "table": source[1]},
                "target": {"schema": target[0], "table": target[1]},
                "columns": [],
            }
        relations[key]["columns"].append({"source": row["source_column"], "target": row["target_column"]})
    return list(relations.values())
