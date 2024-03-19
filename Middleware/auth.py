from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from pydantic import BaseModel
from models import User
from passlib.context import CryptContext
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from starlette import status
from Database.database import SessionLocal
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse


router = APIRouter(
    tags= ["Authentication"]
) 

templates = Jinja2Templates(directory="templates")

SECRET_KEY = '3a58b71435f0c7d8f9be1ab9792e9c30598f203c4c971f6d0d788539c3c51f78'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

class CreateUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    async def create_outh_form(self):
        form = await self.request.form()
        self.username = form.get('username')
        self.password = form.get('password')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def authenticate_user(db, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user
 
def create_access_token(username: str,  user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id':user_id}
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request):
    try:
        token = request.cookies.get("access_token")
        if token is None:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None or user_id is None:
            return None
        return {"username": username, "id": user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

# create a new user 
@router.post('/create_user', status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    create_user_model = User(
        first_name = create_user_request.first_name,
        last_name = create_user_request.last_name,
        email = create_user_request.email,
        username = create_user_request.username,
        hashed_password = bcrypt_context.hash(create_user_request.password),
        role = create_user_request.role,
        is_active = True
    )

    db.add(create_user_model)
    db.commit()

@router.post('/token', response_model=Token)
async def login_for_access_token(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        # return False
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    
    token = create_access_token(user.username, user.id, timedelta(minutes=30))

    response.set_cookie(key="access_token", value=token, httponly=True)

    return Token(access_token=token, token_type="bearer")

@router.get('/login', response_class=HTMLResponse)
async def authenticationpage(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})

@router.post('/login', response_class=HTMLResponse)
async def login(request:Request, db: db_dependency):
    try:
        form = LoginForm(request)
        await form.create_outh_form()
        response = RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)

        validate_user_cookie = await login_for_access_token(response=response, form_data=form, db=db)

        if not validate_user_cookie:
            msg = "Invalid username or password" 
            return templates.TemplateResponse('login.html', {'request': request, 'msg': msg})
        return response
    except HTTPException:
        msg = "Invalid username or password" 
        return templates.TemplateResponse('login.html', {'request': request, 'msg': msg})

@router.get('/logout', response_class=HTMLResponse)
async def logout(request: Request):
    msg = "Logged out successfully"
    response = templates.TemplateResponse('login.html', {'request': request, 'msg': msg})
    response.delete_cookie(key="access_token")
    return response

@router.get('/register', response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})

@router.post('/register', response_class=HTMLResponse)
async def register_user(request: Request, db: db_dependency, first_name: str = Form(...), last_name: str = Form(...), email: str = Form(...), username: str = Form(...), password: str = Form(...)):
    
    validation1 = db.query(User).filter(User.username == username).first()

    validation2 = db.query(User).filter(User.email == email).first()

    if validation1 or validation2:
        msg = "Username or email already exists"
        return templates.TemplateResponse('register.html', {'request': request, 'msg': msg})
    
    user_model = User()
    user_model.first_name = first_name
    user_model.last_name = last_name
    user_model.email = email
    user_model.username = username
    user_model.hashed_password = bcrypt_context.hash(password)
    user_model.is_active = True

    db.add(user_model)
    db.commit()
    db.refresh(user_model)
    
    msg = "Registered successfully"
    return templates.TemplateResponse('login.html', {'request': request, 'msg': msg})


