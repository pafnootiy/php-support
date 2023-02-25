from django.contrib import admin

from .models import Chat, Client, Developer, Order, Storage

admin.site.register(Chat)
admin.site.register(Client)
admin.site.register(Developer)
admin.site.register(Order)
admin.site.register(Storage)

