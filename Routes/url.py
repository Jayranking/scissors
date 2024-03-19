from fastapi import Depends, HTTPException, APIRouter, Request
from typing import Annotated
from sqlalchemy.orm import Session
import models
from models import Url
from starlette import status
from Database.database import engine, SessionLocal
from Middleware.auth import get_current_user
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import secrets
import qrcode
import os
from pydantic import BaseModel


url_router = APIRouter()

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)] 

class ShortenURLRequest(BaseModel):
    long_url: str

@url_router.get('/', response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@url_router.get('/dashboard', response_class=HTMLResponse)
async def dashboard(request: Request, user: user_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized')
    return templates.TemplateResponse('dashboard.html', {'request': request})

@url_router.get('/shorten', response_class=HTMLResponse)
async def dashboard(request: Request, user: user_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized')
    return templates.TemplateResponse('shorten.html', {'request': request})
    

@url_router.get("/history", response_class=HTMLResponse)
async def url_history(request: Request, user: user_dependency, db: Session = Depends(get_db)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized')
 
    urls = db.query(Url).all()  
    return templates.TemplateResponse("history.html", {"request": request, "urls": urls})


@url_router.post("/shorten/", response_model=dict)
async def shorten_url(url_request: ShortenURLRequest, db: Session = Depends(get_db)):
    short_id = secrets.token_urlsafe(5)
    url_model = Url(short_id=short_id, long_url=url_request.long_url)
    db.add(url_model)
    db.commit()
    # Generate QR code
    qr_code_path = generate_qr_code(url_request.long_url, short_id)
    return {"short_url": f"/{short_id}", "qr_code_path": qr_code_path}


@url_router.get("/{short_id}/", response_class=HTMLResponse)
async def redirect_to_long_url(short_id: str, db: Session = Depends(get_db)):
    url = db.query(Url).filter(Url.short_id == short_id).first()
    if url is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return templates.TemplateResponse("redirect.html", {"request": None, "long_url": url.long_url})

@url_router.get("/{short_id}/qr")
async def get_qr_code(short_id: str):
    # Retrieve the path to the QR code image
    qr_code_path = os.path.join("static", "qr_codes", f"{short_id}.png")
    if os.path.exists(qr_code_path):
        return FileResponse(qr_code_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="QR Code not found")


# Function to generate QR Code
def generate_qr_code(data: str, short_id: str):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    qr_code_path = os.path.join("static", "qr_codes", f"{short_id}.png")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(qr_code_path), exist_ok=True)
    
    # Save the QR code image to a file
    qr.make_image(fill_color="black", back_color="white").save(qr_code_path)
    return qr_code_path



@url_router.post("/delete/{url_id}", response_class=HTMLResponse)
async def delete_url(url_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db), request: Request = None):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized')

    url = db.query(Url).filter(Url.id == url_id).first()
    if url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    db.delete(url)
    db.commit()

    urls = db.query(Url).all()

    success_message = "URL deleted successfully"

    return templates.TemplateResponse("history.html", {"request": request, "urls": urls, "success_message": success_message})
