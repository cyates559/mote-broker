# Generated by Django 4.2.1 on 2024-02-11 03:58

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Message",
            fields=[
                ("topic", models.TextField(primary_key=True, serialize=False)),
                ("data", models.BinaryField(default=None, null=True)),
                ("qos", models.PositiveIntegerField(default=None, null=True)),
            ],
        ),
    ]
