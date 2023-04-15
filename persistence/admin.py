from django.contrib import admin

from persistence.models import RetainedMessage


@admin.register(RetainedMessage)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "topic",
        "data",
    )
