from pyrogram.types import Message

from .base import BotCheckin


class PornembyCheckin(BotCheckin):
    name = "Pornemby"
    bot_username = "PronembyTGBot2_bot"
    bot_checkin_cmd = "/checkin"
    bot_success_pat = r"(\d+)\s精币[\s\S]*(\d{3})\s精币"

    async def message_handler(self, client, message: Message):
        if message.reply_markup:
            keys = [k.text for r in message.reply_markup.inline_keyboard for k in r]
            for k in keys:
                if "点击签到" in k:
                    await message.click(k)
        await super().message_handler(client, message)