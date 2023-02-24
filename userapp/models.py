from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Chat(models.Model):
    """Чат в Telegram."""
    chat_id = models.CharField('Telegram Id чата с пользователем',
                               max_length=64, db_index=True,
                               null=False,
                               blank=False
                               )
    dialogue_state = models.CharField('Этап диалога пользователя с ботом',
                                      default='START',
                                      max_length=96
                                      )
class Order(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateField(auto_now_add=True)
    update_at = models.DateField(auto_now=True)
    is_published = models.BooleanField(default=True)

class Storage(models.Model):
    message = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)