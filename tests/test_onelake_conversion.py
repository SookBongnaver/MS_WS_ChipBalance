"""Exercise the OneLake export helper without a Spark session or cloud access."""
import ast
import types
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TimestampType:
    def simpleString(self):
        return "timestamp"


class StringType:
    def simpleString(self):
        return "string"


class DateType:
    def simpleString(self):
        return "date"


class UnsupportedType:
    def simpleString(self):
        return "unsupported"


class Column:
    def __init__(self, name, epoch_micros=False):
        self.name, self.epoch_micros = name, epoch_micros

    def alias(self, name):
        return Column(name, self.epoch_micros)


class Frame:
    def __init__(self, fields, rows, client_zone=timezone.utc):
        self.schema = types.SimpleNamespace(fields=fields)
        self.rows, self.client_zone = rows, client_zone

    def collect(self):
        rows = []
        for row in self.rows:
            values = {name: value.astimezone(self.client_zone).replace(tzinfo=None)
                      if isinstance(value, datetime) else value for name, value in row.items()}
            rows.append(types.SimpleNamespace(asDict=lambda values=values: dict(values)))
        return rows

    def select(self, columns):
        output = []
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        for row in self.rows:
            values = {}
            for column in columns:
                value = row[column.name]
                if value is not None and column.epoch_micros:
                    difference = value.astimezone(timezone.utc) - epoch
                    value = (difference.days * 86400 + difference.seconds) * 1000000 + difference.microseconds
                values[column.name] = value
            output.append(types.SimpleNamespace(asDict=lambda values=values: dict(values)))
        return types.SimpleNamespace(collect=lambda: output)


class OneLakeConversionTests(unittest.TestCase):
    def setUp(self):
        source = (ROOT / "src" / "notebooks" / "01_setup.py").read_text(encoding="utf-8")
        node = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "to_arrow")
        self.namespace = {
            "datetime": datetime, "timedelta": timedelta, "timezone": timezone,
            "T": types.SimpleNamespace(TimestampType=TimestampType),
            "F": types.SimpleNamespace(col=Column, unix_micros=lambda column: Column(column.name, True)),
            "ARROW_TYPES": {TimestampType: "timestamp[us, UTC]", StringType: "string", DateType: "date32"},
            "pa": types.SimpleNamespace(
                field=lambda name, kind: (name, kind), schema=lambda fields: fields,
                Table=types.SimpleNamespace(from_pylist=lambda rows, schema: types.SimpleNamespace(rows=rows, schema=schema))),
        }
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<to_arrow>", "exec"), self.namespace)

    def field(self, name, data_type):
        return types.SimpleNamespace(name=name, dataType=data_type)

    def test_timestamp_instant_is_independent_of_python_client_timezone(self):
        instant = datetime(2026, 10, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
        for zone in (timezone.utc, timezone(timedelta(hours=9)), timezone(timedelta(hours=-7))):
            with self.subTest(zone=zone):
                frame = Frame([self.field("detected_at", TimestampType())], [{"detected_at": instant}], zone)
                exported = self.namespace["to_arrow"](frame)
                self.assertEqual(instant, exported.rows[0]["detected_at"])
                self.assertEqual([("detected_at", "timestamp[us, UTC]")], exported.schema)

    def test_null_timestamp_and_non_timestamp_fields_are_preserved(self):
        fields = [self.field("id", StringType()), self.field("day", DateType()),
                  self.field("checked_at", TimestampType())]
        rows = [{"id": "p001", "day": date(2026, 10, 1), "checked_at": None}]
        self.assertEqual(rows, self.namespace["to_arrow"](Frame(fields, rows)).rows)

    def test_microseconds_before_epoch_are_preserved(self):
        instant = datetime(1969, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
        result = self.namespace["to_arrow"](
            Frame([self.field("checked_at", TimestampType())], [{"checked_at": instant}]))
        self.assertEqual(instant, result.rows[0]["checked_at"])

    def test_empty_frame_keeps_schema(self):
        result = self.namespace["to_arrow"](Frame([self.field("detected_at", TimestampType())], []))
        self.assertEqual([], result.rows)
        self.assertEqual([("detected_at", "timestamp[us, UTC]")], result.schema)

    def test_unsupported_type_has_actionable_error(self):
        with self.assertRaisesRegex(TypeError, "payload unsupported"):
            self.namespace["to_arrow"](Frame([self.field("payload", UnsupportedType())], []))


if __name__ == "__main__":
    unittest.main()
