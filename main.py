import os
import telebot
from dotenv import load_dotenv

load_dotenv()
bot: telebot = telebot.TeleBot(token=os.getenv('telegram_bot_key'))

d_length_options: list = [3, 5, 10]
d_options: list = ['Weather', 'Casual', 'Shopping']

users = {}


class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.dialogue: str | None = None
        self.d_length: int | None = None

    def set_dialogue(self, dialogue):
        self.dialogue = dialogue

    def set_d_length(self, d_length):
        self.d_length = d_length

    def get_dialogue(self):
        return self.dialogue

    def get_d_length(self) -> int:
        return self.d_length

    def is_ready(self) -> bool:
        return self.dialogue is not None and self.d_length is not None

    def get_callback_command(self, **kwargs) -> str:
        if "dialogue" in kwargs:
            self.set_dialogue(kwargs["dialogue"])
        if self.is_ready():
            return f'start_{self.dialogue.lower()}_dialogue'
        elif not self.d_length:
            return 'select_dialogue_length'
        else:
            return 'select_dialogue'

    def __str__(self):
        return f"Subject: {self.dialogue}, dialogue length: {self.d_length}"


@bot.message_handler(commands=['help'])
def handle_start_help(message):
    return bot.reply_to(message, "Hello! I am a bot who will talk to you in Turkish. To start, select a dialogue option.")


@bot.callback_query_handler(func=lambda call: call.data == 'start_weather_dialogue')
def handle_weather_dialogue(call):
    return bot.send_message(call.message.chat.id, "Merhaba! Bugün hava nasıl?")


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_dialogue_length_'))
def handle_set_dialogue_length(call):
    user: User = users[call.message.chat.id]
    d_length: int = call.data.split('_')[-1]
    user.set_d_length(int(call.data.split('_')[-1]))
    bot.send_message(call.message.chat.id, f"Dialogue length was set to {d_length} messages.")
    if user.is_ready():
        bot.send_message(call.message.chat.id, f"Great! Let's start the {user.dialogue} dialogue!")
        bot.callback_query_handler(user.get_callback_command())


@bot.callback_query_handler(func=lambda call: call.data == 'select_dialogue_length')
def handle_select_dialogue_length(call):
    keyboard = telebot.types.InlineKeyboardMarkup()
    for d_length in d_length_options:
        keyboard.row(
            telebot.types.InlineKeyboardButton(f'{d_length} messages',
                                               callback_data=f'set_dialogue_length_{d_length}')
        )
    return bot.send_message(call.message.chat.id, "Great! How long should we chat?", reply_markup=keyboard)


@bot.message_handler(commands=['dialogue'])
def handle_dialogue(message):
    if message.chat.id not in users:
        users[message.chat.id] = User(message.chat.id)
    user: User = users[message.chat.id]
    keyboard = telebot.types.InlineKeyboardMarkup()
    for option in d_options:
        keyboard.row(
            telebot.types.InlineKeyboardButton(option, callback_data=user.get_callback_command(dialogue=option))
        )

    return bot.send_message(message.chat.id, 'Select a conversation subject', reply_markup=keyboard)


if __name__ == '__main__':
    bot.infinity_polling()
