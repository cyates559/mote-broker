import os

from pytest import fixture


@fixture
def db():
    import django
    os.environ["DJANGO_SETTINGS_MODULE"] = "db.settings"
    django.setup()
    yield django

