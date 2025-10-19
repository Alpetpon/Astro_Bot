from .start import router as start_router
from .menu import router as menu_router
from .courses import router as courses_router
from .consultations import router as consultations_router
from .cabinet import router as cabinet_router
from .payments_handler import router as payments_router
from .reviews import router as reviews_router
from .admin import router as admin_router
from .admin_guides import router as admin_guides_router
from .admin_reviews import router as admin_reviews_router
from .admin_video import router as admin_video_router
from .admin_mini_course import router as admin_mini_course_router

__all__ = [
    'start_router',
    'menu_router',
    'courses_router',
    'consultations_router',
    'cabinet_router',
    'payments_router',
    'reviews_router',
    'admin_router',
    'admin_guides_router',
    'admin_reviews_router',
    'admin_video_router',
    'admin_mini_course_router'
]

