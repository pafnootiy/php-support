# TODO: Раскомментировать после отладки
# import logging
from contextlib import suppress

from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters, MessageHandler, Updater

from ...models import Chat


# TODO: Раскомментировать после отладки
# logger = logging.getLogger(__file__)


START = 'START'
MAIN_MENU = 'MAIN_MENU'
CLIENT_BASE_MENU = 'CLIENT_BASE_MENU'
DEVELOPER_BASE_MENU = 'DEVELOPER_BASE_MENU'
NEW_ORDER_MENU = 'NEW_ORDER_MENU'
CLIENT_ORDERS_MENU = 'CLIENT_ORDERS_MENU'


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
            MAIN_MENU: self.handle_button,
            CLIENT_BASE_MENU: self.handle_button,
            DEVELOPER_BASE_MENU: self.handle_button,
            NEW_ORDER_MENU: self.handle_button,
            CLIENT_ORDERS_MENU: self.handle_button,
        }

    def handle(self, *args, **kwargs):
        """Прослушивает сообщения в Telegram."""
        
        self.updater.start_polling()
        self.updater.idle()
        
    def handle_user_action(self, update, context):
        """Обрабатывает действие пользователя в чате."""

        if update.message:
            user_reply = update.message.text
            chat_id = update.message.chat_id
        elif update.callback_query:
            # Обязательная команда (см. https://core.telegram.org/bots/api#callbackquery)
            update.callback_query.answer()     
            user_reply = update.callback_query.data
            chat_id = update.callback_query.message.chat_id
        else:
            return
                   
        dialogue_state = START if user_reply == '/start' else self.get_dialogue_state(chat_id) or START
        state_handler = self.states_handlers[dialogue_state]

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
      
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Кто вы?",
            reply_markup=self.create_main_menu_markup()
        )
        return MAIN_MENU

    def create_main_menu_markup(self):
        """Создаёт клавиатуру главного меню."""
 
        keyboard = [[
            InlineKeyboardButton('Заказчик', callback_data='client'),
            InlineKeyboardButton('Программист', callback_data='developer')
        ]]
        return InlineKeyboardMarkup(keyboard)
        
    def handle_button(self, update, context):
        """Обрабатывает нажатие кнопок."""

        query = update.callback_query
        variant = query.data
        methods = {
            'main_menu': self.handle_start_command,
            'client': self.handle_client_button,
            'developer': self.handle_developer_button,
            'new_order': self.handle_new_order_button,
            'client_orders': self.handle_client_orders_button,
        }
        return methods[variant](update, context)
        
    def handle_client_button(self, update, context):
        """Обрабатывает нажатие кнопки 'Заказчик' в главном меню."""

        if not self.check_payment(update, context):
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Оплатите, пожалуйста, наши услуги и затем вернитесь в чат.",
                reply_markup=self.create_main_menu_markup()
            )
            return MAIN_MENU
        
        keyboard = [
            [
                InlineKeyboardButton('Создать заказ', callback_data='new_order'),
                InlineKeyboardButton('Мои заказы', callback_data='client_orders')
            ],
            [
                InlineKeyboardButton('«‎ Вернуться в главное меню', callback_data='main_menu')
            ]
        ]
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Выберите желаемое действие.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENT_BASE_MENU

    def check_payment(self, update, context):
        """Проверяет, оплатил ли Заказчик предоставление ему услуг в этом чате."""

        # TODO: Написать реальный код вместо заглушки
        return True
        
    def handle_new_order_button(self, update, context):
        pass
        return NEW_ORDER_MENU

    def handle_client_orders_button(self, update, context):
        pass
        return CLIENT_ORDERS_MENU
         
    def handle_developer_button(self, update, context):
        """Обрабатывает нажатие кнопки 'Программист' в главном меню."""
        
        # TODO: Написать реальный код вместо заглушки
        pass
        return DEVELOPER_BASE_MENU
   
    def handle_error(self, update, error):
        """Обрабатывает ошибки."""
 
        logger.warning(f'Update "{update}" вызвал ошибку "{error}"')
        

