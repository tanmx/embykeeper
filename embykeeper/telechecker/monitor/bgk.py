from pyrogram.types import Message

from .base import Monitor


class BGKMonitor(Monitor):
    name = "不给看"
    chat_name = "Ephemeralemby"
    chat_keyword = r"(?:^|\s)([a-zA-Z0-9]{32})(?!\S)"
    bot_username = "UnknownEmbyBot"
    notify_create_name = True
    allow_edit = False

    async def on_trigger(self, message: Message, key, reply):
        await self.client.send_message(self.bot_username, "/invite")
        await self.client.send_message(self.bot_username, key)
        await self.client.send_message(self.bot_username, self.unique_name)
        self.log.bind(notify=True).info(f'已向Bot发送邀请码: "{key}", 请查看.')
