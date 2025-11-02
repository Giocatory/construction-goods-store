from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import aiosqlite

from auth import get_current_active_user

router = APIRouter(prefix="/products", tags=["products"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def read_products(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    category: str = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        db.row_factory = aiosqlite.Row
        
        if category:
            products = await get_products(db, skip=skip, limit=limit, category=category)
        else:
            products = await get_products(db, skip=skip, limit=limit)
        
        # Get unique categories for filter
        async with db.execute("SELECT DISTINCT category FROM products WHERE is_active = TRUE") as cursor:
            categories = [row[0] for row in await cursor.fetchall()]
    
    context = {
        "request": request,
        "products": products,
        "categories": categories,
        "selected_category": category,
        "current_user": current_user,
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    
    return templates.TemplateResponse("products.html", context)

@router.get("/{product_id}", response_class=HTMLResponse)
async def read_product(
    request: Request,
    product_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        db.row_factory = aiosqlite.Row
        product = await get_product(db, product_id)
        
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    context = {
        "request": request,
        "product": product,
        "current_user": current_user,
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    
    return templates.TemplateResponse("product_detail.html", context)

# Import functions from crud
from crud import get_products, get_product