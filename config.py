import os
from dotenv import load_dotenv

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    # まずは DATABASE_URL を見る。なければ個別のDB_*から組み立てる（保険）
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "static/image"