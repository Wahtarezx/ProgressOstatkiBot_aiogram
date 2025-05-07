from .msg_provider import router as msg_routers
from .provider_analytics import router as provider_analytics_routers

routers = [
    msg_routers,
    provider_analytics_routers,
]
