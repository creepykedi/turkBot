from typing import Optional, Callable
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_logger
from llm import TurkBot
from dotenv import load_dotenv
import os
load_dotenv()
logger = get_logger(__name__)


d_length_options: list = [3, 5, 10]
d_options: list = ['Weather', 'Casual', 'Shopping', 'Food']

users = {}  # fake db {user_id: User}


class User:
    def __init__(self, user_id):
        self.user_id: int = user_id
        self.topic: str | None = d_options[1]
        self.d_length: int | None = d_length_options[0]

    def set_topic(self, topic) -> None:
        self.topic = topic

    def set_d_length(self, d_length) -> None:
        self.d_length = d_length

    def get_topic(self) -> str:
        return self.topic

    def get_d_length(self) -> int:
        return self.d_length

    def __str__(self):
        return f"Topic: {self.topic}, dialogue length: {self.d_length}"


def choose_topic(update, context):
    results = [InlineKeyboardButton(
                text=option,
                callback_data=option
            ) for option in d_options]
    reply_markup = InlineKeyboardMarkup([results])
    update.message.reply_text('Choose chat topic', reply_markup=reply_markup)


def topic_option_button(update, context):
    query = update.callback_query
    user_obj: User = retrieve_user(update)
    user_obj.set_topic(query.data)
    query.answer()
    query.edit_message_text(text=f"Selected option: {query.data}")


def choose_chat_length(update, context):
    results = [
        InlineKeyboardButton(
            text=x,
            callback_data=int(x)
        ) for x in d_length_options
    ]
    reply_markup = InlineKeyboardMarkup([results])
    update.message.reply_text('Choose chat length', reply_markup=reply_markup)


def dialogue_length_option_button(update, context):
    query = update.callback_query
    user_obj: User = retrieve_user(update)
    user_obj.set_d_length(query.data)
    query.answer()
    query.edit_message_text(text=f"Selected chat length: {query.data}")


def retrieve_user(update):
    if update.message:
        user = update.message.from_user
    elif update.callback_query:
        user = update.callback_query.from_user
    else:
        return None
    user_obj: User = users.get(user.id)
    if not user_obj:
        user_obj = User(user.id)
        users[user.id] = user_obj
        logger.info(f"User set: {users}")
    logger.info(f"Users here: {users}")

    return user_obj


class TgBot:
    def __init__(
        self,
        token: str,
    ):
        self.token = token
        self.updater: Updater = self._init_updater()
        self.dp = self._init_dispatcher()
        self.turk_bot: Optional[TurkBot] = None

    def _init_turk_bot(self, dialogue_subject='Casual', memory_depth=5):
        self.turk_bot = TurkBot(dialogue_subject=dialogue_subject, memory_depth=memory_depth)

    def _init_updater(self) -> Updater:
        return Updater(self.token, use_context=True)

    def _init_dispatcher(self):
        return self.updater.dispatcher

    def echo(self, update, context):
        if self.turk_bot is not None:
            response = self.turk_bot.tell(update.message.text)
            update.message.reply_text(response)
        else:
            update.message.reply_text("There is no active bot. Please write /start and init one bot")

    def error(self, update, context):
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def start(self, update, context):
        logger.info("Init bot")
        user_obj = retrieve_user(update)
        length: int = user_obj.get_d_length()
        topic: str = user_obj.get_topic()
        self._init_turk_bot(dialogue_subject=topic, memory_depth=length)
        logger.info("Init bot is done")
        update.message.reply_text("Kemal bot is here! Default conversation topic is set to Casual. "
                                  "Type /help to see all of the options. Say Merhaba! 🙌🏻")

    def end(self, update, context):
        self.turk_bot.end_dialogue()
        update.message.reply_text('Goodbye! Talk to you again soon.')

    @staticmethod
    def show_settings(update, context):
        user_obj: User = retrieve_user(update)
        update.message.reply_text(f"Current settings are \n Topic: {user_obj.get_topic()} \n "
                                  f"Chat length: {user_obj.get_d_length()}")

    def show_history(self, update, context):
        if self.turk_bot is not None:
            update.message.reply_text(self.turk_bot.show_history)
        else:
            update.message.reply_text("There is no active turk bot. Please write /start and init one bot")

    def help(self, update, context):
        help_string = """
        @muhtesem_bot
        I am Kemal, Turkish bot. I will talk to you in Turkish and help you with your language skills!
        /start - start the conversion
        /topic - select chat topic
        /length - select chat length
        /settings - current settings
        /end - end the conversation
        /help - info 
        """
        update.message.reply_text(help_string)

    def add_handler(self, name: str, func: Callable):
        self.dp.add_handler(CommandHandler(name, func))
        return self

    def add_message_handler(self, func: Callable):
        self.dp.add_handler(MessageHandler(Filters.text, func))
        return self

    def add_error_handler(self, func: Callable):
        self.dp.add_error_handler(func)
        return self

    def add_handlers(self):
        self.dp.add_handler(CallbackQueryHandler(dialogue_length_option_button, pattern='^\d+'))
        self.dp.add_handler(CallbackQueryHandler(topic_option_button, pattern=f'^({"|".join(d_options)})$'))
        (
            self.add_handler("start", self.start)
            .add_handler("end", self.end)
            .add_handler("help", self.help)
            .add_handler("settings", self.show_settings)
            .add_handler("topic", choose_topic)
            .add_handler("length", choose_chat_length)
            .add_message_handler(self.echo)
            .add_error_handler(self.error)
        )

    def start_bot(self):
        self.updater.start_polling()
        self.updater.idle()

if __name__ == '__main__':
    b = TgBot(token=os.getenv('telegram_bot_key'))
    b.add_handlers()
    b.start_bot()
