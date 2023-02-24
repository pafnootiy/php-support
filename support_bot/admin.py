from django.contrib import admin

from .models import Chat, Order, Storage

admin.site.register(Chat)
admin.site.register(Order)
admin.site.register(Storage)

