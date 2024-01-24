from django.contrib import admin

from tree.models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "topic",
        "data",
    )
