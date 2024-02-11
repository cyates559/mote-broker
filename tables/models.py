from django.db.models import Model, CharField

attrs = {
    'name': CharField(max_length=32),
    '__module__': 'tables.models'
}
Animal = type("Animal", (Model,), attrs)
