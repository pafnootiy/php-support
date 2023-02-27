from django.contrib import admin

from . import models


# class OrderInline(admin.TabularInline):
#    model = models.
#    extra = 0
    
   
@admin.register(models.Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ['chat_id', 'dialogue_state']
    list_display_links = ['chat_id']
    search_fields = ['chat_id']
    

@admin.register(models.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'chat', 'expiration_at']
    list_display_links = ['name']
    search_fields = ['name']


@admin.register(models.Developer)
class DeveloperAdmin(admin.ModelAdmin):
    list_display = ['name', 'chat', 'work_allowed']
    list_display_links = ['name']
    search_fields = ['name']
#    inlines = [OrderInline]

    
@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'client', 'number', 'is_published', 'developer', 'finished_at']
    list_display_links = ['title']
    search_fields = ['title']
    readonly_fields = ['created_at']

