from pyrogram.types import Message
from thefuzz import process, fuzz

from ...data import get_data
from .base import AnswerBotCheckin

__ignore__ = True


class JMSCheckin(AnswerBotCheckin):
    ocr = "idioms@v1"
    idioms = None

    name = "卷毛鼠"
    bot_username = "jmsembybot"

    async def start(self):
        async with self.lock:
            if self.idioms is None:
                with open(
                    await get_data(self.basedir, "idioms@v1.txt", proxy=self.proxy, caller=self.name)
                ) as f:
                    self.__class__.idioms = [i for i in f.read().splitlines() if len(i) == 4]
        return await super().start()

    def to_idiom(self, captcha: str):
        phrase, score = process.extractOne(captcha, self.idioms, scorer=fuzz.partial_token_sort_ratio)
        if score > 70 or len(captcha) < 4:
            result = phrase
            self.log.debug(f'[gray50]已匹配识别验证码 "{captcha}" -> 成语 "{result}"[/]')
        else:
            result = captcha
        return result

    async def on_captcha(self, message: Message, captcha: str):
        captcha = self.to_idiom(captcha)
        async with self.operable:
            if not self.message:
                await self.operable.wait()
            for l in captcha:
                try:
                    await self.message.click(l)
                except ValueError:
                    self.log.info(f'未能找到对应 "{l}" 的按键, 正在重试.')
                    await self.retry()
                    break
