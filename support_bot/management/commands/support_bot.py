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


class Command(BaseCommand):
    help = 'Команда организации работы Telegram-бота в приложении Django.'
    
    def __init__(self):
        super().__init__()
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            filename='support_bot.log',
            filemode='w'
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
            MAIN_MENU: self.handle_start_command,
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
            user_reply = update.callback_query.data
            chat_id = update.callback_query.message.chat_id
        else:
            return
                   
        user_state = START if user_reply == '/start' else self.get_chat_state(chat_id) or START
        state_handler = self.states_handlers[user_state]

        next_state = state_handler(update, context)
        self.set_chat_state(chat_id, next_state)
        
    def get_chat_state(self, chat_id):
        """Получает состояние чата."""

        # TODO: заменить заглушку на получение состояния чата
        return START # Chat.get_chat_state(chat_id=chat_id)
        
    def set_chat_state(self, chat_id, next_state):
        # TODO: заменить заглушку на изменение состояния чата
        pass

    def handle_start_command(self, update, context):
        """Обрабатывает состояние START."""
     
        query = update.callback_query
        if not query:
            with suppress(BadRequest):
                context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id-1
                )
                
        keyboard = [
            [InlineKeyboardButton(user_role, callback_data=user_role)]
            for user_role in ['Заказчик', 'Программист']
        ]
        reply_markup=InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Кто вы?",
            reply_markup=reply_markup
        )
        return MAIN_MENU      

    def handle_error(update, error):
        """Обрабатывает ошибки."""

        logger.warning(f'Update "{update}" вызвал ошибку "{error}"')

