from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite

from auth import get_current_active_user

router = APIRouter(prefix="/cart", tags=["cart"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def view_cart(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        db.row_factory = aiosqlite.Row
        cart_items = await get_cart_items(db, current_user["id"])
        
        total = sum(item["price"] * item["quantity"] for item in cart_items)
    
    context = {
        "request": request,
        "cart_items": cart_items,
        "total": total,
        "current_user": current_user,
        "cart_count": getattr(request.state, 'cart_count', 0)
    }
    
    return templates.TemplateResponse("cart.html", context)

@router.post("/add/{product_id}")
async def add_to_cart(
    product_id: int,
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    form_data = await request.form()
    quantity = int(form_data.get("quantity", 1))
    
    async with aiosqlite.connect("construction_store.db") as db:
        # Check if product exists
        product = await get_product(db, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Add to cart
        await add_to_cart(db, current_user["id"], product_id, quantity)
    
    return RedirectResponse(url="/cart/", status_code=303)

@router.post("/update/{product_id}")
async def update_cart_item(
    product_id: int,
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    form_data = await request.form()
    quantity = int(form_data.get("quantity", 1))
    
    async with aiosqlite.connect("construction_store.db") as db:
        await update_cart_item(db, current_user["id"], product_id, quantity)
    
    return RedirectResponse(url="/cart/", status_code=303)

@router.post("/remove/{product_id}")
async def remove_from_cart(
    product_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        await remove_from_cart(db, current_user["id"], product_id)
    
    return RedirectResponse(url="/cart/", status_code=303)

@router.post("/clear")
async def clear_cart(
    current_user: dict = Depends(get_current_active_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        await clear_cart(db, current_user["id"])
    
    return RedirectResponse(url="/cart/", status_code=303)

@router.post("/checkout")
async def checkout(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    async with aiosqlite.connect("construction_store.db") as db:
        db.row_factory = aiosqlite.Row
        
        # Get cart items
        cart_items = await get_cart_items(db, current_user["id"])
        
        if not cart_items:
            context = {
                "request": request,
                "cart_items": [],
                "total": 0,
                "current_user": current_user,
                "cart_count": getattr(request.state, 'cart_count', 0),
                "error": "Корзина пуста"
            }
            return templates.TemplateResponse("cart.html", context)
        
        # Check stock availability
        for item in cart_items:
            if item["quantity"] > item["stock_quantity"]:
                context = {
                    "request": request,
                    "cart_items": cart_items,
                    "total": sum(item["price"] * item["quantity"] for item in cart_items),
                    "current_user": current_user,
                    "cart_count": getattr(request.state, 'cart_count', 0),
                    "error": f"Недостаточно товара '{item['name']}' в наличии"
                }
                return templates.TemplateResponse("cart.html", context)
        
        # Create order
        order_id = await create_order(db, current_user["id"], cart_items)
        
        # Update product stock
        for item in cart_items:
            new_stock = item["stock_quantity"] - item["quantity"]
            await db.execute(
                "UPDATE products SET stock_quantity = ? WHERE id = ?",
                (new_stock, item["product_id"])
            )
        
        # Clear cart
        await clear_cart(db, current_user["id"])
        
        await db.commit()
    
    context = {
        "request": request,
        "cart_items": [],
        "total": 0,
        "current_user": current_user,
        "cart_count": getattr(request.state, 'cart_count', 0),
        "message": f"Заказ №{order_id} успешно оформлен! Товары куплены."
    }
    return templates.TemplateResponse("cart.html", context)

# Import functions from crud
from crud import get_cart_items, add_to_cart, update_cart_item, remove_from_cart, clear_cart, create_order, get_product