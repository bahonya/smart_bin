#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""This example showcases how PTBs "arbitrary callback data" feature can be used.
For detailed info on arbitrary callback data, see the wiki page at
https://github.com/python-telegram-bot/python-telegram-bot/wiki/Arbitrary-callback_data
Note:
To use arbitrary callback data, you must install PTB via
`pip install python-telegram-bot[callback-data]`
"""
import logging
from typing import List, Tuple, cast
from telegram import __version__ as TG_VER
from telegram.ext import ConversationHandler, MessageHandler, filters
from settings import bot_token as bot_token
from db import create_wg, add_inhabitant, user_is_in_wg, get_bins_states, get_top10_duties, add_garbage_bin, get_wg_by_user
from throwingqueue import ThrowingQueue

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InvalidCallbackData,
    PicklePersistence,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

CREATE_WG_END, JOIN_WG_END = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Join or create a WG"""
    await update.message.reply_text("Please create or join a WG, you need WG id in order to join a WG")

async def create_wg_start(update, context):
    await update.message.reply_text("Write a name of a WG you want to create")
    return CREATE_WG_END

async def create_wg_end(update, context):
    wg_id = create_wg(update.message.text)
    add_inhabitant(chat_id=update.message.chat_id, name=update.message.chat.first_name, flat_share_id=wg_id)
    await update.message.reply_text(f"Here is your WG id, share it with your inhabitants {wg_id}")
    return ConversationHandler.END

async def join_wg_start(update, context):
    await update.message.reply_text("Write an ID of WG you want to join")
    return JOIN_WG_END

async def join_wg_end(update, context):
    add_inhabitant(chat_id=update.message.chat_id, name=update.message.chat.first_name, flat_share_id=update.message.text)
    await update.message.reply_text(f"You joined a WG")
    return ConversationHandler.END

ADD_BIN_CONTINUE, ADD_BIN_END = range(2)
async def add_bin_start(update, context):
    await update.message.reply_text("Write an DevEUI of sensor for bin")
    return ADD_BIN_CONTINUE
async def add_bin_continue(update, context):
    context.user_data["DevEUI"] = update.message.text
    await update.message.reply_text(f"Now write a name of a bin, e.g. Bio or Papier")
    return ADD_BIN_END
async def add_bin_end(update, context):
    context.user_data["name"] = update.message.text
    flat_share_id = get_wg_by_user(update.message.chat_id)[0]
    add_garbage_bin(garbage_bin_id=context.user_data["DevEUI"], name=context.user_data["name"], state=False, flat_share_id=flat_share_id)
    await update.message.reply_text(f"You added a bin")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text(
        "Use /start to test this bot. Use /clear to clear the stored data so that you can see "
        "what happens, if the button data is not available. "
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the callback data cache"""
    context.bot.callback_data_cache.clear_callback_data()
    context.bot.callback_data_cache.clear_callback_queries()
    await update.effective_message.reply_text("All clear!")

# Stages
START_ROUTES, END_ROUTES = range(2)
# Callback data
ONE, TWO, THREE, FOUR = range(4)

async def main_menu_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_in_wg(chat_id=update.effective_chat.id):
        await update.effective_message.reply_text("You should be in a WG, create or join a WG in order to see the panel")
    else:
        keyboard = [[InlineKeyboardButton('get status of garbage bins 🚮', callback_data=str(THREE))],
                    [InlineKeyboardButton('history 📜', callback_data=str(FOUR))],
                    [InlineKeyboardButton('quit 🚪', callback_data=str(TWO))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Main menu 🏠", reply_markup=reply_markup)
        return START_ROUTES

async def main_menu_keyboard_again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not user_is_in_wg(chat_id=update.effective_chat.id):
        await update.effective_message.reply_text("You should be in a WG, create or join a WG in order to see the panel")
    else:
        keyboard = [[InlineKeyboardButton('get bin statuses 🚮', callback_data=str(THREE))],
                    [InlineKeyboardButton('history 📜', callback_data=str(FOUR))],
                    [InlineKeyboardButton('quit 🚪', callback_data=str(TWO))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Main menu 🏠", reply_markup=reply_markup)
        return START_ROUTES

async def get_states_of_bins_in_wg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List states of bins in WG"""
    query = update.callback_query
    await query.answer()
    states = get_bins_states(update.effective_chat.id)
    messages = [f"{name} bin is full" if state == True else f"{name} bin is not full" for state, name in states]
    keyboard = []
    for i, message in enumerate(messages):
        keyboard.append([InlineKeyboardButton(message, callback_data=i)])
    keyboard.append([InlineKeyboardButton("Go to main menu 🏠", callback_data=str(ONE))])
    reply_markup=InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Bin statuses 🚮", reply_markup=reply_markup)
    return END_ROUTES

async def get_10_last_from_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List top 10 entries for a WG, from duties table"""
    query = update.callback_query
    await query.answer()
    duties = get_top10_duties(update.effective_chat.id)
    messages = [f"{duty} at {date_time}" for duty, date_time in duties]
    keyboard = []
    for i, message in enumerate(messages):
        keyboard.append([InlineKeyboardButton(message, callback_data=i)])
    keyboard.append([InlineKeyboardButton("Go to main menu 🏠", callback_data=str(ONE))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Last 10 entries of history 📜", reply_markup=reply_markup)
    return END_ROUTES

async def main_menu_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="See you next time! 👋")
    return ConversationHandler.END

async def handle_invalid_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Informs the user that the button is no longer available."""
    await update.callback_query.answer()
    await update.effective_message.edit_text(
        "Sorry, I could not process this button click 😕 Please send /start to get a new keyboard."
    )


def main() -> None:
    """Run the bot."""
    # We use persistence to demonstrate how buttons can still work after the bot was restarted
    persistence = PicklePersistence(filepath="arbitrarycallbackdatabot")
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token(bot_token)
        .persistence(persistence)
        .arbitrary_callback_data(True)
        .build()
    )
    #job_queue = application.job_queue
    #job_minute = job_queue.run_repeating(callback_minute, interval=60, first=10)
    create_wg_handler = ConversationHandler(
        entry_points=[CommandHandler('create_wg', create_wg_start)],
        fallbacks=[],
        states={
            CREATE_WG_END: [MessageHandler(filters.TEXT, create_wg_end)]
        },
    )
    join_wg_handler = ConversationHandler(
        entry_points=[CommandHandler('join_wg', join_wg_start)],
        fallbacks=[],
        states={
            JOIN_WG_END: [MessageHandler(filters.TEXT, join_wg_end)]
        },
    )
    add_bin_handler = ConversationHandler(
        entry_points=[CommandHandler('add_bin', add_bin_start)],
        fallbacks=[],
        states={
            ADD_BIN_CONTINUE: [MessageHandler(filters.TEXT, add_bin_continue)],
            ADD_BIN_END: [MessageHandler(filters.TEXT, add_bin_end)]
        },
    )
    main_menu_handler = ConversationHandler(
        entry_points=[CommandHandler('menu', main_menu_keyboard)],
        fallbacks=[CommandHandler("menu", main_menu_keyboard)],
        states={
            START_ROUTES: [
                CallbackQueryHandler(get_states_of_bins_in_wg, pattern="^" + str(THREE) + "$"),
                CallbackQueryHandler(get_10_last_from_history, pattern="^" + str(FOUR) + "$"),
                CallbackQueryHandler(main_menu_end, pattern="^" + str(TWO) + "$")
            ],
            END_ROUTES: [
                CallbackQueryHandler(main_menu_keyboard_again, pattern="^" + str(ONE) + "$"),
                CallbackQueryHandler(main_menu_end, pattern="^" + str(TWO) + "$"),
            ],
        },
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(create_wg_handler)
    application.add_handler(join_wg_handler)
    application.add_handler(add_bin_handler)
    application.add_handler(main_menu_handler)
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
