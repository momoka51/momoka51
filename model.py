import google.generativeai as genai
import re
import io
import matplotlib.pyplot as plt
import base64
import matplotlib
import matplotlib.pyplot as plt

# matplotlibで日本語が表示できるようフォント設定
matplotlib.rcParams['font.family'] = 'Yu Gothic'  
matplotlib.rcParams['axes.unicode_minus'] = False


# Gemini APIセットアップ
genai.configure(api_key="AIzaSyD7ADx5AXuhYW-WG1_lcAvYaLcsl40s7Eg")
model = genai.GenerativeModel("gemini-1.5-flash")

def recognize_ingredients(input_file):
    """Geminiに画像を送って食材を認識する"""
    response = model.generate_content([input_file, "日本語で写っている食材を詳細に説明してください"])
    return response.text

def suggest_recipes(ingredients):
    """Geminiに食材を渡して栄養バランスを考慮したレシピを生成"""
    prompt = (
        f"以下の食材を使って、栄養バランスを考慮した献立を日本語で提案してください。"
        f"献立は主菜・副菜・汁物など、栄養の偏りを防ぐ組み合わせにしてください。"
        f"各料理は『料理名』→『材料』→『作り方』の順で箇条書きで説明し、"
        f"必ず『栄養バランス：タンパク質xx%、脂質xx%、炭水化物xx%、ビタミン・ミネラルxx%』の形式で各料理ごとに付けてください。"
        f"食材: {ingredients}"
    )
    response = model.generate_content(prompt)
    return response.text

def parse_nutrition_data(recipes_text):
    """Geminiから返ってきたレシピテキストから栄養情報を抽出して辞書化"""
    pattern = r'料理名：(.+?)\s.*?栄養バランス：(.+?)(?:\n|$)'
    matches = re.findall(pattern, recipes_text, re.DOTALL)
    nutrition_dict = {}
    for recipe_name, nutrition_str in matches:
        nutrition_items = re.findall(r'(\S+?)\s*(\d+)%', nutrition_str)
        nutrition_data = {item[0]: int(item[1]) for item in nutrition_items}
        nutrition_dict[recipe_name.strip()] = nutrition_data
    return nutrition_dict

def plot_nutrition_pie(nutrition_data):
    """栄養バランスの円グラフをbase64で返す"""
    labels = list(nutrition_data.keys())
    sizes = list(nutrition_data.values())
    colors = ['#f44336','#ff9800','#4caf50','#03a9f4']
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

if __name__ == "__main__":
    print("model.py単体テスト")
    uploaded_file = genai.upload_file(path="uploaded_fridge_image.png", display_name="test_image")
    result = recognize_ingredients(uploaded_file)
    print(result)


