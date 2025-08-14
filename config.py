# import os
# from dotenv import load_dotenv

# class Config:
#     SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
#     # まずは DATABASE_URL を見る。なければ個別のDB_*から組み立てる（保険）
#     SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or (
#         f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
#         f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
#     )
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     UPLOAD_FOLDER = "static/image"

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Flaskアプリケーションの設定クラス"""

    # 必須: Renderで設定したSECRET_KEYを読み込む
    SECRET_KEY = os.getenv("SECRET_KEY")

    # 必須: Renderで設定したDATABASE_URLを読み込む
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    # 以下は固定値
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "static/image"