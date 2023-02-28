# TODO: Раскомментировать после отладки
# import logging
from contextlib import suppress
from datetime import date, datetime
from functools import partial
from textwrap import dedent

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import Max, Q
from django.utils import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters, MessageHandler, Updater

from ...models import Chat, Client, Developer, Order, Message

# TODO: Раскомментировать после отладки
# logger = logging.getLogger(__file__)


START = 'START'
MAIN_MENU = 'MAIN_MENU'
CLIENT_BASE_MENU = 'CLIENT_BASE_MENU'
CLIENT_NEW_ORDER_TITLE = 'CLIENT_NEW_ORDER_TITLE'
CLIENT_ADD_ORDER_DESCRIPTION = 'CLIENT_ADD_ORDER_DESCRIPTION'
CLIENT_ORDER_CHOICE = 'CLIENT_ORDER_CHOICE'
DEVELOPER_BASE_MENU = 'DEVELOPER_BASE_MENU'
DEVELOPER_SELECT_ORDER = 'DEVELOPER_SELECT_ORDER'
DEVELOPER_ADD_QUESTION_ORDER = 'DEVELOPER_ADD_QUESTION_ORDER'


class Command(BaseCommand):
    help = 'Команда организации работы Telegram-бота в приложении Django.'
    
    def __init__(self):
        super().__init__()
        # TODO: Раскомментировать после отладки
        #logging.basicConfig(
        #    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        #    level=logging.INFO
        #    filename='support_bot.log',
        #    filemode='w'
        #)

        self.updater = Updater(token=settings.TELEGRAM_BOT_TOKEN)
        self.dispatcher = self.updater.dispatcher

        handler = self.handle_user_action
        self.dispatcher.add_handler(CallbackQueryHandler(handler))
        self.dispatcher.add_handler(MessageHandler(Filters.text, handler))
        self.dispatcher.add_handler(CommandHandler('start', handler))
        # TODO: Раскомментировать после отладки
        # self.dispatcher.add_error_handler(self.handle_error)
        
        self.states_handlers = {
            START: self.handle_start_command,
            CLIENT_NEW_ORDER_TITLE: self.handle_new_order_title,
            CLIENT_ADD_ORDER_DESCRIPTION: self.handle_add_order_description,
            DEVELOPER_ADD_QUESTION_ORDER: self.handle_add_question_order,
        }

    def handle(self, *args, **kwargs):
        """Прослушивает сообщения в Telegram."""
        
        self.updater.start_polling()
        self.updater.idle()
        
    def handle_user_action(self, update, context):
        """Обрабатывает действие пользователя в чате."""

        chat_id = update.effective_chat.id
        if update.message:
            user_reply = update.message.text
            dialogue_state = START if user_reply == '/start' else self.get_dialogue_state(chat_id) or START
            state_handler = self.states_handlers[dialogue_state]
        elif update.callback_query:
            # Обязательная команда (см. https://core.telegram.org/bots/api#callbackquery)
            update.callback_query.answer()     
            user_reply = update.callback_query.data
            state_handler = self.handle_button
        else:
            return
 
        next_dialogue_state = state_handler(update, context)
        self.update_dialogue_state_in_db(chat_id, next_dialogue_state)
        
    def get_dialogue_state(self, chat_id):
        """Получает из БД состояние диалога в чатe."""

        dialogue_state = Chat.get_dialogue_state(chat_id=chat_id)
        if dialogue_state is None:
            dialogue_state = START
            Chat.objects.get_or_create(chat_id=chat_id, dialogue_state=dialogue_state)
        return dialogue_state
                
    def update_dialogue_state_in_db(self, chat_id, dialogue_state):
        """Обновляет в БД состояние диалога в чате."""

        dialogue_state_from_db = Chat.update_dialogue_state(
            chat_id=chat_id,
            dialogue_state=dialogue_state
        )

        if dialogue_state_from_db is None:
            chat, _ = Chat.objects.get_or_create(chat_id=chat_id)
            dialogue_state_from_db = chat.dialogue_state

        if dialogue_state_from_db != dialogue_state:
            dialogue_state_from_db = Chat.update_dialogue_state(
                chat_id=chat_id,
                dialogue_state=dialogue_state
            )
        return dialogue_state_from_db

    def handle_start_command(self, update, context):
        """Обрабатывает состояние START."""
        
        query = update.callback_query
        if not query:
            with suppress(BadRequest):
                context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id-1
                )

        keyboard = [[
            InlineKeyboardButton('Заказчик', callback_data='client'),
            InlineKeyboardButton('Программист', callback_data='developer')
        ]]      
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Кто вы?',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return MAIN_MENU

    def handle_button(self, update, context):
        """Обрабатывает нажатие кнопок."""

        variant = update.callback_query.data
        methods = {
            'main_menu': self.handle_start_command,
            'client': self.handle_client_button,
            'developer': self.handle_developer_button,
            'client_new_order': self.handle_client_new_order_button,
            'client_orders': self.handle_client_orders_button,
            'developer_agreement': self.handle_developer_agreement,
            'developer_registration': self.handle_developer_registration,
            'show_free_orders': self.handle_show_free_orders,
            'handle_show_order': self.handle_show_order,
            'handle_select_free_order': self.handle_select_free_order,
            'show_work_orders': self.handle_show_work_orders,
            'show_work_order': self.handle_show_work_order,
            'make_done_order': self.handle_make_done_order,
            'show_history_orders': self.handle_show_history_orders,
            'make_question_order': self.handle_make_question_order,
            'developer_account': self.handle_developer_account,
        }

        if variant in methods:
            return methods[variant](update, context)
            
        methods = {
            'client_order_choice_': self.send_client_order_details,
        }
        for method in methods:
            length = len(method)
            if len(variant) > length and variant[:length] == method:
                return methods[method](update, context)

        return self.handle_show_order(update, context)
        
    def handle_client_button(self, update, context):
        """Обрабатывает нажатие кнопки 'Заказчик' в главном меню."""

        if not self.check_payment(update, context):
            return self.send_message_about_payment(update, context)
        
        keyboard = [[self.get_new_order_button(), self.get_my_orders_button()],[self.get_main_menu_button()]]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите желаемое действие.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENT_BASE_MENU
        
    @staticmethod
    def get_new_order_button():
        return InlineKeyboardButton('Создать заказ', callback_data='client_new_order')

    @staticmethod
    def get_my_orders_button():
        return InlineKeyboardButton('Мои заказы', callback_data='client_orders')
        
    @staticmethod
    def get_main_menu_button():
        return InlineKeyboardButton('«‎ Вернуться в главное меню', callback_data='main_menu')

    def check_payment(self, update, context):
        """Проверяет, оплатил ли Заказчик предоставление услуг."""

        chat_id = update.effective_chat.id
        count = Client.objects.filter(chat__chat_id=chat_id, expiration_at__gte=date.today()).count()
        return count == 1

    def send_message_about_payment(self, update, context):
        """Посылает в чат Заказчика сообщение о необходимости оплатить услуги."""

        keyboard = [[InlineKeyboardButton('«‎ Вернуться в главное меню', callback_data='main_menu')]]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Оплатите, пожалуйста, наши услуги и затем вернитесь в чат.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return START

    def handle_client_new_order_button(self, update, context):
        """Обрабатывает нажатие Заказчиком кнопки 'Создать заказ'."""

        if not self.check_payment(update, context):
            return self.send_message_about_payment(update, context)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Введите Название заказа'
        )
        return CLIENT_NEW_ORDER_TITLE
 
    def handle_new_order_title(self, update, context):
        """Принимает от Заказчика ввод названия нового заказа."""

        if not self.check_payment(update, context):
            return self.send_message_about_payment(update, context)
        
        title = update.message.text.strip()
        if len(title) < 4:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Слишком короткое Название заказа.\nВведите Название заказа'
            )
            return CLIENT_NEW_ORDER_TITLE

        chat_id = update.effective_chat.id
        client = Client.objects.get(chat__chat_id=chat_id)
        max_orders_number = Order.objects.filter(client=client).aggregate(Max('number')).get('number__max')
        order_number = max_orders_number+1 if max_orders_number else 1
        Order.objects.create(number=order_number, title=title, description='', client=client)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Введите Описание заказа.'
        )
        context.user_data['order_number'] = order_number
        # return self.send_client_order_details(update, context)
        return CLIENT_ADD_ORDER_DESCRIPTION
        
    def handle_add_order_description(self, update, context):
        """Принимает от Заказчика ввод описания заказа."""
 
        if not self.check_payment(update, context):
            return self.send_message_about_payment(update, context)
            
        description = update.message.text.strip()
        chat_id = update.effective_chat.id        
        order_number = context.user_data['order_number']
        orders = Order.objects.filter(client__chat__chat_id=chat_id, number=order_number)
        if not orders:
            return self.send_client_message_order_not_exist(update, context)

        order = orders[0]
        order.description = description
        order.published_at = datetime.now()
        order.save()
        
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Заказ создан.'
        )
        return self.send_client_order_details(update, context)
         
    def send_client_order_details(self, update, context):
        """Отправляет в чат детали заказа для Заказчика."""
        
        chat_id = update.effective_chat.id
        order_number = self.get_order_number_from_bot(update, context)
        orders = (
            Order.objects
                 .filter(client__chat__chat_id=chat_id, number=order_number, published_at__isnull=False)
                 .select_related('developer')
        )    
        if not orders:
            context.user_data['order_number'] = order_number
            return self.send_client_message_order_not_exist(update, context)

        order = orders[0]
        created_at = f'{order.created_at}'[:16]
        text = (
            f'*Заказ № {order.number}*\n'
            f'*{order.title}*\n'
            f'Создан: {created_at}\n'
        )

        developer_name = order.developer.name if order.developer else '-'
        text = f'{text}Исполнитель: {developer_name}\n'           
        if order.finished_at:
            finished_at = f'{order.finished_at}'[:16]
            text = f'{text}Завершён: {finished_at}\n'
        text = f'{text}\n{order.description}'

        keyboard = [[self.get_new_order_button(), self.get_my_orders_button()],[self.get_main_menu_button()]]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENT_BASE_MENU

    def get_order_number_from_bot(self, update, context):
        """Извлекает номер заказа из бота."""

        if 'order_number' in context.user_data:
            return context.user_data.pop('order_number')
 
        query_data = update.callback_query.data
        return int(query_data[query_data.rfind('_')+1:])
      
    def send_client_message_order_not_exist(self, update, context):
        """Посылает в чат сообщение об отсутствии выбранного заказа для Заказчика."""
        
        order_number = context.user_data.pop('order_number')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Заказа № {order_number} не существует. Обратитесь к администратору.'
        )
        return self.handle_client_button(update, context)

    def handle_client_orders_button(self, update, context):
        """Обрабатывает нажатие Заказчиком кнопки 'Мои заказы'."""

        chat_id = update.effective_chat.id
        orders = Order.objects.filter(client__chat__chat_id=chat_id, published_at__isnull=False).order_by('number')
        if not orders:
            return self.send_client_message_orders_not_exist(update, context)

        keyboard = [
            [
                InlineKeyboardButton(
                    f'{order.number}. {order.title}',
                    callback_data=f'client_order_choice_{order.number}')
            ]
            for order in orders
        ]
        keyboard.append([InlineKeyboardButton('«‎ Вернуться в меню Заказчика', callback_data='client')])

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите заказ для просмотра.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENT_ORDER_CHOICE

    def send_client_message_orders_not_exist(self, update, context):
        """Посылает в чат сообщение об отсутствии заказов у Заказчика."""
        
        order_number = context.user_data.pop('order_number')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'У вас пока нет заказов.'
        )
        return self.handle_client_button(update, context)
   
    def handle_developer_button(self, update, context):
        """Обрабатывает нажатие кнопки 'Программист' в главном меню."""

        keyboard = [
            [
                InlineKeyboardButton('Аккаунт', callback_data='developer_account'),
            ],
            [
                InlineKeyboardButton('Cвободные заказы', callback_data='show_free_orders'),
                InlineKeyboardButton('Заказы в работе', callback_data='show_work_orders'),
            ],
            [
                InlineKeyboardButton('Смотреть историю выполненных заказов', callback_data='show_history_orders'),
            ],
            [
                InlineKeyboardButton('<< Назад', callback_data='main_menu'),
            ],
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите желаемое действие.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEVELOPER_BASE_MENU

    def handle_developer_account(self, update, context):
        keyboard = [
            [
                InlineKeyboardButton('Условия работы', callback_data='developer_agreement'),
            ],
            [
                InlineKeyboardButton('Регистрация', callback_data='developer_registration'),
            ],
            [
                InlineKeyboardButton('<< Назад', callback_data='developer'),
            ],
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите желаемое действие.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEVELOPER_BASE_MENU

    def handle_show_history_orders(self, update, context):

        keyboard = []

        try:
            developer = Developer.objects.get(chat__chat_id=update.effective_chat.id)
        except ObjectDoesNotExist:
            message = 'Вы не зарегистрированные в боте'
            keyboard.append([InlineKeyboardButton('Назад', callback_data='developer')])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DEVELOPER_BASE_MENU

        query = Q(developer=developer) & Q(finished_at__isnull=False)
        orders = Order.objects.filter(query)

        if not orders:
            message = 'У вас нет выполненных заказов в истории'
            keyboard.append([InlineKeyboardButton('<< Назад', callback_data='developer')])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DEVELOPER_BASE_MENU

        orders = [str(count+1) + ' ' + order.title + ' ' + order.finished_at.strftime('%m/%d/%Y, %H:%M:%S') for count, order in enumerate(orders)]

        message = '\n'.join(orders)

        keyboard.append([InlineKeyboardButton('<< Назад', callback_data='developer')])

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DEVELOPER_BASE_MENU

    def handle_show_work_orders(self, update, context):

        keyboard = []

        try:
            developer = Developer.objects.get(chat__chat_id=update.effective_chat.id)
        except ObjectDoesNotExist:
            message = 'Вы не зарегистрированные в боте'
            keyboard.append([InlineKeyboardButton('Назад', callback_data='developer')])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DEVELOPER_BASE_MENU

        query = Q(developer=developer) & Q(finished_at__isnull=True)
        orders = Order.objects.filter(query)

        if not orders:
            message = 'У вас нет заказов в работе'
            keyboard.append([InlineKeyboardButton('<< Назад', callback_data='developer')])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DEVELOPER_BASE_MENU

        for order in orders:
            context.user_data['order_id'] = order.pk
            keyboard.append([InlineKeyboardButton(order.title, callback_data='show_work_order')])
        keyboard.append([InlineKeyboardButton('<< Назад', callback_data='developer')])

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Ваши заказы в работе',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DEVELOPER_BASE_MENU

    def handle_show_work_order(self, update, context):

        keyboard = []

        try:
            order = Order.objects.get(pk=context.user_data['order_id'])
        except ObjectDoesNotExist:
            message = 'Такого заказа нет'
            keyboard.append([InlineKeyboardButton('Назад', callback_data='show_work_orders')])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DEVELOPER_BASE_MENU

        order_messages = Message.objects.filter(order=order).order_by('created_at')

        formed_message = ''
        for message in order_messages:
            if not message.sender_role:
                formed_message += 'Программист: ' + message.text + '\n'
            else:
                formed_message += 'Заказчик: ' + message.text + '\n'

        message = f'title: {order.title}\ndescription: {order.description}\ncustomer: {order.client}\n\nmessages:\n{formed_message}'
        context.user_data['order_id'] = order.pk
        keyboard.append([InlineKeyboardButton('Задать вопрос по заказу', callback_data='make_question_order')])
        keyboard.append([InlineKeyboardButton('Сделано', callback_data='make_done_order')])
        keyboard.append([InlineKeyboardButton('<< Назад', callback_data='show_work_orders')])
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DEVELOPER_BASE_MENU

    def handle_make_question_order(self, update, context):

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Введите вопрос'
        )

        return DEVELOPER_ADD_QUESTION_ORDER

    def handle_add_question_order(self, update, context):

        keyboard = []
        message_question = update.message.text
        try:
            order = Order.objects.get(pk=context.user_data['order_id'])
        except ObjectDoesNotExist:
            message = 'Такого заказа нет'
            keyboard.append([InlineKeyboardButton('Назад', callback_data='show_work_orders')])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DEVELOPER_BASE_MENU

        message = 'Ваш вопрос отправлен заказчику'

        question = Message.objects.create(text=message_question, order=order, sender_role=0)

        keyboard.append([InlineKeyboardButton('<< Назад', callback_data='show_work_orders')])
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEVELOPER_BASE_MENU

    def handle_make_done_order(self, update, context):
        keyboard = []

        try:
            order = Order.objects.get(pk=context.user_data['order_id'])
        except ObjectDoesNotExist:
            message = 'Такого заказа нет'
            keyboard.append([InlineKeyboardButton('<< Назад', callback_data='show_work_orders')])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DEVELOPER_BASE_MENU

        order.finished_at = timezone.now()
        order.save()

        return self.handle_show_work_orders(update, context)

    def handle_developer_agreement(self, update, context):

        message = dedent('''
                Пользовательское соглашение.
                1. Зарегистрироваться.
                2. Дождаться активации аккаунта админом.
                3. Выбрать заказ для выполнения.
                4. Выполнить заказ.
                5. Отметить заказ выполненным.
                6. Получить профит.
                ''')
        keyboard = [
            [
                InlineKeyboardButton('<< Назад', callback_data='developer_account'),
            ],
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEVELOPER_BASE_MENU

    def handle_developer_registration(self, update, context):

        message = dedent('''
                Запрос на регистрацию отправлен. 
                Дождитесь активации аккаунта администратором. 
                ''')
        keyboard = [
            [
                InlineKeyboardButton('<< Назад', callback_data='developer_account'),
            ],
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEVELOPER_BASE_MENU

    def handle_show_free_orders(self, update, context):

        orders = Order.objects.filter(developer__isnull=True)

        if orders:
            message = 'Выбирайте заказ'
        else:
            message = 'Доступных заказов на данный момент нет'


        keyboard = []

        for order in orders:
            context.user_data['order_id'] = order.id
            keyboard.append([InlineKeyboardButton(order.title, callback_data='handle_show_order')])

        keyboard.append([InlineKeyboardButton('<< Назад', callback_data='developer')])

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DEVELOPER_BASE_MENU

    def handle_select_free_order(self, update, context):
        order_id = context.user_data['order_id']

        keyboard = []

        try:
            order = Order.objects.get(pk=order_id)
        except ObjectDoesNotExist:
            keyboard.append([InlineKeyboardButton('Назад', callback_data='show_free_orders')])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Такого заказа нет',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        chat, created = Chat.objects.get_or_create(chat_id=update.effective_chat.id)
        developer, created = Developer.objects.get_or_create(name='None', chat=chat, work_allowed=True)
        order.developer = developer
        order.save()

        return self.handle_show_free_orders(update, context)

    def handle_show_order(self, update, context):

        order_id = context.user_data['order_id']

        keyboard = []

        try:
            order = Order.objects.get(pk=order_id)
        except ObjectDoesNotExist:
            keyboard.append([[InlineKeyboardButton('Назад', callback_data='show_free_orders')]])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
               text='Такого заказа нет',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        message = dedent(f'''
                    Заголовок: {order.title}
                    Описание: {order.description}
                    Клиент: {order.client.name}
                    ''')

        context.user_data['order_id'] = order_id
        keyboard.append([InlineKeyboardButton('В работу', callback_data='handle_select_free_order')])
        keyboard.append([InlineKeyboardButton('<< Назад', callback_data='show_free_orders')])
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEVELOPER_BASE_MENU


    def handle_error(self, update, error):
        """Обрабатывает ошибки."""
 
        logger.warning(f'Update "{update}" вызвал ошибку "{error}"')
        

