# TODO: Раскомментировать после отладки
# import logging
from contextlib import suppress
from datetime import date
from functools import partial
from textwrap import dedent

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import Max
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters, MessageHandler, Updater

from ...models import Chat, Client, Developer, Order


# TODO: Раскомментировать после отладки
# logger = logging.getLogger(__file__)


START = 'START'
MAIN_MENU = 'MAIN_MENU'
CLIENT_BASE_MENU = 'CLIENT_BASE_MENU'
CLIENT_NEW_ORDER_TITLE = 'CLIENT_NEW_ORDER_TITLE'
CLIENT_ADD_ORDER_DESCRIPTION_MENU = 'CLIENT_ADD_ORDER_DESCRIPTION_MENU'
CLIENT_ADD_ORDER_DESCRIPTION = 'CLIENT_ADD_ORDER_DESCRIPTION'
CLIENT_ORDER_PUBLICATION_MENU = 'CLIENT_ORDER_PUBLICATION_MENU'
CLIENT_ORDER_PUBLICATION_CHOICE = 'CLIENT_ORDER_PUBLICATION_CHOICE'
CLIENT_ORDER_CHOICE = 'CLIENT_ORDER_CHOICE'
DEVELOPER_BASE_MENU = 'DEVELOPER_BASE_MENU'
DEVELOPER_SELECT_ORDER = 'DEVELOPER_SELECT_ORDER'


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
            DEVELOPER_SELECT_ORDER: self.handle_select_free_order,
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
            # chat_id = update.message.chat_id
            dialogue_state = START if user_reply == '/start' else self.get_dialogue_state(chat_id) or START
            state_handler = self.states_handlers[dialogue_state]
        elif update.callback_query:
            # Обязательная команда (см. https://core.telegram.org/bots/api#callbackquery)
            update.callback_query.answer()     
            user_reply = update.callback_query.data
            # chat_id = update.callback_query.message.chat_id
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
            chat = Chat.objects.get_or_create(chat_id=chat_id)
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
            'handle_select_free_order': self.handle_select_free_order,
        }

        if variant in methods:
            return methods[variant](update, context)
            
        methods = {
            'client_add_order_description_': self.handle_client_add_order_description_button,
            'client_order_publication_': self.handle_client_order_publication_button,
            'client_order_choice_': self.handle_client_order_choice_button,
        }
        for method in methods:
            length = len(method)
            if len(variant) > length and variant[:length] == method:
                return methods[method](update, context)

        return self.handle_show_order(update, context)
        
    def handle_client_button(self, update, context):
        """Обрабатывает нажатие кнопки 'Заказчик' в главном меню."""

        if not self.check_payment(update, context):
            return send_message_about_payment(update, context)
        
        keyboard = [
            [
                InlineKeyboardButton('Создать заказ', callback_data='client_new_order'),
                InlineKeyboardButton('Мои заказы', callback_data='client_orders')
            ],
            [
                InlineKeyboardButton('«‎ Вернуться в главное меню', callback_data='main_menu')
            ]
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите желаемое действие.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENT_BASE_MENU

    def check_payment(self, update, context):
        """Проверяет, оплатил ли Заказчик предоставление услуг."""

        chat_id = update.effective_chat.id
        count = Client.objects.filter(chat__chat_id=chat_id, expiration_at__gte=date.today()).count()
        return count == 1

    def send_message_about_payment(update, context):
        """Посылает в чат Заказчика сообщение о необходимости оплатить услуги."""

        keyboard = [[InlineKeyboardButton('«‎ Вернуться в главное меню', callback_data='main_menu')]]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Оплатите, пожалуйста, наши услуги и затем вернитесь в чат.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return START

    def handle_client_new_order_button(self, update, context):
        """Начинает создание Заказчиком нового заказа."""

        if not self.check_payment(update, context):
            return send_message_about_payment(update, context)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Введите Название заказа'
        )
        return CLIENT_NEW_ORDER_TITLE
 
    def handle_new_order_title(self, update, context):
        """Принимает от Заказчика ввод названия нового заказа."""

        if not self.check_payment(update, context):
            return send_message_about_payment(update, context)
        
        title = update.message.text.strip()
        if len(title) < 4:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Слишком короткое Название заказа. Заказ не создан.'
            )
            return self.handle_client_button(update, context)

        chat_id = update.effective_chat.id
        client = Client.objects.get(chat__chat_id=chat_id)
        max_orders_number = Order.objects.filter(client=client).aggregate(Max('number')).get('number__max')
        order_number = max_orders_number+1 if max_orders_number else 1
        Order.objects.create(number=order_number, title=title, description='', client=client)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Заказ № {order_number} с заголовком "{title}" создан.'
        )
        context.user_data['order_number'] = order_number
        return self.send_client_add_order_description_menu(update, context)

    def send_client_add_order_description_menu(self, update, context):
        """Посылает в чат меню с кнопкой 'Добавить описание к Заказу' для Заказчика."""

        order_number = context.user_data.pop('order_number')
        keyboard = [
            [
                InlineKeyboardButton(
                    f'Добавить описание к Заказу № {order_number}',
                    callback_data=f'client_add_order_description_{order_number}'
                ),
            ],
            [
                InlineKeyboardButton('«‎ Вернуться в меню Заказчика', callback_data='client')
            ]
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите желаемое действие.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )            
        return CLIENT_ADD_ORDER_DESCRIPTION_MENU
 
    def handle_client_add_order_description_button(self, update, context):
        """Обрабатывает нажатие Заказчиком кнопки 'Добавить описание к заказу'."""

        if not self.check_payment(update, context):
            return send_message_about_payment(update, context)
            
        chat_id = update.effective_chat.id
        order_number = self.get_order_number_from_bot(update)
        orders = Order.objects.filter(client__chat__chat_id=chat_id, number=order_number)
        if not orders:
            context.user_data['order_number'] = order_number
            return self.send_client_message_order_not_exist(update, context)
            
        if orders[0].description:
            context.user_data['order_number'] = order_number        
            return self.send_client_message_order_description_exists(update, context)
            
        context.user_data['order_number'] = order_number
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Введите Описание заказа № {order_number} ("{orders[0].title}"):'
        )
        return CLIENT_ADD_ORDER_DESCRIPTION
 
    def get_order_number_from_bot(self, update):
        """Извлекает номер заказа из данных, зашитых в кнопку чата в Telegram."""

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
        
    def send_client_message_order_description_exists(self, update, context):
        """Посылает в чат сообщение для Заказчика о том, что выбранный заказ уже содержит описание."""
        
        order_number = context.user_data.pop('order_number')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Заказ № {order_number} уже содержит описание.'
        )
        return self.handle_client_button(update, context)
        
    def handle_add_order_description(self, update, context):
        """Принимает от Заказчика ввод описания заказа."""
 
        if not self.check_payment(update, context):
            return send_message_about_payment(update, context)
            
        description = update.message.text.strip()
        if len(description) < 10:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Слишком короткое Описание заказа. Описание не добавлено.'
            )
            return self.send_client_add_order_description_menu(update, context)

        chat_id = update.effective_chat.id        
        order_number = context.user_data['order_number']
        orders = Order.objects.filter(client__chat__chat_id=chat_id, number=order_number)
        if not orders:
            return self.send_client_message_order_not_exist(update, context)

        order = orders[0]
        if order.description:
            context.user_data['order_number'] = order_number        
            return self.send_client_message_order_description_exists(update, context)

        order.description = description
        order.save()
        
        text = (
            f'Описание в заказ № {order_number} добавлено.'
            '\nВы можете опубликовать заказ сейчас или сделать это позднее.'
        )
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text
        )
        return self.send_client_order_publication_menu(update, context)

    def send_client_order_publication_menu(self, update, context):
        """Посылает в чат Заказчика меню с кнопкой 'Опубликовать Заказ'."""

        order_number = context.user_data.pop('order_number')
        keyboard = [
            [
                InlineKeyboardButton(
                    f'Опубликовать Заказ № {order_number}',
                    callback_data=f'client_order_publication_{order_number}'
                ),
            ],
            [
                InlineKeyboardButton('«‎ Вернуться в меню Заказчика', callback_data='client')
            ]
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите желаемое действие.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )            
        return CLIENT_ORDER_PUBLICATION_MENU
 
    def handle_client_order_publication_button(self, update, context):
        """Обрабатывает нажатие Заказчиком кнопки 'Опубликовать заказ'."""

        if not self.check_payment(update, context):
            return send_message_about_payment(update, context)

        chat_id = update.effective_chat.id
        order_number = self.get_order_number_from_bot(update)
        orders = Order.objects.filter(client__chat__chat_id=chat_id, number=order_number)
        if not orders:
            context.user_data['order_number'] = order_number
            return self.send_client_message_order_not_exist(update, context)
            
        order = orders[0]
        if not order.description:
            context.user_data['order_number'] = order_number        
            return self.send_client_message_order_description_not_exist(update, context)
        
        order.is_published = True
        order.save()

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Заказ № {order_number} опубликован.'
        )
        return self.handle_client_button(update, context)
 
    def send_client_message_order_description_not_exist(self, update, context):
        """Посылает в чат сообщение для Заказчика о том, что выбранный заказ не содержит описания."""
        
        order_number = context.user_data.pop('order_number')
        text = (
            f'У заказа № {order_number} нет описания.'
            '\nОпубликовать заказ без описания нельзя.'
        )
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text
        )
        return self.send_client_add_order_description_menu(update, context)

    def handle_client_orders_button(self, update, context):
        """Обрабатывает нажатие Заказчиком кнопки 'Мои заказы'."""

        chat_id = update.effective_chat.id
        orders = Order.objects.filter(client__chat__chat_id=chat_id).order_by('number')
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
        
    def handle_client_order_choice_button(self, update, context):
        """Обрабатывает нажатие заказчиком кнопки заказа в меню 'Мои заказы'."""
        
        # TODO: Заменить заглушку на реальный код.
        pass
        return START
    
    def handle_developer_button(self, update, context):
        """Обрабатывает нажатие кнопки 'Программист' в главном меню."""

        keyboard = [
            [
                InlineKeyboardButton('Условия работы', callback_data='developer_agreement'),
            ],
            [
                InlineKeyboardButton('Регистрация', callback_data='developer_registration'),
            ],
            [
                InlineKeyboardButton('Смотреть свободные заказы', callback_data='show_free_orders'),
            ],
            [
                InlineKeyboardButton('Назад', callback_data='main_menu'),
            ],
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите желаемое действие.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEVELOPER_BASE_MENU

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
                InlineKeyboardButton('Назад', callback_data='developer'),
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
                InlineKeyboardButton('Назад', callback_data='developer'),
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

        keyboard = []

        for order in orders:
            keyboard.append([InlineKeyboardButton(order.title, callback_data=order.id)])

        keyboard.append([InlineKeyboardButton('<< Назад', callback_data='developer')])

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите заказ',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DEVELOPER_BASE_MENU

    def handle_select_free_order(self, update, context):
        print(update.callback_query.data)
        pass

    def handle_show_order(self, update, context):
        query = update.callback_query
        variant = query.data

        keyboard = []

        try:
            order = Order.objects.get(pk=variant)
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

        keyboard.append([InlineKeyboardButton('За работу', callback_data='handle_select_free_order')])
        keyboard.append([InlineKeyboardButton('Назад', callback_data='show_free_orders')])
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return DEVELOPER_SELECT_ORDER


    def handle_error(self, update, error):
        """Обрабатывает ошибки."""
 
        logger.warning(f'Update "{update}" вызвал ошибку "{error}"')
        

