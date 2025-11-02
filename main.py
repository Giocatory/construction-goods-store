from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import aiosqlite

from database import init_db
from routers import users, products, feedback, admin, cart
from auth import get_current_user

app = FastAPI(title="Construction Store", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(users.router)
app.include_router(products.router)
app.include_router(feedback.router)
app.include_router(admin.router)
app.include_router(cart.router)

templates = Jinja2Templates(directory="templates")

# Добавляем функции min и range в окружение Jinja2
templates.env.globals.update(min=min, range=range)

@app.on_event("startup")
async def on_startup():
    await init_db()

# Middleware для добавления информации о пользователе в запрос
@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    # Получаем пользователя из токена
    try:
        current_user = await get_current_user(request)
        request.state.current_user = current_user
        
        # Получаем количество товаров в корзине
        cart_count = 0
        if current_user:
            async with aiosqlite.connect("construction_store.db") as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT SUM(quantity) as total FROM cart WHERE user_id = ?", 
                    (current_user["id"],)
                ) as cursor:
                    result = await cursor.fetchone()
                    cart_count = result["total"] if result and result["total"] else 0
        
        request.state.cart_count = cart_count
    except Exception as e:
        # Если произошла ошибка, устанавливаем значения по умолчанию
        request.state.current_user = None
        request.state.cart_count = 0
        print(f"Error in middleware: {e}")
    
    response = await call_next(request)
    return response

# Функция для добавления cart_count во все шаблоны
def add_cart_count_to_templates(request: Request, context: dict):
    context.update({
        "cart_count": getattr(request.state, 'cart_count', 0),
        "current_user": getattr(request.state, 'current_user', None)
    })
    return context

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    async with aiosqlite.connect("construction_store.db") as db:
        db.row_factory = aiosqlite.Row
        
        # Get featured products
        async with db.execute("SELECT * FROM products WHERE is_active = TRUE LIMIT 6") as cursor:
            featured_products = await cursor.fetchall()
        
        # Get categories
        async with db.execute("SELECT DISTINCT category FROM products WHERE is_active = TRUE LIMIT 5") as cursor:
            categories = [row[0] for row in await cursor.fetchall()]
    
    context = {
        "request": request,
        "featured_products": featured_products,
        "categories": categories
    }
    context = add_cart_count_to_templates(request, context)
    
    return templates.TemplateResponse("index.html", context)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)