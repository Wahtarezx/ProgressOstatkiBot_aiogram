from .login import router as login_router
from .documents.menu import router as menu_router
from .documents.accept import router as accept_router
from .documents.doc_info import router as doc_info_router
from .draftbeer.add import router as draftbeer_add_router
from .draftbeer.info import router as draftbeer_info_router
from .draftbeer.menu import router as draftbeer_menu_router

edo_routers = [
    login_router,
    menu_router,
    accept_router,
    doc_info_router,
    draftbeer_add_router,
    draftbeer_info_router,
    draftbeer_menu_router,
]
