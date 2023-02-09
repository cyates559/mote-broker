from django.contrib import admin

from persistence.models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "topic",
        "data",
    )
