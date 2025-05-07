from .cmd import router as msg_routers
from .last_ostatki import router as last_ostatki_routers
from .list_ostatki import router as list_ostatki_routers

routers = [
    msg_routers,
    last_ostatki_routers,
    list_ostatki_routers,
]
