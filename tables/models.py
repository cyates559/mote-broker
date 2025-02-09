import json
from collections import OrderedDict

from django.db.models import Model as Model, Field, CharField, PositiveIntegerField, IntegerField, URLField, BinaryField
from django.core.management import call_command

from logger import log
from tables.exceptions import CorruptModelError

field_class_map = {
    "char": CharField,
    "uint": PositiveIntegerField,
    "int": IntegerField,
    "url": URLField,
    "bytes": BinaryField,
}


def parse_field(field_name: str, type_name: str, **field_attrs) -> Field:
    type_class = field_class_map.get(type_name, None)
    if type_class is None:
        raise TypeError(f"Field {field_name} has invalid type: {type_name}")
    field = type_class(**field_attrs)
    return field


def parse_fields(fields: OrderedDict) -> OrderedDict:
    result = OrderedDict()
    for field_name, (type_name, field_attrs) in fields.items():
        result[field_name] = parse_field(field_name, type_name, **field_attrs)
    return result


def parse_model_name(topic: str):
    name = topic.replace("/", "_").replace("+", "").replace("#", "")
    return name


def create_model_class(topic: str, fields: OrderedDict) -> type[Model]:
    model_name = parse_model_name(topic)
    attrs = parse_fields(fields)
    attrs["__module__"] = "tables.models"
    clazz = type(model_name, (Model,), attrs)
    # noinspection PyTypeChecker
    return clazz


class TableMeta(Model):
    name: str = CharField(primary_key=True, max_length=300)
    topic: str = CharField(max_length=600)
    field_bytes: bytes = BinaryField(default="{}".encode())

    app_name = "tables"

    @classmethod
    def create_table(cls, topic_str: str, field_data: bytes) -> type[Model]:
        table = TableMeta(
            name=parse_model_name(topic_str),
            topic=topic_str,
            field_bytes=field_data,
        )
        log.debug("TABLE", table, table.app_name)
        # Check that the model can be built
        model = table.build()
        table.save()
        call_command("makemigrations", table.app_name)
        call_command("migrate", table.app_name)
        return model

    def drop(self):
        self.delete()

    def build(self) -> type[Model]:
        try:
            fields = json.loads(self.field_bytes.decode())
        except json.JSONDecodeError:
            raise CorruptModelError("Could not parse JSON")
        return create_model_class(self.topic, fields)

    class Meta:
        unique_together = (("name", "topic"),)
