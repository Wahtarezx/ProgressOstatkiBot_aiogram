from .menu import router as msg_routers
from .create_bonus_card import router as create_bonus_card_routers

loyalty_routers = [
    msg_routers,
    create_bonus_card_routers,
]
