from django.db.models import (
    Model,
    TextField,
    BinaryField,
    PositiveIntegerField,
    Manager,
)


class Message(Model):
    objects = Manager()

    topic = TextField(primary_key=True)
    data = BinaryField(null=True, default=None)
    qos = PositiveIntegerField(default=None, null=True)

    class Meta:
        app_label = "persistence"
