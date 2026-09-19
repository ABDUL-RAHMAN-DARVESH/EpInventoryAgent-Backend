from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.customers import router as customers_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.manufacturers import router as manufacturers_router
from app.api.routes.payments import router as payments_router
from app.api.routes.products import router as products_router
from app.api.routes.purchases import router as purchases_router
from app.api.routes.sales import router as sales_router
from app.api.routes.version import router as version_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(version_router)
api_router.include_router(customers_router)
api_router.include_router(sales_router)
api_router.include_router(manufacturers_router)
api_router.include_router(purchases_router)
api_router.include_router(products_router)
api_router.include_router(payments_router)
api_router.include_router(dashboard_router)
