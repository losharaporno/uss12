import os
import re
import secrets
import string
import pymysql
import logging
import sys
from datetime import datetime, timedelta
from flask import Flask, request, redirect, session, render_template_string, flash, get_flashed_messages, abort
from flask_wtf.csrf import CSRFProtect
from markupsafe import escape
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=1024 * 1024)
CSRFProtect(app)
if os.environ.get('TRUST_PROXY') == '1':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']
DB_NAME = os.environ['DB_NAME']

def get_conn():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, connect_timeout=10, read_timeout=15, write_timeout=15)
POSITIONS = ['Власник', 'Генеральний директор', "Власник ігрових об'єктів", "Співвласник ігрових об'єктів", "Керівник ігрових об'єктів", 'Юрист', 'Головний бухгалтер', 'Бухгалтер', 'Керуючий відділу технічного спрямування', 'Куратор відділу', 'Технічний спеціаліст']
DEPARTMENTS = ['B1', 'J2', 'G3', 'H4', 'Y5', 'Q6', 'M7']
BENEFITS = ['УБД', 'НДСО', 'СР1', 'СР2', 'ВД', 'І1', 'І2', 'І3', 'ЦД1', 'ЦД2', 'ЦД3']
POSITION_RANKS = {'Власник': 11, 'Генеральний директор': 10, "Власник ігрових об'єктів": 9, "Співвласник ігрових об'єктів": 8, "Керівник ігрових об'єктів": 7, 'Юрист': 6, 'Головний бухгалтер': 5, 'Бухгалтер': 4, 'Керуючий відділу технічного спрямування': 3, 'Куратор відділу': 2, 'Технічний спеціаліст': 1}

def get_user_rank(user):
    if not user or not user.get('positions'):
        return 0
    ranks = [POSITION_RANKS.get(p, 0) for p in user['positions'].split(',')]
    return max(ranks) if ranks else 0

def generate_password():
    return ''.join((secrets.choice(string.ascii_letters + string.digits) for _ in range(14)))
CSS = "\n<style>\n  * { box-sizing: border-box; font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; }\n  body { background: #0F0F1E; color: #fff; margin: 0; padding: 20px; display: flex; justify-content: center; }\n  .container { width: 100%; max-width: 500px; }\n  .logo { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; display: block; margin: 0 auto 20px; box-shadow: 0 0 20px rgba(108,99,255,0.5); }\n  .card { background: #1F1F3A; border-radius: 20px; padding: 25px; margin-bottom: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }\n  h1, h2, h3 { text-align: center; margin-top: 0; }\n  label { display: block; color: #A0A0C0; font-size: 13px; margin-bottom: 5px; }\n  input, select, textarea { width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 10px; border: none; background: #2A2A4A; color: #fff; outline: none; resize: vertical; }\n  input:focus, select:focus, textarea:focus { border: 1px solid #6C63FF; }\n  button { width: 100%; padding: 14px; border: none; border-radius: 10px; background: linear-gradient(135deg, #6C63FF, #4A42D6); color: #fff; font-weight: bold; cursor: pointer; font-size: 15px; }\n  button:hover { opacity: 0.9; }\n  .nav { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; justify-content: center; }\n  .nav a { color: #fff; text-decoration: none; padding: 8px 15px; background: #2A2A4A; border-radius: 20px; font-size: 14px; }\n  .nav a:hover { background: #6C63FF; }\n  .error { background: #FF6B6B22; color: #FF6B6B; padding: 10px; border-radius: 10px; margin-bottom: 15px; text-align: center; }\n  .success { background: #4CAF5022; color: #4CAF50; padding: 10px; border-radius: 10px; margin-bottom: 15px; text-align: center; }\n  .user-card { display: flex; align-items: center; gap: 15px; padding: 10px 0; border-bottom: 1px solid #333355; }\n  .avatar { width: 50px; height: 50px; border-radius: 50%; background: #6C63FF; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; }\n  .user-info { flex: 1; }\n  .user-name { font-weight: bold; font-size: 16px; }\n  .user-desc { color: #A0A0C0; font-size: 13px; }\n  .checkbox-group { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-bottom: 15px; }\n  .checkbox-group label { display: flex; align-items: center; gap: 5px; color: #fff; font-size: 12px; margin: 0; }\n  .msg-box { background: #2A2A4A; padding: 15px; border-radius: 10px; margin-bottom: 15px; border-left: 4px solid #6C63FF; }\n  .msg-text { font-size: 15px; margin-bottom: 5px; }\n  .msg-meta { font-size: 12px; color: #A0A0C0; }\n  .badge { background: #FF6B6B; color: #fff; border-radius: 50%; padding: 2px 8px; font-size: 12px; font-weight: bold; margin-left: 5px; }\n\n@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');\n*{font-family:'Manrope',-apple-system,sans-serif}body{background:#080510;background-image:radial-gradient(ellipse 380px 180px at 50% 80px,#32124799,transparent);padding:24px 20px 40px;min-height:100vh}.container{max-width:560px}.brand-mark{margin:18px auto 20px;width:84px;height:84px;border:1px solid #a377ff;border-radius:26px;display:grid;place-items:center;font-size:56px;font-weight:800;color:#e4cdff;background:linear-gradient(140deg,#401b64,#13091e);box-shadow:0 0 55px #8d38e244;transform:rotate(-6deg)}h1{font-size:28px;letter-spacing:5px;margin-bottom:30px}h2,h3{font-weight:800;text-align:left;letter-spacing:-.6px}.card{background:linear-gradient(145deg,#1a1028,#110b1b);border:1px solid #352343;border-radius:18px;padding:24px;box-shadow:none;margin-bottom:22px}.nav{gap:8px;margin-bottom:26px;justify-content:flex-start}.nav a{background:#181021;border:1px solid #362444;color:#c9bdd9;border-radius:10px;padding:11px 13px;font-size:12px}.nav a:hover{background:#39204f}label{color:#b6a6ca;font-size:11px;margin-bottom:8px}input,select,textarea{background:#0e0917;border:1px solid #443052;border-radius:10px;min-height:48px;padding:13px;font-size:14px}input:focus,textarea:focus,select:focus{border:1px solid #a377ff;box-shadow:0 0 0 3px #a377ff18}button{background:#a377ff;color:#160d24;border-radius:10px;min-height:48px;font-size:13px;font-weight:800}.user-card{border-color:#31213f;padding:16px 0}.avatar{background:#342047;color:#d8bdff;flex-shrink:0}.user-name{font-size:14px}.user-desc{color:#ad9dbe;font-size:12px;line-height:1.8;overflow-wrap:anywhere}.checkbox-group{grid-template-columns:1fr;gap:12px}.checkbox-group label{font-size:12px;line-height:1.5}.checkbox-group input{width:18px;height:18px;min-height:18px;margin:0;accent-color:#a377ff}.msg-box{background:#100a1a;border:1px solid #352343;border-left:3px solid #a377ff}.msg-text{white-space:pre-wrap;overflow-wrap:anywhere}.error{color:#f28b9a}.success{color:#62d6a3}.logout-form{margin:0}.logout-form button{width:auto;background:#181021;border:1px solid #362444;color:#c9bdd9;padding:11px 13px;font-size:12px;min-height:0;font-weight:500}footer{text-align:center;color:#7f6b93;font-size:10px;letter-spacing:2px;margin-top:30px}a{color:#c9a9ff}.badge{background:#a377ff;color:#160d24}input[type=hidden]{display:none}\n</style>\n"
BASE_HTML = '<!doctype html><html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="theme-color" content="#080510"><title>UUS — Робочий простір</title>' + CSS + '</head><body>\n<div class="container">\n    <div class="brand-mark" aria-label="UUS">U</div>\n    <h1>UUS</h1>\n    {% if user %}\n    <div class="nav">\n        <a href="/">Головна</a>\n        {% if rank >= 9 %}<a href="/staff">Працівники</a>{% endif %}\n        {% if rank >= 4 %}<a href="/accounting">Бухгалтерія</a>{% endif %}\n        <a href="/benefits">Пільги</a>\n        <a href="/servers">Сервери</a>\n        <a href="/messages">Повідомлення {% if unread_count > 0 %}<span class="badge">{{ unread_count }}</span>{% endif %}</a>\n        {% if rank >= 10 %}<a href="/send_message">Надіслати</a>{% endif %}\n        <a href="/profile">Профіль</a>\n        <form action="/logout" method="post" class="logout-form"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><button type="submit">Вихід</button></form>\n    </div>\n    {% endif %}\n    {% with messages = get_flashed_messages(with_categories=true) %}\n      {% if messages %}\n        {% for category, message in messages %}\n          <div class="{{ category }}">{{ message }}</div>\n        {% endfor %}\n      {% endif %}\n    {% endwith %}\n    {{ content|safe }}\n    <footer>UUS · РОБОЧИЙ ПРОСТІР</footer>\n</div></body></html>\n'

def render_page(content, **kwargs):
    user = None
    rank = 0
    unread_count = 0
    if 'user_id' in session:
        conn = get_conn()
        with conn.cursor() as c:
            c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
            user = c.fetchone()
            if user:
                rank = get_user_rank(user)
                c.execute('SELECT COUNT(*) as cnt FROM messages WHERE is_read=0')
                unread_count = c.fetchone()['cnt']
        conn.close()
    from flask_wtf.csrf import generate_csrf
    token = str(escape(generate_csrf()))
    content = re.sub('(<form\\b[^>]*method="post"[^>]*>)', lambda match: match.group(1) + '<input type="hidden" name="csrf_token" value="' + token + '">', content, flags=re.I)
    return render_template_string(BASE_HTML, user=user, rank=rank, unread_count=unread_count, content=content, **kwargs)

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/profile')
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pw = request.form.get('password', '').strip()
        try:
            conn = get_conn()
            with conn.cursor() as c:
                c.execute('SELECT * FROM users WHERE email=%s', (email,))
                user = c.fetchone()
            conn.close()
            if user and check_password_hash(user['password'], pw):
                session.clear()
                session['user_id'] = user['id']
                return redirect('/profile')
            error = 'Невірна пошта або пароль'
        except Exception as e:
            logger.error(f'Login error: {e}')
            error = 'Сервер тимчасово недоступний. Спробуйте пізніше.'
    content = f"""\n    <div class="card">\n        <h2>Вхід у систему</h2>\n        {(f'<div class="error">{escape(error)}</div>' if error else '')}\n        <form method="post">\n            <label>Електронна пошта</label>\n            <input name="email" type="email" required placeholder="vinto@ukr.uus.net">\n            <label>Пароль</label>\n            <input name="password" type="password" required>\n            <button type="submit">Увійти</button>\n        </form>\n    </div>\n    """
    return render_page(content)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/')

@app.route('/staff', methods=['GET', 'POST'])
def staff():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_conn()
    with conn.cursor() as c:
        c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
        me = c.fetchone()
    rank = get_user_rank(me)
    if rank < 9:
        conn.close()
        return redirect('/')
    if request.method == 'POST':
        fn = request.form.get('first_name')
        ln = request.form.get('last_name')
        em = request.form.get('email')
        pos_list = request.form.getlist('positions')
        dept_list = request.form.getlist('departments')
        positions = ','.join(pos_list) if pos_list else ''
        departments = ','.join(dept_list) if dept_list else None
        new_password = generate_password()
        try:
            with conn.cursor() as c:
                c.execute('INSERT INTO users (first_name, last_name, email, password, positions, departments) VALUES (%s, %s, %s, %s, %s, %s)', (fn, ln, em, generate_password_hash(new_password), positions, departments))
            conn.commit()
            flash(f'Працівника додано! Пароль: {new_password}', 'success')
        except pymysql.err.IntegrityError:
            flash('Помилка: Ця електронна пошта вже зайнята!', 'error')
        except Exception as e:
            logger.error(f'Staff error: {e}')
            flash('Не вдалося виконати дію. Перевірте дані або зверніться до адміністратора.', 'error')
    search = request.args.get('search', '')
    with conn.cursor() as c:
        if search:
            c.execute('SELECT * FROM users WHERE last_name LIKE %s ORDER BY last_name', (f'%{search}%',))
        else:
            c.execute('SELECT * FROM users ORDER BY last_name')
        users = c.fetchall()
    conn.close()
    pos_options = ''.join([f'<label><input type="checkbox" name="positions" value="{escape(p)}"> {escape(p)}</label>' for p in POSITIONS])
    dept_options = ''.join([f'<label><input type="checkbox" name="departments" value="{escape(d)}"> {escape(d)}</label>' for d in DEPARTMENTS])
    user_list = ''
    for u in users:
        dept_text = u['departments'].replace(',', ', ') if u['departments'] else 'Відсутній'
        user_list += f"""\n        <div class="user-card">\n            <div class="avatar">{escape(u['first_name'][0])}{escape(u['last_name'][0])}</div>\n            <div class="user-info">\n                <div class="user-name">{escape(u['first_name'])} {escape(u['last_name'])}</div>\n                <div class="user-desc">{escape(u['email'])}</div>\n                <div class="user-desc">{escape(u['positions'])}</div>\n                <div class="user-desc">Відділ: {escape(dept_text)}</div>\n            </div>\n        </div>\n        """
    content = f'''\n    <div class="card">\n        <h3>Додати працівника</h3>\n        <form method="post">\n            <label>Ім'я</label><input name="first_name" required>\n            <label>Прізвище</label><input name="last_name" required>\n            <label>Електронна пошта</label><input name="email" type="email" required>\n            <label>Посади (можна декілька)</label>\n            <div class="checkbox-group">{pos_options}</div>\n            <label>Відділи (не обов'язково)</label>\n            <div class="checkbox-group">{dept_options}</div>\n            <button type="submit">Додати</button>\n        </form>\n    </div>\n    <div class="card">\n        <h3>Список працівників</h3>\n        <form method="get" style="display:flex; gap:10px; margin-bottom:15px;">\n            <input name="search" placeholder="Пошук за прізвищем" value="{escape(search)}" style="margin:0;">\n            <button type="submit" style="width:100px; margin:0;">Знайти</button>\n        </form>\n        {user_list}\n    </div>\n    '''
    return render_page(content)

@app.route('/accounting', methods=['GET', 'POST'])
def accounting():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_conn()
    with conn.cursor() as c:
        c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
        me = c.fetchone()
    rank = get_user_rank(me)
    if rank < 4:
        conn.close()
        return redirect('/')
    if request.method == 'POST':
        month = request.form.get('month')
        year = request.form.get('year')
        expenses = request.form.get('expenses')
        try:
            with conn.cursor() as c:
                c.execute('INSERT INTO statements (month, year, expenses, created_by) VALUES (%s, %s, %s, %s)', (month, year, expenses, me['id']))
            conn.commit()
            flash('Виписку створено!', 'success')
        except Exception as e:
            logger.error(f'Accounting error: {e}')
            flash('Не вдалося виконати дію. Перевірте дані або зверніться до адміністратора.', 'error')
    with conn.cursor() as c:
        c.execute('SELECT s.*, u.first_name, u.last_name FROM statements s JOIN users u ON s.created_by = u.id ORDER BY s.created_at DESC')
        statements = c.fetchall()
    conn.close()
    stmt_html = ''
    for s in statements:
        can_edit = (s['created_by'] == me['id'] or rank >= 9) and datetime.now() - s['created_at'] < timedelta(days=7)
        edit_btn = f"""<a href="/edit_statement/{escape(s['id'])}"><button style="width:100px; padding:5px; margin-top:10px;">Редагувати</button></a>""" if can_edit else ''
        stmt_html += f"""\n        <div class="user-card" style="flex-direction:column; align-items:flex-start;">\n            <div style="font-weight:bold;">{escape(s['month'])}.{escape(s['year'])}</div>\n            <div style="font-size:12px; color:#A0A0C0;">Автор: {escape(s['first_name'])} {escape(s['last_name'])}</div>\n            <div style="margin-top:5px;">Витрати: {escape(s['expenses'])}</div>\n            {edit_btn}\n        </div>\n        """
    content = f'\n    <div class="card">\n        <h3>Створити виписку</h3>\n        <form method="post">\n            <label>Місяць</label><input name="month" type="number" min="1" max="12" required>\n            <label>Рік</label><input name="year" type="number" value="2026" required>\n            <label>Витрати</label><input name="expenses" required>\n            <button type="submit">Створити</button>\n        </form>\n    </div>\n    <div class="card">\n        <h3>Виписки</h3>\n        {stmt_html}\n    </div>\n    '
    return render_page(content)

@app.route('/benefits', methods=['GET', 'POST'])
def benefits():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_conn()
    with conn.cursor() as c:
        c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
        me = c.fetchone()
    rank = get_user_rank(me)
    if request.method == 'POST' and rank >= 9:
        user_id = request.form.get('user_id')
        benefit = request.form.get('benefit')
        try:
            with conn.cursor() as c:
                c.execute('INSERT INTO benefits (user_id, benefit_name) VALUES (%s, %s)', (user_id, benefit))
            conn.commit()
            flash('Пільгу додано!', 'success')
        except Exception as e:
            logger.error(f'Benefits error: {e}')
            flash('Не вдалося виконати дію. Перевірте дані або зверніться до адміністратора.', 'error')
    search = request.args.get('search', '')
    with conn.cursor() as c:
        if search:
            c.execute('SELECT * FROM users WHERE last_name LIKE %s ORDER BY last_name', (f'%{search}%',))
        else:
            c.execute('SELECT * FROM users ORDER BY last_name')
        users = c.fetchall()
        c.execute('SELECT b.*, u.first_name, u.last_name FROM benefits b JOIN users u ON b.user_id = u.id')
        all_benefits = c.fetchall()
    conn.close()
    ben_dict = {}
    for b in all_benefits:
        if b['user_id'] not in ben_dict:
            ben_dict[b['user_id']] = []
        ben_dict[b['user_id']].append(b['benefit_name'])
    user_list = ''
    for u in users:
        u_benefits = ', '.join(ben_dict.get(u['id'], [])) or 'Немає'
        user_list += f"""\n        <div class="user-card">\n            <div class="user-info">\n                <div class="user-name">{escape(u['first_name'])} {escape(u['last_name'])}</div>\n                <div class="user-desc">Пільги: {escape(u_benefits)}</div>\n            </div>\n        </div>\n        """
    form_html = ''
    if rank >= 9:
        options = ''.join([f'''<option value="{escape(u['id'])}">{escape(u['last_name'])} {escape(u['first_name'])}</option>''' for u in users])
        ben_options = ''.join([f'<option value="{escape(b)}">{escape(b)}</option>' for b in BENEFITS])
        form_html = f'\n        <div class="card">\n            <h3>Додати пільгу</h3>\n            <form method="post">\n                <label>Працівник</label><select name="user_id">{options}</select>\n                <label>Пільга</label><select name="benefit">{ben_options}</select>\n                <button type="submit">Додати</button>\n            </form>\n        </div>\n        '
    content = f'\n    {form_html}\n    <div class="card">\n        <h3>Пільговики</h3>\n        <form method="get" style="display:flex; gap:10px; margin-bottom:15px;">\n            <input name="search" placeholder="Пошук за прізвищем" value="{escape(search)}" style="margin:0;">\n            <button type="submit" style="width:100px; margin:0;">Знайти</button>\n        </form>\n        {user_list}\n    </div>\n    '
    return render_page(content)

@app.route('/servers', methods=['GET', 'POST'])
def servers():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_conn()
    with conn.cursor() as c:
        c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
        me = c.fetchone()
    rank = get_user_rank(me)
    if request.method == 'POST' and rank not in [4, 5, 6, 7, 8]:
        server_id = request.form.get('server_id')
        new_status = request.form.get('status')
        try:
            with conn.cursor() as c:
                c.execute('UPDATE servers SET is_online=%s WHERE id=%s', (new_status, server_id))
            conn.commit()
            flash('Статус сервера змінено!', 'success')
        except Exception as e:
            logger.error(f'Servers error: {e}')
            flash('Не вдалося виконати дію. Перевірте дані або зверніться до адміністратора.', 'error')
    with conn.cursor() as c:
        c.execute('SELECT * FROM servers')
        srvs = c.fetchall()
    conn.close()
    srv_html = ''
    for s in srvs:
        status_text = '🟢 Онлайн' if s['is_online'] else '🔴 Офлайн'
        btn = ''
        if rank not in [4, 5, 6, 7, 8]:
            btn_text = 'Вимкнути' if s['is_online'] else 'Ввімкнути'
            new_st = 0 if s['is_online'] else 1
            btn = f'''\n            <form method="post" style="display:inline;">\n                <input type="hidden" name="server_id" value="{escape(s['id'])}">\n                <input type="hidden" name="status" value="{escape(new_st)}">\n                <button type="submit" style="width:100px; padding:5px;">{escape(btn_text)}</button>\n            </form>\n            '''
        srv_html += f"""\n        <div class="user-card" style="justify-content:space-between;">\n            <div>\n                <div class="user-name">{escape(s['name'])}</div>\n                <div class="user-desc">{escape(status_text)}</div>\n            </div>\n            {btn}\n        </div>\n        """
    content = f'\n    <div class="card">\n        <h3>Сервери</h3>\n        {srv_html}\n    </div>\n    '
    return render_page(content)

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_conn()
    with conn.cursor() as c:
        c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
        me = c.fetchone()
    rank = get_user_rank(me)
    with conn.cursor() as c:
        c.execute('SELECT m.*, u.first_name, u.last_name FROM messages m JOIN users u ON m.sender_id = u.id ORDER BY m.created_at DESC')
        msgs = c.fetchall()
        c.execute('UPDATE messages SET is_read=1')
    conn.commit()
    conn.close()
    msg_html = ''
    for m in msgs:
        dt = m['created_at'].strftime('%d.%m.%Y %H:%M')
        msg_html += f"""\n        <div class="msg-box">\n            <div class="msg-text">{escape(m['message'])}</div>\n            <div class="msg-meta">Від: {escape(m['first_name'])} {escape(m['last_name'])} | {escape(dt)}</div>\n        </div>\n        """
    content = f"""\n    <div class="card">\n        <h3>Повідомлення</h3>\n        {(msg_html if msg_html else '<p style="text-align:center; color:#A0A0C0;">Немає повідомлень</p>')}\n    </div>\n    """
    return render_page(content)

@app.route('/send_message', methods=['GET', 'POST'])
def send_message():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_conn()
    with conn.cursor() as c:
        c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
        me = c.fetchone()
    rank = get_user_rank(me)
    if rank < 10:
        conn.close()
        return redirect('/')
    if request.method == 'POST':
        text = request.form.get('message', '').strip()
        if text:
            try:
                with conn.cursor() as c:
                    c.execute('INSERT INTO messages (sender_id, message) VALUES (%s, %s)', (me['id'], text))
                conn.commit()
                flash('Повідомлення надіслано!', 'success')
            except Exception as e:
                logger.error(f'Send message error: {e}')
                flash('Не вдалося виконати дію. Перевірте дані або зверніться до адміністратора.', 'error')
    conn.close()
    content = f'\n    <div class="card">\n        <h3>Надіслати повідомлення</h3>\n        <form method="post">\n            <label>Текст повідомлення</label>\n            <textarea name="message" rows="5" required placeholder="Введіть текст..."></textarea>\n            <button type="submit">Надіслати всім</button>\n        </form>\n    </div>\n    '
    return render_page(content)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_conn()
    if request.method == 'POST':
        phone = request.form.get('phone')
        avatar = request.form.get('avatar_url')
        try:
            with conn.cursor() as c:
                c.execute('UPDATE users SET phone=%s, avatar_url=%s WHERE id=%s', (phone, avatar, session['user_id']))
            conn.commit()
            flash('Профіль оновлено!', 'success')
        except Exception as e:
            logger.error(f'Profile error: {e}')
            flash('Не вдалося виконати дію. Перевірте дані або зверніться до адміністратора.', 'error')
    with conn.cursor() as c:
        c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
        me = c.fetchone()
    conn.close()
    avatar_img = f'''<img src="{escape(me['avatar_url'])}" style="width:80px; height:80px; border-radius:50%; object-fit:cover; margin:0 auto 15px; display:block;">''' if me['avatar_url'] else f"""<div class="avatar" style="width:80px; height:80px; font-size:30px; margin:0 auto 15px;">{escape(me['first_name'][0])}{escape(me['last_name'][0])}</div>"""
    content = f'''\n    <div class="card">\n        {avatar_img}\n        <h2 style="text-align:center;">{escape(me['first_name'])} {escape(me['last_name'])}</h2>\n        <p style="text-align:center; color:#A0A0C0;">Email: {escape(me['email'])}</p>\n        <p style="text-align:center; color:#A0A0C0;">{escape(me['positions'])}</p>\n        <p style="text-align:center; color:#A0A0C0;">Відділи: {escape(me['departments'] or 'Відсутній')}</p>\n        \n        <form method="post" style="margin-top:20px;">\n            <label>Аватарка (URL)</label>\n            <input name="avatar_url" value="{escape(me['avatar_url'] or '')}" placeholder="https://...">\n            <label>Номер телефону</label>\n            <input name="phone" value="{escape(me['phone'] or '')}" placeholder="+380...">\n            <button type="submit">Зберегти</button>\n        </form>\n    </div>\n    '''
    return render_page(content)

@app.route('/edit_statement/<int:statement_id>', methods=['GET', 'POST'])
def edit_statement(statement_id):
    if 'user_id' not in session:
        return redirect('/')
    conn = get_conn()
    try:
        with conn.cursor() as c:
            c.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
            me = c.fetchone()
            c.execute('SELECT * FROM statements WHERE id=%s', (statement_id,))
            stmt = c.fetchone()
        if not stmt:
            abort(404)
        rank = get_user_rank(me)
        if rank < 4 or not (stmt['created_by'] == me['id'] or rank >= 9) or datetime.now() - stmt['created_at'] >= timedelta(days=7):
            abort(403)
        if request.method == 'POST':
            month = request.form.get('month', type=int)
            year = request.form.get('year', type=int)
            expenses = request.form.get('expenses', '').strip()
            if not month or not 1 <= month <= 12 or not year or not 2000 <= year <= 2200 or not expenses:
                abort(400)
            with conn.cursor() as c:
                c.execute('UPDATE statements SET month=%s, year=%s, expenses=%s WHERE id=%s', (month, year, expenses, statement_id))
            conn.commit()
            flash('Виписку оновлено!', 'success')
            return redirect('/accounting')
        content = f"""<div class="card"><h2>Редагувати виписку</h2><form method="post"><label>Місяць</label><input name="month" type="number" min="1" max="12" required value="{stmt['month']}"><label>Рік</label><input name="year" type="number" min="2000" max="2200" required value="{stmt['year']}"><label>Витрати</label><input name="expenses" required value="{escape(stmt['expenses'])}"><button>Зберегти</button></form></div>"""
        return render_page(content)
    finally:
        conn.close()

@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' https: data:; script-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    response.headers['Cache-Control'] = 'no-store'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
