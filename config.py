import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("Tyuya0326")
    SQLALCHEMY_DATABASE_URI = os.getenv("postgresql://neondb_owner:npg_4UK9mgdCTlvG@ep-bitter-darkness-ad988r56-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
