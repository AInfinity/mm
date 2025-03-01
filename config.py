import os

# API Configuration
SPOONACULAR_API_KEY = 'da6f49a4979c4bda9781caf077009fbc'

# Database Configuration
DB_SERVER = 'meatmealgroup2.database.windows.net'
DB_NAME = 'meatmeal2'
DB_USERNAME = 'group2'
DB_PASSWORD = 'Seniorproject!'
DB_DRIVER = '{ODBC Driver 17 for SQL Server}'

# Session Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Production Settings
DEBUG = False
