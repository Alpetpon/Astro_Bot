from .start import router as start_router
from .menu import router as menu_router
from .courses import router as courses_router
from .consultations import router as consultations_router
from .cabinet import router as cabinet_router
from .payments_handler import router as payments_router

__all__ = [
    'start_router',
    'menu_router',
    'courses_router',
    'consultations_router',
    'cabinet_router',
    'payments_router'
]

