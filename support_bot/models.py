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
    
class Developer(models.Model):
    """Программист."""

    name = models.CharField('Фио', max_length=200)
    chat = models.OneToOneField(
        Chat,
        verbose_name='Чат',
        on_delete=models.CASCADE,
        related_name='chats',
        blank=True,
    )
    approve = models.BooleanField(default=True) # work_allowed = models.BooleanField('Разрешено ли работать', default=False)

    def __str__(self):
        return self.name

# class Client(models.Model):
#    """Заказчик."""

#    chat = models.OneToOneField(
#        Chat,
#        verbose_name='Связанный чат',
#        on_delete=models.PROTECT
#    )
#    expiration_at = models.DateField('Когда истекает срок обслуживания', null=True, blank=True)
    

class Order(models.Model):
    """Заказ."""

    title = models.CharField(max_length=150) # models.CharField('Название', max_length=150)
    description = models.TextField(blank=True) # models.TextField('Описание', blank=True)
    created_at = models.DateField(auto_now_add=True) # models.DateField('Дата создания', auto_now_add=True)
    update_at = models.DateField(auto_now=True) # client = models.ForeignKey(
#        Client,
#        related_name='orders',
#        verbose_name='Создан заказчиком',
#        on_delete=models.PROTECT
#    )
    is_published = models.BooleanField(default=True) # Удалить
    developer = models.ForeignKey(
        Developer,
        on_delete=models.CASCADE, # models.PROTECT
        related_name='orders',
        verbose_name='Заявка'  # 'Кто разрабатывает',
#        
    )
    take_order = models.BooleanField('Беру заказ', default=False) # Удалить
#    finished_at = models.DateField('Дата завершения', auto_now=False)

class Storage(models.Model):
    message = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

