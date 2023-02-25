from django.db import models


class Chat(models.Model):
    """Чат в Telegram."""

    chat_id = models.CharField('Telegram Id чата с пользователем',
                               max_length=64,
                               unique=True,
                               null=False,
                               blank=False)
    dialogue_state = models.CharField('Этап диалога пользователя с ботом',
                                      max_length=64,
                                      default='START')
    
    @classmethod
    def get_dialogue_state(cls, chat_id):
        """Получает из БД состояние диалога для чата."""

        count = cls.objects.filter(chat_id=chat_id).count()
        if count != 1:
            return None

        chats = cls.objects.filter(chat_id=chat_id)
        return chats[0].dialogue_state
        
    @classmethod
    def update_dialogue_state(cls, chat_id, dialogue_state):
        """Изменяет в БД состояние диалога для чата."""

        if cls.objects.filter(chat_id=chat_id).count() != 1:
            return None
 
        cls.objects.filter(chat_id=chat_id).update(dialogue_state=dialogue_state)
        return dialogue_state
    

class Storage(models.Model):
    message = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)


class Developer(models.Model):
    name = models.CharField('Фио', max_length=200)
    chat = models.OneToOneField(Chat, on_delete=models.CASCADE,
                             related_name='chats', blank=True,verbose_name='Чат')
    work_allowed = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Order(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateField(auto_now_add=True)
    update_at = models.DateField(auto_now=True)
    is_published = models.BooleanField(default=True)
    developer = models.ForeignKey(Developer,on_delete=models.CASCADE,
                              related_name='orders',verbose_name='Заявка')
    take_order = models.BooleanField('Беру заказ', default=False)
