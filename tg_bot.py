import argparse
import logging
import os
from pprint import pprint
from textwrap import dedent

import telegram
from functools import partial
from dotenv import load_dotenv
from environs import Env
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler,
                          MessageHandler, Filters,
                          CallbackContext, ConversationHandler, CallbackQueryHandler)

from error_processing import TelegramLogsHandler

logger = logging.getLogger(__file__)

START, JOIN_HANDLER, HANDLE_MENU, RULES_HANDLER, HANDLE_DESCRIPTION = range(5)


def start(update: Update, context: CallbackContext) -> None:
    keyboard = []
    keyboard.append([InlineKeyboardButton('Условия работы.', callback_data=1)])
    keyboard.append([InlineKeyboardButton('Получить доступ.', callback_data=2)])
    keyboard.append([InlineKeyboardButton('Назад.', callback_data=3)])


    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        'Выбирайте варианты.',
        reply_markup=reply_markup,
    )

    return JOIN_HANDLER


def join_handler(
        update: Update,
        context: CallbackContext,
        chat_id) -> None:
    query = update.callback_query
    choice = query.data

    print(choice)

    if choice == 3:
        # Назад
        return

    if choice == 1:
        message = dedent('''\
        Rules
        '''
        )

        keyboard = []
        keyboard.append([InlineKeyboardButton('Назад.', callback_data=5)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(chat_id=chat_id, text='ddd', reply_markup=reply_markup)

        return RULES_HANDLER

    if choice == 2:
        # Send join request
        return


    #keyboard = []
    #keyboard.append([InlineKeyboardButton('1 кг', callback_data=1), InlineKeyboardButton('5 кг', callback_data=5),
    #                 InlineKeyboardButton('10 кг', callback_data=10)])
    #keyboard.append([InlineKeyboardButton('Взад', callback_data=token)])
    #reply_markup = InlineKeyboardMarkup(keyboard)

    #context.bot.sendPhoto(chat_id=update.callback_query.message.chat.id, photo=image_url, caption=message,
    #                      reply_markup=reply_markup)
    #context.bot.delete_message(chat_id=update.callback_query.message.chat.id,
    #                           message_id=update.callback_query.message.message_id)

    #return HANDLE_MENU


def rules_handler(update: Update, context: CallbackContext) -> None:
    choice = update.callback_query.data

    message = dedent('''\
            Rules
            '''
                     )

    keyboard = []
    keyboard.append([InlineKeyboardButton('Назад.', callback_data=3)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        'Условия работы',
        reply_markup=reply_markup,
    )

    return JOIN_HANDLER


def cancel(bot, update):
    user = update.message.from_user
    logger.info("Пользователь %s завершил покупку.", user.first_name)
    update.message.reply_text('Пока пока!',
                              reply_markup=telegram.ReplyKeyboardRemove())

    return ConversationHandler.END


def error_handler(update, context):
    logger.error(msg='Ошибка при работе скрипта: ', exc_info=context.error)


def main() -> None:
    env = Env()
    env.read_env()
    telegram_token = env('TELEGRAM_TOKEN')
    chat_id = env('CHAT_ID')

    service_bot = telegram.Bot(token=telegram_token)
    logging.basicConfig(level=logging.ERROR)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(TelegramLogsHandler(service_bot, chat_id))

    updater = Updater(telegram_token)
    dispatcher = updater.dispatcher

    partial_start_handler = partial(
        start,
    )
    partial_join_handler = partial(
        join_handler,
        chat_id,
    )
    partial_rules_handler = partial(
        rules_handler,
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', partial_start_handler)],
        states={
            JOIN_HANDLER: [
                CallbackQueryHandler(
                    partial_join_handler,
                )
            ],
            RULES_HANDLER: [
                CallbackQueryHandler(
                    partial_rules_handler,
                )
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
