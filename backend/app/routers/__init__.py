from .public import router as public_router
from .internal import router as internal_router
from .admin import router as admin_router

__all__ = ["public_router", "internal_router", "admin_router"]
