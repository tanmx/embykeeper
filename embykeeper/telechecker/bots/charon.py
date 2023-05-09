import asyncio

from .base import BotCheckin


class CharonCheckin(BotCheckin):
    name = "卡戎"
    bot_username = "charontv_bot"
    bot_checkin_cmd = ["/checkin", "/cancel"]
    bot_send_interval = 3
    bot_captcha_len = 6
    bot_success_pat = r".*(\d+)"
    bot_text_ignore = ["已结束当前对话"]

    async def send_checkin(self, retry=False):
        if retry:
            await asyncio.sleep(self.bot_send_interval)
        while True:
            await self.send("/checkin")
            if await self.wait_until("已结束当前对话", 3):
                continue
            else:
                break
