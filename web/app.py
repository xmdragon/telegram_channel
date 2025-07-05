from flask import Flask, request, redirect, url_for, render_template, flash, jsonify, render_template_string
import json,os
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 如果要用 flash 必须有

DB_FILE = "../sender/database.db"

# 配置两个 JSON 文件路径
KEYWORDS_PATH = '../keywords.json'
AD_KEYWORDS_PATH = '../ad_keywords.json'


def load_json_list(path: str, key: str) -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get(key, [])


def save_json_list(path: str, key: str, items: list[str]):
    data = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data[key] = items
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =============== 你的 keyword 编辑 ===================
def load_keywords() -> list[str]:
    return load_json_list(KEYWORDS_PATH, 'keywords')


def save_keywords(keywords: list[str]):
    save_json_list(KEYWORDS_PATH, 'keywords', keywords)


def load_ad_keywords() -> list[str]:
    return load_json_list(AD_KEYWORDS_PATH, 'keywords')


def save_ad_keywords(ad_keywords: list[str]):
    save_json_list(AD_KEYWORDS_PATH, 'keywords', ad_keywords)

def get_loader_and_saver(kind):
    if kind == 'ad':
        return load_ad_keywords, save_ad_keywords
    else:
        return load_keywords, save_keywords


@app.route('/add', methods=['POST'])
def add_keyword():
    kind = request.form.get('kind', 'normal')
    kw = request.form.get('keyword', '').strip()
    if kw:
        if kind == 'ad':
            lst = load_ad_keywords()
            if kw not in lst:
                lst.append(kw)
                save_ad_keywords(lst)
        else:
            lst = load_keywords()
            if kw not in lst:
                lst.append(kw)
                save_keywords(lst)
    return redirect(url_for('index'))

@app.route('/edit/<kind>/<int:idx>', methods=['GET', 'POST'])
def edit_keyword(kind: str, idx: int):
    load, save = get_loader_and_saver(kind)
    lst = load()

    if request.method == 'POST':
        new_kw = request.form.get('keyword', '').strip()
        if new_kw and 0 <= idx < len(lst):
            old_kw = lst[idx]
            lst[idx] = new_kw
            save(lst)
            flash(f"已将 {kind} 关键词从 '{old_kw}' 修改为 '{new_kw}'")
        else:
            flash("提交内容无效或索引超出范围。")
        return redirect(url_for('index'))

    if 0 <= idx < len(lst):
        return render_template('edit.html', index=idx, keyword=lst[idx], kind=kind)
    else:
        flash("索引超出范围，无法编辑。")
        return redirect(url_for('index'))
    

@app.route('/delete/<kind>/<int:idx>')
def delete_keyword(kind: str, idx: int):
    load, save = get_loader_and_saver(kind)
    lst = load()
    if 0 <= idx < len(lst):
        removed = lst.pop(idx)
        save(lst)
        flash(f"已删除 {kind} 关键词: {removed}")
    else:
        flash("索引无效，未删除任何关键词。")
    return redirect(url_for('index'))

@app.route('/')
def index():
    kws = load_keywords()
    ad_kws = load_ad_keywords()
    return render_template('index.html', keywords=kws, ad_keywords=ad_kws)

# =============== 集成 inspect_db 功能 ===================

@app.route("/inspect_html")
def inspect_html():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, username, phone, first_name, last_name, last_sent_date, sent_flag
        FROM sent_users ORDER BY sent_flag DESC
    """)
    rows = cur.fetchall()
    conn.close()

    return render_template("inspect.html", users=rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
