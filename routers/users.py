from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import aiosqlite
from datetime import timedelta

from schemas import UserCreate
from auth import authenticate_user, create_access_token, get_current_active_user, get_password_hash
from database import get_db
from crud import create_user as crud_create_user, get_user_by_username, get_user_by_email

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="templates")

@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    context = {
        "request": request,
        "current_user": getattr(request.state, 'current_user', None),
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    return templates.TemplateResponse("register.html", context)

@router.post("/register")
async def register(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    form_data = await request.form()
    
    user_data = UserCreate(
        email=form_data.get("email"),
        username=form_data.get("username"),
        full_name=form_data.get("full_name"),
        password=form_data.get("password")
    )
    
    # Check if username exists
    existing_user = await get_user_by_username(db, user_data.username)
    if existing_user:
        context = {
            "request": request,
            "current_user": getattr(request.state, 'current_user', None),
            "cart_count": getattr(request.state, 'cart_count', 0),
            "error": "Username already registered"
        }
        return templates.TemplateResponse("register.html", context)
    
    # Check if email exists
    existing_email = await get_user_by_email(db, user_data.email)
    if existing_email:
        context = {
            "request": request,
            "current_user": getattr(request.state, 'current_user', None),
            "cart_count": getattr(request.state, 'cart_count', 0),
            "error": "Email already registered"
        }
        return templates.TemplateResponse("register.html", context)
    
    user_id = await crud_create_user(db, user_data)
    
    # Auto login after registration
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=f"bearer {access_token}", httponly=True)
    return response

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    context = {
        "request": request,
        "current_user": getattr(request.state, 'current_user', None),
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    return templates.TemplateResponse("login.html", context)

@router.post("/login")
async def login_for_access_token(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    
    user = await authenticate_user(username, password)
    if not user:
        context = {
            "request": request,
            "current_user": getattr(request.state, 'current_user', None),
            "cart_count": getattr(request.state, 'cart_count', 0),
            "error": "Incorrect username or password"
        }
        return templates.TemplateResponse("login.html", context)
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=f"bearer {access_token}", httponly=True)
    return response

@router.get("/me", response_class=HTMLResponse)
async def read_users_me(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    context = {
        "request": request,
        "user": current_user,
        "current_user": current_user,
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    return templates.TemplateResponse("profile.html", context)

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response