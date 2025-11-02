import aiosqlite
import os

DATABASE_URL = "construction_store.db"

async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        
        # Users table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                is_superuser BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Products table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                category TEXT NOT NULL,
                image_url TEXT,
                stock_quantity INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Feedback table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                email TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Cart table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (product_id) REFERENCES products (id),
                UNIQUE(user_id, product_id)
            )
        ''')
        
        # Orders table (для истории заказов)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                status TEXT DEFAULT 'completed',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Order items table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # Create default admin user
        from auth import get_password_hash
        admin_password = get_password_hash("admin123")
        
        await db.execute('''
            INSERT OR IGNORE INTO users 
            (email, username, hashed_password, full_name, is_superuser)
            VALUES (?, ?, ?, ?, ?)
        ''', ("admin@store.com", "admin", admin_password, "Administrator", True))
        
        # Insert sample products
        sample_products = [
            ("Молоток строительный", "Профессиональный молоток с фиберглассовой ручкой", 25.99, "Инструменты", "/static/images/hammer.jpg", 50),
            ("Шуруповерт аккумуляторный", "Беспроводной шуруповерт 18V", 89.99, "Электроинструменты", "/static/images/screwdriver.jpg", 30),
            ("Цемент М500", "Цемент марки М500, мешок 50кг", 8.99, "Строительные материалы", "/static/images/cement.jpg", 100),
            ("Кирпич строительный", "Красный керамический кирпич", 0.45, "Строительные материалы", "/static/images/brick.jpg", 1000),
            ("Доска обрезная", "Сосновая доска 50x100x3000мм", 3.99, "Пиломатериалы", "/static/images/board.jpg", 200),
            ("Краска акриловая", "Водостойкая акриловая краска белая, 5л", 24.99, "Отделочные материалы", "/static/images/paint.jpg", 75),
            ("Плитка керамическая", "Напольная плитка 30x30см", 12.99, "Отделочные материалы", "/static/images/tile.jpg", 150),
            ("Перфоратор", "Мощный перфоратор 800Вт", 120.99, "Электроинструменты", "/static/images/perforator.jpg", 20),
        ]
        
        await db.executemany('''
            INSERT OR IGNORE INTO products 
            (name, description, price, category, image_url, stock_quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)
        
        await db.commit()

async def get_db():
    db = await aiosqlite.connect(DATABASE_URL)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        yield db
    finally:
        await db.close()