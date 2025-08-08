from flask import Flask, render_template, request, url_for, redirect,flash,jsonify
import os
from PIL import Image
import io
import base64
import json
from datetime import datetime
import google.generativeai as genai
from model import recognize_ingredients, suggest_recipes, parse_nutrition_data, plot_nutrition_pie
from flask import g 
import psycopg2
from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'static/image'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.getenv("SECRET_KEY")

def get_db():
    if 'conn' not in g:
        g.conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
    return g.conn

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

@app.teardown_appcontext
def close_connection(exception):
    conn = g.pop('conn', None)
    if conn is not None:
        conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['upload_file']
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # アップロードしたファイル名を次の画面へ引き継ぐ
        return redirect(url_for('choose_action', filename=filename))

    return render_template('index.html')


    
    if request.method == "POST":
        値1 = request.form["フォームの名前1"]
        値2 = request.form["フォームの名前2"]

        # 処理

        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("INSERT INTO 作成したテーブル名 (カラム1, カラム2) VALUES (%s, %s)", (値1, 値2))
                conn.commit()
        except Exception as e:
            conn.rollback()
            flash("データの保存に失敗しました。")

        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM 作成したテーブル名 ORDER BY created_at DESC")
                rows = cur.fetchall()
            if not rows:
                flash("データが存在しません。")
        except Exception as e:
            flash("データの取得に失敗しました。")


@app.route('/generate_recipes', methods=['POST'])
def generate_recipes():
    edited_ingredients = request.form['edited_ingredients']
    recipes = suggest_recipes(edited_ingredients)

    nutrition_info = parse_nutrition_data(recipes)
    graphs = {}
    for recipe_name, nutrition in nutrition_info.items():
        img_data = plot_nutrition_pie(nutrition)
        graphs[recipe_name] = img_data

    formatted_recipes = recipes.replace('\n', '<br>')
    ingredients_part, method_part = split_recipe_parts(formatted_recipes)

    return render_template('result.html',
                           image_path=None,
                           ingredients=edited_ingredients,
                           ingredients_part=ingredients_part,
                           method_part=method_part,
                           graphs=graphs)



@app.route('/saved_recipes', methods=['POST','GET'])
def saved_recipes():
    if request.method == 'POST':
        title = request.form['title']
        ingredients = request.form['ingredients']
        method = request.form['method']
        ingredients_part = request.form['ingredients_part']
        method_part = request.form['method_part']

        try:
            conn = get_db()
            with conn.cursor() as cur:
                # 🔴 変更点1: SELECT文に 'id' を追加する
                # ------------------------------------------------------------------------------------------------
                cur.execute("SELECT id, title, ingredients, method, ingredients_part, method_part FROM saved_recipes ORDER BY id DESC")
                # ------------------------------------------------------------------------------------------------
                
                raw_saved_list = cur.fetchall() # 元のタプルのリストを取得

                # 🔴 変更点2: 辞書のリストに変換する
                # 各タプルを、キー（カラム名）でアクセスできる辞書に変換します
                saved_list = []
                for item_tuple in raw_saved_list:
                    saved_list.append({
                        'id': item_tuple[0],             # id
                        'title': item_tuple[1],          # title
                        'ingredients': item_tuple[2],    # ingredients (完全なレシピテキスト)
                        'method': item_tuple[3],         # method (完全なレシピテキスト)
                        'ingredients_part': item_tuple[4], # ingredients_part (材料部分)
                        'method_part': item_tuple[5]       # method_part (作り方部分)
                    })

            # 🔴 変更点3: テンプレートに渡す変数名を 'recipes' に合わせる
            # テンプレートで {% for r in recipes %} となっているので、ここで 'recipes' として渡します
            return render_template('saved_recipes.html', recipes=saved_list)
        except Exception as e:
            print(f"レシピ一覧の取得失敗: {e}")
            flash("保存されたレシピの読み込みに失敗しました。")
            return "レシピ一覧の表示エラー", 500
    else:
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, ingredients, method, ingredients_part, method_part FROM saved_recipes ORDER BY id DESC")
                rows = cur.fetchall()
                recipes = [
                    {
                        'id': row[0],
                        'title': row[1],
                        'ingredients': row[2],
                        'method': row[3],
                        'ingredients_part': row[4],
                        'method_part': row[5]
                    }
                    for row in rows
                ]
            return render_template('saved_recipes.html', recipes=recipes)
        except Exception as e:
            print(f"レシピ一覧の取得失敗: {e}")
            flash("保存されたレシピの読み込みに失敗しました。")
            return "レシピ一覧の表示エラー", 500



@app.route('/delete_recipe/<int:id>', methods=['POST'])
def delete_recipe(id):
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM saved_recipes WHERE id = %s", (id,))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print("削除失敗：", e)

    return redirect(url_for('saved_recipes'))



@app.route('/fridge', methods=['GET', 'POST'])
def fridge():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='fridge_items'")
    print(cursor.fetchall())

    if request.method == 'POST':
        name = request.form['name']
        purchase_date=datetime.now().date()
        expiration_date = request.form['expiration_date']
        expiration_type = request.form['expiration_type']

        cursor.execute("""
            INSERT INTO fridge_items (name, purchase_date, expiration_date, expiration_type)
            VALUES (%s, %s, %s,%s)
        """, (name, purchase_date,expiration_date, expiration_type))
        conn.commit()

    cursor.execute("SELECT * FROM fridge_items ORDER BY expiration_date")
    raw_items = cursor.fetchall()
    items = []
    for item in raw_items:
        days_left = (item[2] - datetime.today().date()).days
        items.append({
            'id': item[0],
            'name': item[1],
            'purchase_date': item[2],
            'expiration_date': item[3],
            'expiration_type': item[4],
            'days_left': (item[3] - datetime.today().date()).days
        })

    items.sort(key=lambda x: x["days_left"])
    cursor.close()
    return render_template('fridge.html', items=items)


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fridge_items WHERE id = %s", (item_id,))
    conn.commit()
    cursor.close()
    return redirect(url_for('fridge'))

@app.route('/edit/<int:item_id>', methods=['GET'])
def edit_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fridge_items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()

    if item:
        item_data = {
            'id': item[0],
            'name': item[1],
            'purchase_date': item[2],
            'expiration_date': item[3],
            'expiration_type': item[4],
        }
        return render_template('edit_item.html', item=item_data)
    else:
        return "該当データが見つかりませんでした", 404

@app.route('/edit/<int:item_id>', methods=['POST'])
def update_item(item_id):
    name = request.form['name']
    purchase_date = request.form['purchase_date']
    expiration_date = request.form['expiration_date']
    expiration_type = request.form['expiration_type']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE fridge_items 
        SET name = %s, purchase_date = %s, expiration_date = %s, expiration_type = %s 
        WHERE id = %s
    """, (name, purchase_date, expiration_date, expiration_type, item_id))
    conn.commit()
    cursor.close()
    return redirect(url_for('fridge'))  # fridgeが一覧ページの関数名である前提


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
    graphs = {}
    for recipe_name, nutrition in nutrition_info.items():
        img_data = plot_nutrition_pie(nutrition)
        graphs[recipe_name] = img_data

    ingredients_part, method_part = split_recipe_parts(recipes)

    return render_template('result.html',
                           image_path=url_for('static', filename=f'image/{filename}'),
                           ingredients=ingredients,
                           ingredients_part=ingredients_part,
                           method_part=method_part,
                           graphs=graphs)

@app.route('/fridge', methods=['POST'])
def fridge_page():
    filename = request.form['filename']  # 現在は使用していないが、将来使う可能性あり

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT name, expiration_type, expiration_date FROM fridge_items ORDER BY expiration_date ASC")
        items = cur.fetchall()

    return render_template('fridge.html', items=items)

@app.route('/check_expiration', methods=['POST'])
def check_expiration():
    filename = request.form['filename']
    return redirect(url_for('fridge_page'))

# 保存日数の目安データ（仮の例です）
STORAGE_DAYS = {
    "にんじん": 14,
    "じゃがいも": 30,
    "ピーマン": 7,
    "キャベツ": 10,
    "レタス": 5,
    "きゅうり": 5,
    "トマト": 7,
    "玉ねぎ": 30,
    # どんどん追加できます
}
def initialize_storage_days():
    conn = get_db()
    cur = conn.cursor()
    for name, days in STORAGE_DAYS.items():
        # 既に存在しているか確認
        cur.execute("SELECT 1 FROM storage_days WHERE name = %s", (name,))
        if not cur.fetchone():
            cur.execute("INSERT INTO storage_days (name, days) VALUES (%s, %s)", (name, days))
    conn.commit()
    cur.close()

@app.route('/get_storage_days', methods=['GET'])
def get_storage_days():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, days FROM storage_days")
    rows = cur.fetchall()
    cur.close()
    return jsonify({name: days for name, days in rows})

@app.route('/update_storage_day', methods=['POST'])
def update_storage_day():
    data = request.get_json()
    name = data.get("name")
    days = data.get("days")
    if not name or not isinstance(days, int):
        return jsonify({"error": "Invalid data"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO storage_days (name, days)
        VALUES (%s, %s)
        ON CONFLICT (name) DO UPDATE SET days = EXCLUDED.days
    """, (name, days))
    conn.commit()
    cur.close()
    return jsonify({"success": True})



if __name__ == '__main__':
    app.run(debug=True)


