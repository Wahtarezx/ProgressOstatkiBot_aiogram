from .msg_admin import router as msg_routers
from .accept_without_scan import router as awc_routers
from .choose_role import router as choose_role_routers
from .create_post import router as create_post_routers

routers = [
    msg_routers,
    awc_routers,
    choose_role_routers,
    create_post_routers,
]
