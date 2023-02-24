import logging
from contextlib import suppress

from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters, MessageHandler, Updater

from ...models import Chat


logger = logging.getLogger(__file__)


START = 'START'
MAIN_MENU = 'MAIN_MENU'
CLIENT_BASE_MENU = 'CLIENT_BASE_MENU'
DEVELOPER_BASE_MENU = 'MAIN_MENU'


class Command(BaseCommand):
    help = 'Команда организации работы Telegram-бота в приложении Django.'
    
    def __init__(self):
        super().__init__()
        # TODO: Добавить filename='support_bot.log', filemode='w' чтобы логи выводились в файл
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )

        self.updater = Updater(token=settings.TELEGRAM_BOT_TOKEN)
        self.dispatcher = self.updater.dispatcher

        handler = self.handle_user_action
        self.dispatcher.add_handler(CallbackQueryHandler(handler))
        self.dispatcher.add_handler(MessageHandler(Filters.text, handler))
        self.dispatcher.add_handler(CommandHandler('start', handler))
        self.dispatcher.add_error_handler(self.handle_error)
        
        self.states_handlers = {
            START: self.handle_start_command,
            MAIN_MENU: self.handle_main_menu,
            CLIENT_BASE_MENU: self.handle_client_base_menu,
            DEVELOPER_BASE_MENU: self.handle_developer_base_menu,
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

        dialogue_state = None
        try:
            dialogue_state = Chat.get_dialogue_state(chat_id=chat_id)
        except Exception as ex:
            logger.warning(f'Ошибка в чате с chat_id={chat_id}:')
            logger.warning(ex)
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
            dialogue_state_from_db = self.get_or_create_chat_in_db(update)

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
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Кто вы?",
            reply_markup=reply_markup
        )
        return MAIN_MENU

    def handle_main_menu(self, update, context):
        """Обрабатывает состояние MAIN_MENU."""

        query = update.callback_query
        variant = query.data
        methods = {
            'client': self.handle_client_button,
            'developer': self.handle_developer_button,
        }
        return methods[variant](update, context)
        
    def handle_client_button(self, update, context):
        """Обрабатывает нажатие кнопки Заказчик главного меню."""
        pass
        # if not self.check_payment(update, context):
        
        return CLIENT_BASE_MENU
        
    def handle_client_base_menu(self, update, context):
        """Обрабатывает состояние CLIENT_BASE_MENU."""
        pass
        
    def handle_developer_button(self, update, context):
        """Обрабатывает нажатие кнопки Программист главного меню."""
        pass
        return DEVELOPER_BASE_MENU
 
    def handle_developer_base_menu(self, update, context):
        """Обрабатывает состояние DEVELOPER_BASE_MENU."""
        pass
   
    def handle_error(self, update, error):
        """Обрабатывает ошибки."""

