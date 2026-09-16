from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.db.models import Base
from app.db.session import engine

app = FastAPI(title="GharSeva API")

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(users_router)
