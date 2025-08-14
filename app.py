from flask import Flask, render_template, request, url_for, redirect, flash, jsonify
import os
from datetime import datetime, date, timezone
import google.generativeai as genai
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
# 内部モジュールのインポート
from config import Config
from model import recognize_ingredients, suggest_recipes, parse_nutrition_data, plot_nutrition_pie
from models import db, SavedRecipe, FridgeItem, StorageDay
from dotenv import load_dotenv

load_dotenv()
# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# config.pyから設定を読み込む
app.config.from_object(Config)


# UPLOAD_FOLDERの設定
# UPLOAD_FOLDER = 'static/image'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# SQLAlchemyとMigrateをアプリケーションに連携
# models.pyで作成されたdbインスタンスをここでアプリに紐付けます
#db = SQLAlchemy(app)

os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/image'), exist_ok=True)

# ★ models.py 由来の db をアプリにバインド（新しく作らない）
db.init_app(app)

migrate = Migrate(app, db)


# 📌 材料と作り方を分割する関数
def split_recipe_parts(recipe_text):
    if "作り方" in recipe_text:
        parts = recipe_text.split("作り方", 1)
        ingredients = parts[0].strip()
        method = "作り方" + parts[1].strip()
    else:
        ingredients = recipe_text
        method = ""
    return ingredients, method


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['upload_file']
        if file and file.filename:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('choose_action', filename=filename))
    return render_template('index.html')


@app.route('/generate_recipes', methods=['POST'])
def generate_recipes():
    edited_ingredients = request.form['edited_ingredients']
    recipes = suggest_recipes(edited_ingredients)
    nutrition_info = parse_nutrition_data(recipes)
    graphs = {name: plot_nutrition_pie(nut) for name, nut in nutrition_info.items()}
    formatted_recipes = recipes.replace('\n', '<br>')
    ingredients_part, method_part = split_recipe_parts(formatted_recipes)
    return render_template('result.html',
                           image_path=None,
                           ingredients=edited_ingredients,
                           ingredients_part=ingredients_part,
                           method_part=method_part,
                           graphs=graphs)


@app.route('/saved_recipes', methods=['GET'])

@app.route('/saved_recipes', methods=['GET', 'POST'])
def saved_recipes():
    # result.html からの保存フォームを受ける（POST）
    if request.method == 'POST':
        title = request.form.get('title') or '新しいレシピ'
        ingredients = request.form.get('ingredients') or ''           # hidden
        method = request.form.get('method') or ''                     # textarea
        ingredients_part = request.form.get('ingredients_part') or '' # hidden
        method_part = request.form.get('method_part') or ''           # hidden

        if not ingredients and not method:
            flash('保存できるレシピ内容がありません。')
            return redirect(url_for('saved_recipes'))

        try:
            rec = SavedRecipe(
                title=title,
                ingredients=ingredients,
                method=method,
                ingredients_part=ingredients_part,
                method_part=method_part,
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(rec)
            db.session.commit()
            flash('レシピを保存しました。')
        except Exception as e:
            db.session.rollback()
            app.logger.exception(e)
            flash('レシピの保存に失敗しました。')

        return redirect(url_for('saved_recipes'))

    # GET：一覧表示
    try:
        recipes = SavedRecipe.query.order_by(SavedRecipe.id.desc()).all()
        return render_template('saved_recipes.html', recipes=recipes)
    except Exception as e:
        app.logger.exception(e)
        flash('保存されたレシピの読み込みに失敗しました。')
        return render_template('saved_recipes.html', recipes=[])



@app.route('/delete_recipe/<int:id>', methods=['POST'])
def delete_recipe(id):
    try:
        # 削除対象のレシピを取得。見つからなければ404エラー
        recipe_to_delete = db.session.get(SavedRecipe, id)
        if recipe_to_delete:
            db.session.delete(recipe_to_delete)
            db.session.commit()
            flash('レシピを削除しました。')
    except Exception as e:
        db.session.rollback()
        print(f"削除失敗：{e}")
        flash('レシピの削除に失敗しました。')
    return redirect(url_for('saved_recipes'))


@app.route('/fridge', methods=['GET', 'POST'])
def fridge():
    if request.method == 'POST':
        try:
            # フォームから新しい食材アイテムを作成
            new_item = FridgeItem(
                name=request.form['name'],
                expiration_date=datetime.strptime(request.form['expiration_date'], '%Y-%m-%d').date(),
                expiration_type=request.form['expiration_type'],
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(new_item)
            db.session.commit()
            flash('食材を追加しました。')
        except Exception as e:
            db.session.rollback()
            print(f"食材の追加に失敗: {e}")
            flash('食材の追加に失敗しました。')
        return redirect(url_for('fridge'))

    # GETリクエストの場合、全食材をリスト表示
    try:
        all_items = FridgeItem.query.order_by(FridgeItem.expiration_date).all()
        today = datetime.today().date()
        for item in all_items:
            item.days_left = (item.expiration_date - today).days
        return render_template('fridge.html', items=all_items)
    except Exception as e:
        print(f"食材リストの取得失敗: {e}")
        flash("食材リストの取得に失敗しました。")
        return render_template('fridge.html', items=[])


@app.route("/delete_item/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    try:
        item_to_delete = db.session.get(FridgeItem, item_id)
        if item_to_delete:
            db.session.delete(item_to_delete)
            db.session.commit()
            flash('食材を削除しました。')
    except Exception as e:
        db.session.rollback()
        print(f"食材の削除に失敗: {e}")
        flash('食材の削除に失敗しました。')
    return redirect(url_for('fridge'))


@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = db.session.get(FridgeItem, item_id)
    if not item:
        return "該当データが見つかりませんでした", 404

    if request.method == 'POST':
        try:
            item.name = request.form['name']
            item.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
            item.expiration_date = datetime.strptime(request.form['expiration_date'], '%Y-%m-%d').date()
            item.expiration_type = request.form['expiration_type']
            db.session.commit()
            flash('食材の情報を更新しました。')
            return redirect(url_for('fridge'))
        except Exception as e:
            db.session.rollback()
            print(f"食材の更新に失敗: {e}")
            flash('食材の更新に失敗しました。')
    
    return render_template('edit_item.html', item=item)


@app.route('/choose_action')
def choose_action():
    filename = request.args.get('filename')
    image_path = url_for('static', filename=f'image/{filename}')
    return render_template('choose_action.html', filename=filename, image_path=image_path)


@app.route('/generate_recipes_from_image', methods=['POST'])
def generate_recipes_from_image():
    filename = request.form['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    uploaded_file = genai.upload_file(path=filepath, display_name="fridge_image")
    ingredients = recognize_ingredients(uploaded_file)
    recipes = suggest_recipes(ingredients)

    nutrition_info = parse_nutrition_data(recipes)
    graphs = {name: plot_nutrition_pie(nut) for name, nut in nutrition_info.items()}
    ingredients_part, method_part = split_recipe_parts(recipes)

    return render_template('result.html',
                           image_path=url_for('static', filename=f'image/{filename}'),
                           ingredients=ingredients,
                           ingredients_part=ingredients_part,
                           method_part=method_part,
                           graphs=graphs)


STORAGE_DAYS = {
    "にんじん": 14, "じゃがいも": 30, "ピーマン": 7, "キャベツ": 10,
    "レタス": 5, "きゅうり": 5, "トマト": 7, "玉ねぎ": 30,
}

@app.cli.command("init-db")
def init_db_command():
    """データベースを初期化し、初期データを投入します。"""
    db.create_all()
    for name, days in STORAGE_DAYS.items():
        existing_item = StorageDay.query.get(name)
        if not existing_item:
            db.session.add(StorageDay(name=name, days=days))
    db.session.commit()
    print("データベースを初期化しました。")


@app.route('/get_storage_days', methods=['GET'])
def get_storage_days():
    try:
        items = StorageDay.query.all()
        return jsonify({item.name: item.days for item in items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update_storage_day', methods=['POST'])
def update_storage_day():
    data = request.get_json()
    name = data.get("name")
    days = data.get("days")
    if not name or not isinstance(days, int):
        return jsonify({"error": "Invalid data"}), 400

    try:
        item = StorageDay.query.get(name)
        if item:
            item.days = days
        else:
            item = StorageDay(name=name, days=days)
            db.session.add(item)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/save_recipe', methods=['POST'])
def save_recipe():
    from models import SavedRecipe, db  # 既に上でimportしているなら不要

    title = request.form.get('title') or '提案レシピ'
    ingredients = request.form.get('ingredients') or ''
    method = request.form.get('method') or ''
    ingredients_part = request.form.get('ingredients_part') or ''
    method_part = request.form.get('method_part') or ''

    if not ingredients and not method:
        flash('保存できるレシピ内容がありません。')
        return redirect(url_for('saved_recipes'))

    try:
        rec = SavedRecipe(
            title=title,
            ingredients=ingredients,
            method=method,
            ingredients_part=ingredients_part,
            method_part=method_part,
        )
        db.session.add(rec)
        db.session.commit()
        flash('レシピを保存しました。')
    except Exception as e:
        db.session.rollback()
        app.logger.exception(e)
        flash('レシピの保存に失敗しました。')

    return redirect(url_for('saved_recipes'))

if __name__ == '__main__':
    app.run(debug=True)