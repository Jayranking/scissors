from fastapi import FastAPI
from Middleware.auth import router
from Routes.url import url_router
from starlette.staticfiles import StaticFiles


app = FastAPI()

# static file
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include the router
app.include_router(router)
app.include_router(url_router)


