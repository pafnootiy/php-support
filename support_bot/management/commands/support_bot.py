import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters, MessageHandler, Updater


logger = logging.getLogger(__file__)


START = range(1, 2)


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

        handler = self.handle_users_reply
        self.dispatcher.add_handler(CallbackQueryHandler(handler))
        self.dispatcher.add_handler(MessageHandler(Filters.text, handler))
        self.dispatcher.add_handler(CommandHandler('start', handler))
        self.dispatcher.add_error_handler(self.handle_error)

    def handle(self, *args, **kwargs):
        """Прослушивает сообщения в Telegram."""

        self.updater.start_polling()
        self.updater.idle()
        
    def handle_users_reply(self, update, context):
        """Обрабатывает действия пользователей в чатах."""

        pass
        
    def handle_error(update, error):
        """Обрабатывает ошибки."""

        logger.warning(f'Update "{update}" вызвал ошибку "{error}"')

