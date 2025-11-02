from typing import List, Optional
import aiosqlite
from schemas import UserCreate, ProductCreate, FeedbackCreate

# User operations
async def create_user(db: aiosqlite.Connection, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    async with db.execute(
        "INSERT INTO users (email, username, hashed_password, full_name) VALUES (?, ?, ?, ?)",
        (user.email, user.username, hashed_password, user.full_name)
    ) as cursor:
        await db.commit()
        return cursor.lastrowid

async def get_user_by_username(db: aiosqlite.Connection, username: str):
    async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
        return await cursor.fetchone()

async def get_user_by_email(db: aiosqlite.Connection, email: str):
    async with db.execute("SELECT * FROM users WHERE email = ?", (email,)) as cursor:
        return await cursor.fetchone()

# Product operations
async def get_products(db: aiosqlite.Connection, skip: int = 0, limit: int = 100, 
                      category: Optional[str] = None):
    if category:
        async with db.execute(
            "SELECT * FROM products WHERE is_active = TRUE AND category = ? LIMIT ? OFFSET ?",
            (category, limit, skip)
        ) as cursor:
            return await cursor.fetchall()
    else:
        async with db.execute(
            "SELECT * FROM products WHERE is_active = TRUE LIMIT ? OFFSET ?",
            (limit, skip)
        ) as cursor:
            return await cursor.fetchall()

async def get_product(db: aiosqlite.Connection, product_id: int):
    async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
        return await cursor.fetchone()

# Cart operations
async def add_to_cart(db: aiosqlite.Connection, user_id: int, product_id: int, quantity: int = 1):
    # Check if product already in cart
    async with db.execute(
        "SELECT * FROM cart WHERE user_id = ? AND product_id = ?",
        (user_id, product_id)
    ) as cursor:
        existing = await cursor.fetchone()
    
    if existing:
        # Update quantity
        new_quantity = existing["quantity"] + quantity
        async with db.execute(
            "UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?",
            (new_quantity, user_id, product_id)
        ) as cursor:
            await db.commit()
            return cursor.rowcount
    else:
        # Add new item
        async with db.execute(
            "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
            (user_id, product_id, quantity)
        ) as cursor:
            await db.commit()
            return cursor.lastrowid

async def get_cart_items(db: aiosqlite.Connection, user_id: int):
    async with db.execute('''
        SELECT c.*, p.name, p.price, p.image_url, p.stock_quantity 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?
    ''', (user_id,)) as cursor:
        return await cursor.fetchall()

async def update_cart_item(db: aiosqlite.Connection, user_id: int, product_id: int, quantity: int):
    if quantity <= 0:
        # Remove item if quantity is 0 or less
        await remove_from_cart(db, user_id, product_id)
        return 1
    
    async with db.execute(
        "UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?",
        (quantity, user_id, product_id)
    ) as cursor:
        await db.commit()
        return cursor.rowcount

async def remove_from_cart(db: aiosqlite.Connection, user_id: int, product_id: int):
    async with db.execute(
        "DELETE FROM cart WHERE user_id = ? AND product_id = ?",
        (user_id, product_id)
    ) as cursor:
        await db.commit()
        return cursor.rowcount

async def clear_cart(db: aiosqlite.Connection, user_id: int):
    async with db.execute(
        "DELETE FROM cart WHERE user_id = ?",
        (user_id,)
    ) as cursor:
        await db.commit()
        return cursor.rowcount

async def create_order(db: aiosqlite.Connection, user_id: int, cart_items: list):
    # Calculate total amount
    total = sum(item["price"] * item["quantity"] for item in cart_items)
    
    # Create order
    async with db.execute(
        "INSERT INTO orders (user_id, total_amount) VALUES (?, ?)",
        (user_id, total)
    ) as cursor:
        order_id = cursor.lastrowid
        
        # Add order items
        for item in cart_items:
            await db.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                (order_id, item["product_id"], item["quantity"], item["price"])
            )
        
        await db.commit()
        return order_id

# Import get_password_hash from auth
from auth import get_password_hash