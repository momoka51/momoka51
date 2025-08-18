from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# SQLAlchemyのインスタンスを作成
db = SQLAlchemy()

class SavedRecipe(db.Model):
    __tablename__ = 'saved_recipes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    ingredients = db.Column(db.Text)
    method = db.Column(db.Text)
    ingredients_part = db.Column(db.Text)
    method_part = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FridgeItem(db.Model):
    __tablename__ = 'fridge_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    expiration_date = db.Column(db.Date, nullable=False)
    expiration_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class StorageDay(db.Model):
    __tablename__ = 'storage_days'

    name = db.Column(db.String(100), primary_key=True)
    days = db.Column(db.Integer, nullable=False)

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 