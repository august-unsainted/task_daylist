from bot_constructor.bot_config import BotConfig

config = BotConfig()
db = config.db
messages, texts, kbs = config.messages, config.texts, config.keyboards
config.entries_on_page = 10
config.btn_length = 30
