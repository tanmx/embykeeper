from .base import Messager
from .common import GOOD_DAY_NIGHT


class PornembyMessager(Messager):
    name = "Pornemby"
    chat_name = "Pornemby"
    messages = [*GOOD_DAY_NIGHT]