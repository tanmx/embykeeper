import asyncio
import io

from rich.text import Text
from loguru import logger

from .link import Link
from .tele import ClientsSession

logger = logger.bind(scheme="telenotifier")


class TelegramStream(io.TextIOWrapper):
    def __init__(self, account, proxy=None, basedir=None):
        super().__init__(io.BytesIO(), line_buffering=True)
        self.account = account
        self.proxy = proxy
        self.basedir = basedir

        self.queue = asyncio.Queue()
        self.watch = asyncio.create_task(self.watchdog())

    async def watchdog(self):
        while True:
            message = await self.queue.get()
            try:
                result = await asyncio.wait_for(self.send(message), 10)
            except asyncio.TimeoutError:
                logger.warning("推送消息到 Telegram 超时.")
            else:
                if not result:
                    logger.warning(f'推送消息到 Telegram 失败: 无法登录 {self.account["phone"]}.')

    async def send(self, message):
        async with ClientsSession([self.account], proxy=self.proxy, basedir=self.basedir) as clients:
            async for tg in clients:
                return await Link(tg).send_log(message)
            else:
                return False

    def write(self, message):
        message = Text.from_markup(message).plain
        if message.endswith("\n"):
            message = message[:-1]
        if message:
            self.queue.put_nowait(message)
