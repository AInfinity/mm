import pyodbc
from config import DB_SERVER, DB_NAME, DB_USERNAME, DB_PASSWORD, DB_DRIVER

def get_db_connection():
    conn_str = f'DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USERNAME};PWD={DB_PASSWORD}'
    return pyodbc.connect(conn_str)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
        CREATE TABLE users (
            id INT PRIMARY KEY IDENTITY(1,1),
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(200) NOT NULL,
            created_at DATETIME DEFAULT GETDATE()
        )
    ''')
    
    # Create MealPlans table
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='meal_plans' AND xtype='U')
        CREATE TABLE meal_plans (
            id INT PRIMARY KEY IDENTITY(1,1),
            user_id INT,
            recipe_id INT,
            date DATE,
            meal_type VARCHAR(20),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close() 