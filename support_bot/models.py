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

    class Meta:
        verbose_name = 'чат в Telegram'
        verbose_name_plural = 'чаты в Telegram'

    def __str__(self):
        return self.chat_id
  
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

    name = models.CharField('ФИО', max_length=200)
    chat = models.OneToOneField(
        Chat,
        verbose_name='Чат в Telegram',
        on_delete=models.CASCADE,
        related_name='chats',
        blank=True,
    )
    work_allowed = models.BooleanField('Разрешено ли работать', default=False)
   
    class Meta:
        verbose_name = 'программист'
        verbose_name_plural = 'программисты'

    def __str__(self):
        return self.name


class Client(models.Model):
    """Заказчик."""

    name = models.CharField('ФИО', max_length=200)
    chat = models.OneToOneField(
        Chat,
        verbose_name='Чат в Telegram',
        on_delete=models.PROTECT
    )
    expiration_at = models.DateField('Дата окончания обслуживания', null=True, blank=True)
   
    class Meta:
        verbose_name = 'заказчик'
        verbose_name_plural = 'заказчики'

    def __str__(self):
        return self.name
    

class Order(models.Model):
    """Заказ."""

    number = models.IntegerField('Номер', db_index=True)
    title = models.CharField('Название', max_length=150)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField('Время создания', db_index=True, auto_now_add=True)
    client = models.ForeignKey(
        Client,
        related_name='orders',
        verbose_name='Заказчик',
        on_delete=models.PROTECT
    )
    published_at = models.DateTimeField('Время публикации', null=True, blank=True, auto_now=False)
    developer = models.ForeignKey(
        Developer,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Программист',
        null=True,
        blank=True      
    )
    finished_at = models.DateTimeField('Время завершения', null=True, blank=True, auto_now=False)

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return self.title
        

class Storage(models.Model):
    message = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

