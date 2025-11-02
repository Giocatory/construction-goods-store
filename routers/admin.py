from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import aiosqlite

from auth import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin: dict = Depends(get_current_admin_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        db.row_factory = aiosqlite.Row
        
        # Get stats
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            user_count = (await cursor.fetchone())[0]
        
        async with db.execute("SELECT COUNT(*) FROM products") as cursor:
            product_count = (await cursor.fetchone())[0]
        
        async with db.execute("SELECT COUNT(*) FROM feedback WHERE is_read = FALSE") as cursor:
            unread_feedback = (await cursor.fetchone())[0]
    
    context = {
        "request": request,
        "user_count": user_count,
        "product_count": product_count,
        "unread_feedback": unread_feedback,
        "current_user": admin,
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    
    return templates.TemplateResponse("admin/dashboard.html", context)

@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    admin: dict = Depends(get_current_admin_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cursor:
            users = await cursor.fetchall()
    
    context = {
        "request": request,
        "users": users,
        "current_user": admin,
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    
    return templates.TemplateResponse("admin/users.html", context)

@router.get("/feedback", response_class=HTMLResponse)
async def admin_feedback(
    request: Request,
    admin: dict = Depends(get_current_admin_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT f.*, u.username 
               FROM feedback f 
               LEFT JOIN users u ON f.user_id = u.id 
               ORDER BY f.created_at DESC"""
        ) as cursor:
            feedback_messages = await cursor.fetchall()
    
    context = {
        "request": request,
        "feedback_messages": feedback_messages,
        "current_user": admin,
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    
    return templates.TemplateResponse("admin/feedback.html", context)

@router.post("/users/{user_id}/toggle")
async def toggle_user_status(
    user_id: int,
    request: Request,
    admin: dict = Depends(get_current_admin_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        async with db.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            new_status = not user["is_active"]
            await db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
            await db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/feedback/{feedback_id}/mark-read")
async def mark_feedback_read(
    feedback_id: int,
    request: Request,
    admin: dict = Depends(get_current_admin_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        await db.execute("UPDATE feedback SET is_read = TRUE WHERE id = ?", (feedback_id,))
        await db.commit()
    
    return RedirectResponse(url="/admin/feedback", status_code=303)