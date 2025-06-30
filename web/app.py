from flask import Flask, render_template, request, redirect, url_for
import json, os

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


def load_keywords() -> list[str]:
    return load_json_list(KEYWORDS_PATH, 'keywords')


def save_keywords(keywords: list[str]):
    save_json_list(KEYWORDS_PATH, 'keywords', keywords)


def load_ad_keywords() -> list[str]:
    return load_json_list(AD_KEYWORDS_PATH, 'keywords')


def save_ad_keywords(ad_keywords: list[str]):
    save_json_list(AD_KEYWORDS_PATH, 'keywords', ad_keywords)


app = Flask(__name__)

@app.route('/')
def index():
    kws = load_keywords()
    ad_kws = load_ad_keywords()
    return render_template('index.html', keywords=kws, ad_keywords=ad_kws)


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


@app.route('/delete/<kind>/<int:idx>')
def delete_keyword(kind: str, idx: int):
    if kind == 'ad':
        lst = load_ad_keywords()
        save = save_ad_keywords
    else:
        lst = load_keywords()
        save = save_keywords

    if 0 <= idx < len(lst):
        lst.pop(idx)
        save(lst)
    return redirect(url_for('index'))


@app.route('/edit/<kind>/<int:idx>', methods=['GET', 'POST'])
def edit_keyword(kind: str, idx: int):
    if kind == 'ad':
        lst = load_ad_keywords()
        save = save_ad_keywords
    else:
        lst = load_keywords()
        save = save_keywords

    if request.method == 'POST':
        new_kw = request.form.get('keyword', '').strip()
        if new_kw and 0 <= idx < len(lst):
            lst[idx] = new_kw
            save(lst)
        return redirect(url_for('index'))

    if 0 <= idx < len(lst):
        return render_template('edit.html', index=idx, keyword=lst[idx], kind=kind)
    return redirect(url_for('index'))
