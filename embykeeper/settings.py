import os
from pathlib import Path
import sys
import base64
import hashlib

from loguru import logger
import tomli as tomllib
from schema import And, Optional, Or, Regex, Schema, SchemaError


def check_config(config):
    PositiveInt = lambda: And(int, lambda n: n > 0)
    schema = Schema(
        {
            Optional("timeout"): PositiveInt(),
            Optional("retries"): PositiveInt(),
            Optional("concurrent"): PositiveInt(),
            Optional("random"): PositiveInt(),
            Optional("notifier"): Or(str, bool),
            Optional("nofail"): bool,
            Optional("proxy"): Schema(
                {
                    Optional("hostname"): Regex(
                        r"^(?=.{1,255}$)[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*\.?$"
                    ),
                    Optional("port"): And(int, lambda n: n > 1024 and n < 65536),
                    Optional("scheme"): Schema(Or("socks5", "http")),
                }
            ),
            Optional("service"): Schema(
                {
                    Optional("checkiner"): [str],
                    Optional("monitor"): [str],
                    Optional("messager"): [str],
                }
            ),
            Optional("telegram"): [
                Schema(
                    {
                        "api_id": Regex(r"^\d+$"),
                        "api_hash": Regex(r"^[a-z0-9]+$"),
                        "phone": str,
                        Optional("monitor"): bool,
                        Optional("send"): bool,
                    }
                )
            ],
            Optional("emby"): [
                Schema(
                    {
                        "url": Regex(
                            r"(http|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])"
                        ),
                        "username": str,
                        "password": str,
                        Optional("time"): PositiveInt(),
                        Optional("progress"): PositiveInt(),
                    }
                )
            ],
            Optional("monitor"): Schema({str: Schema({}, ignore_extra_keys=True)}),
        }
    )
    try:
        schema.validate(config)
    except SchemaError as e:
        return e
    else:
        return None


def write_faked_config(path, without_censitive=True):
    import uuid

    from tomlkit import document, nl, comment, item, dump
    from faker import Faker
    from faker.providers import internet, profile

    from .telechecker.main import get_names
    from . import __name__, __version__, __url__

    logger.warning("需要输入一个toml格式的config文件.")
    logger.warning(f'您可以根据生成的参考配置文件 "{path}" 进行配置')

    fake = Faker()
    fake.add_provider(internet)
    fake.add_provider(profile)

    doc = document()
    doc.add(comment("This is an example config file."))
    doc.add(comment("Please fill in your account information."))
    doc.add(comment(f"See details: {__url__}#安装与使用"))
    doc.add(nl())
    doc.add(comment("将关键信息发送到第一个 Telegram 账号, 设为N以发送到第 N 个."))
    doc["notifier"] = True
    doc.add(nl())
    doc.add(comment("每个 Telegram Bot 签到的最大尝试时间 (秒)."))
    doc["timeout"] = 120
    doc.add(nl())
    doc.add(comment("每个 Telegram Bot 签到的最大尝试次数."))
    doc["retries"] = 4
    doc.add(nl())
    doc.add(comment("最大可同时进行的 Telegram Bot 签到."))
    doc["concurrent"] = 1
    doc.add(nl())
    doc.add(comment("计划任务时, 各站点之间签到的随机时间差异 (分钟)."))
    doc["random"] = 15
    doc.add(nl())
    doc.add(comment(f"代理设置, Emby 和 Telegram 均将通过此代理连接, 服务器位于国内时请配置代理并取消注释."))
    proxy = item(
        {
            "hostname": "127.0.0.1",
            "port": 1080,
            "scheme": "socks5",
        }
    )
    proxy["scheme"].comment("可选: http / socks5")
    for line in proxy.as_string().strip().split("\n"):
        doc.add(comment(line))
    doc.add(nl())
    doc.add(comment(f"服务设置, 当您需要禁用某些站点时, 请将该段取消注释并修改."))
    doc.add(comment(f"该部分内容是根据 {__name__.capitalize()} {__version__} 生成的."))
    service = item(
        {
            "service": {
                "checkiner": get_names("checkiner"),
                "monitor": get_names("monitor"),
                "messager": get_names("messager"),
            }
        }
    )
    for line in service.as_string().strip().split("\n"):
        doc.add(comment(line))
    doc.add(nl())
    doc.add(comment("Telegram 账号设置, 您可以重复该片段多次以增加多个账号."))
    telegram = []
    for _ in range(2):
        t = item(
            {
                "api_id": fake.numerify(text="########"),
                "api_hash": uuid.uuid4().hex,
                "phone": f'+861{fake.numerify(text="##########")}',
                "send": False,
                "monitor": False,
            }
        )
        t["api_id"].comment("通过 Telegram 官网申请 API: https://my.telegram.org/")
        t["api_hash"].comment("通过 Telegram 官网申请 API: https://my.telegram.org/")
        telegram.append(t)
    doc["telegram"] = telegram
    for t in doc["telegram"]:
        t.value.item("send").comment("启用该账号的自动水群功能 (谨慎使用)")
        t.value.item("monitor").comment("启用该账号的自动监控功能 (需要高级账号)")
    doc.add(nl())
    doc.add(comment("Emby 账号设置, 您可以重复该片段多次以增加多个账号."))
    emby = []
    for _ in range(2):
        t = item(
            {
                "url": fake.url(["https"]),
                "username": fake.profile()["username"],
                "password": fake.password(),
                "time": 10,
                "progress": 1000,
            }
        )
        t["time"].comment("模拟观看的时长 (秒)")
        t["progress"].comment("模拟观看后设置的时间进度 (秒)")
        emby.append(t)
    doc["emby"] = emby
    with open(path, "w+") as f:
        dump(doc, f)


def encrypt(data: str, password: str):
    from Crypto.Cipher import AES
    from Crypto import Random

    bs = AES.block_size
    pad = lambda s: s + (bs - len(s) % bs) * chr(bs - len(s) % bs)
    iv = Random.new().read(bs)
    padpass = hashlib.md5(password.encode()).hexdigest().encode()
    cipher = AES.new(padpass, AES.MODE_CBC, iv)
    data = cipher.encrypt(pad(data).encode())
    data = iv + data
    return data


def decrypt(data: bytes, password: str):
    from Crypto.Cipher import AES

    bs = AES.block_size
    if len(data) <= bs:
        return data.decode()
    unpad = lambda s: s[0 : -ord(s[-1:])]
    iv = data[:bs]
    padpass = hashlib.md5(password.encode()).hexdigest().encode()
    cipher = AES.new(padpass, AES.MODE_CBC, iv)
    data = unpad(cipher.decrypt(data[bs:]))
    return data.decode()


def interactive_config(config: dict = {}):
    from tomlkit import item
    from rich import get_console
    from rich.prompt import Prompt, IntPrompt, Confirm

    from . import __name__, __url__

    pad = " " * 23
    logger.info("我们将为您生成配置, 需要您根据提示填入信息, 并按回车确认, 您可以随时通过 Ctrl+C 结束运行.")
    logger.info(f"配置帮助详见: {__url__}.")
    telegrams = config.get("telegram", [])
    while True:
        if len(telegrams) > 0:
            logger.info(
                f'您当前填写了 {len(telegrams)} 个 Telegram 账号信息: {", ".join([t["phone"] for t in telegrams])}'
            )
            more = Confirm.ask(pad + "是否继续添加?", default=False)
        else:
            more = Confirm.ask(pad + "是否添加 Telegram 账号?", default=True)
            if more:
                logger.info(
                    f"为了使用 {__name__.capitalize()} 需要您开启您 Telegram 账号的 API 功能, 您可以从 Telegram 官网 (https://my.telegram.org/) 申请."
                )
                logger.info(
                    "(登陆后选择 API development tools, 随后应用信息可以随意填写, 若提示Error您可能需要再次多次点击提交, 或等待新账户脱离风控期/更换代理/清除浏览器记录并重试)"
                )
        if not more:
            break
        phone = Prompt.ask(pad + "请输入您的 Telegram 账号 (带国家区号) [dark_green](+861xxxxxxxxxx)[/]")
        api_id = Prompt.ask(pad + "请输入您的 Telegram api_id")
        api_hash = Prompt.ask(pad + "请输入您的 Telegram api_hash")
        monitor = Confirm.ask(pad + "是否开启该账号的自动监控功能? (需要高级账号)", default=False)
        telegrams.append(
            {"phone": phone, "api_id": api_id, "api_hash": api_hash, "send": False, "monitor": monitor}
        )
    embies = config.get("emby", [])
    while True:
        if len(embies) > 0:
            logger.info(f"您当前填写了 {len(embies)} 个 Emby 账号信息.")
            more = Confirm.ask(pad + "是否继续添加?", default=False)
        else:
            more = Confirm.ask(pad + "是否添加 Emby 账号?", default=True)
        if not more:
            break
        url = Prompt.ask(pad + "请输入您的 Emby 站点 URL <协议://域名:端口> [dark_green](https://abc.com:443)[/]")
        username = Prompt.ask(pad + "请输入您在该 Emby 站点的用户名")
        password = Prompt.ask(pad + "请输入您在该 Emby 站点的密码 (不显示, 按回车确认)", password=True)
        time = IntPrompt.ask(pad + "设置模拟观看时长 (秒)", default=10, show_default=True)
        progress = IntPrompt.ask(pad + "设置模拟观看后进度条位置 (秒)", default=1000, show_default=True)
        embies.append(
            {"url": url, "username": username, "password": password, "progress": progress, "time": time}
        )
    config = {"telegram": telegrams, "emby": embies}
    advanced = Confirm.ask(pad + "是否配置高级设置", default=False)
    config.setdefault("notifier", True)
    config.setdefault("timeout", 120)
    config.setdefault("retries", 4)
    config.setdefault("concurrent", 1)
    config.setdefault("random", 15)
    if advanced:
        logger.info("发送关键日志消息到以下哪个账户?")
        logger.info(f"\t0. 不使用消息推送功能")
        for i, t in enumerate(telegrams):
            logger.info(f'\t{i+1}. {t["phone"]}')
        config["notifier"] = IntPrompt.ask(pad + "请选择", default=1)
        config["timeout"] = IntPrompt.ask(
            pad + "设置每个 Telegram Bot 签到的最大尝试时间 (秒)", default=config["timeout"], show_default=True
        )
        config["retries"] = IntPrompt.ask(
            pad + "设置每个 Telegram Bot 签到的最大尝试次数", default=config["retries"], show_default=True
        )
        config["concurrent"] = IntPrompt.ask(
            pad + "设置最大可同时进行的 Telegram Bot 签到", default=config["concurrent"], show_default=True
        )
        config["random"] = IntPrompt.ask(
            pad + "设置计划任务时, 各站点之间签到的随机时间差异 (分钟)", default=config["random"], show_default=True
        )
    content = item(config).as_string()
    enc = Confirm.ask(pad + "是否生成加密配置 ([red]为了您的密钥安全, 强烈建议生成[/])", default=True)
    if enc:
        enc_password = Prompt.ask(pad + "请输入加密密码, 程序启动时将要求输入 (不显示, 按回车确认)", password=True)
        content = encrypt(content, enc_password)
    else:
        content = content.encode()
    content = base64.b64encode(content)
    logger.info(f"您的配置[green]已生成完毕[/]! 您需要将以下内容写入 SECRETS 变量配置 (名称: {__name__.upper()}_CONFIG)")
    print()
    get_console().rule("EMBYKEEPER_CONFIG")
    print(content.decode())
    print("\n\n")


def load_env_config(data: str):
    from rich.prompt import Prompt

    data = base64.b64decode(data.strip().encode())
    try:
        config = tomllib.loads(data.decode())
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        try:
            logger.info("您正在使用加密配置文件作为输入 (AES).")
            config = tomllib.loads(
                decrypt(data, Prompt.ask(" " * 23 + "您需要输入您的加密密钥 (不显示, 按回车确认)", password=True))
            )
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            config = {}
        if not config:
            logger.error("密钥无效或配置格式错误, 请删除 SECRETS 变量设置, 并重新配置.")
            sys.exit(252)
    else:
        logger.debug("您正在使用 SECRETS 变量配置.")
    return config


def prepare_config(config_file=None, public=False):
    from . import __name__

    env_config = os.environ.get(f"{__name__.upper()}_CONFIG", None)
    if env_config:
        config = load_env_config(env_config)
    else:
        if public:
            logger.warning("您正在使用公共仓库, 因此[red]请勿[/]将密钥存储于[red]任何配置文件[/].")
            config = {}
            if config_file:
                try:
                    with open(config_file, "rb") as f:
                        config = tomllib.load(f)
                except tomllib.TOMLDecodeError as e:
                    logger.error(f"TOML 配置文件错误: {e}.")
                    sys.exit(252)
                else:
                    logger.info(f"将以 {Path(config_file).name} 为基础生成配置.")
            interactive_config(config)
            sys.exit(0)
        default_config_file = Path("config.toml")
        if not config_file:
            if not default_config_file.exists():
                write_faked_config(default_config_file)
                sys.exit(250)
            else:
                config_file = default_config_file
        try:
            if not Path(config_file).exists():
                logger.error(f'配置文件 "{config_file}" 不存在.')
                sys.exit(251)
            elif config_file == default_config_file:
                with open(config_file, "rb") as f:
                    config = tomllib.load(f)
                if not config:
                    write_faked_config(config_file)
                    sys.exit(250)
            else:
                with open(config_file, "rb") as f:
                    config = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            logger.error(f"TOML 配置文件错误: {e}.")
            sys.exit(252)
    error = check_config(config)
    if error:
        logger.error(f"配置文件错误, 请检查配置文件:\n{error}.")
        sys.exit(253)
    proxy: dict = config.get("proxy", None)
    if proxy:
        proxy.setdefault("scheme", "socks5")
        proxy.setdefault("hostname", "127.0.0.1")
        proxy.setdefault("port", 1080)
    return config
