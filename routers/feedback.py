from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import aiosqlite

from schemas import FeedbackCreate
from auth import get_current_active_user

router = APIRouter(prefix="/feedback", tags=["feedback"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def feedback_form(request: Request):
    context = {
        "request": request,
        "current_user": getattr(request.state, 'current_user', None),
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    return templates.TemplateResponse("feedback.html", context)

@router.post("/")
async def create_feedback_message(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    form_data = await request.form()
    feedback_data = FeedbackCreate(
        subject=form_data.get("subject"),
        message=form_data.get("message"),
        email=current_user["email"] if current_user else form_data.get("email")
    )
    
    user_id = current_user["id"] if current_user else None
    
    async with aiosqlite.connect("construction_store.db") as db:
        await db.execute(
            "INSERT INTO feedback (user_id, subject, message, email) VALUES (?, ?, ?, ?)",
            (user_id, feedback_data.subject, feedback_data.message, feedback_data.email)
        )
        await db.commit()
    
    context = {
        "request": request,
        "current_user": current_user,
        "cart_count": getattr(request.state, 'cart_count', 0),
        "message": "Feedback submitted successfully!"
    }
    return templates.TemplateResponse("feedback.html", context)