from django.contrib import admin

from .models import Chat, Client, Order, Storage

admin.site.register(Chat)
admin.site.register(Client)
admin.site.register(Order)
admin.site.register(Storage)

