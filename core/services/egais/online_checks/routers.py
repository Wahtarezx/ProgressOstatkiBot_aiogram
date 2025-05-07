from core.services.egais.online_checks.degustation import router as scan_bottle_router
from core.services.egais.online_checks.ttn.ttn import router as ttn_router
from core.services.egais.online_checks.basic import router as basic_router

online_check_routers = [
    scan_bottle_router,
    ttn_router,
    basic_router,
]
