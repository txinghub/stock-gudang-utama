#!/usr/bin/env python3
"""
Flask API Server for Stock Gudang Utama
Connects to SQLite database in db/stock.db
"""

import sqlite3
import json
import os
from flask import Flask, send_file, request, jsonify
from functools import wraps

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'stock.db')

# ==================== DATABASE HELPERS ====================

def get_db():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    """Convert sqlite3.Row to dict"""
    return dict(row) if row else None

# ==================== CORS WRAPPER ====================

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.after_request
def after_request(response):
    return add_cors_headers(response)

@app.route('/')
def index():
    return send_file('index.html')

# ==================== ITEMS API ====================

@app.route('/api/items', methods=['GET'])
def get_items():
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM item ORDER BY kategori, nama"
    )
    items = [dict_from_row(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(items)

@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    conn = get_db()
    cur = conn.execute("SELECT * FROM item WHERE id = ?", (item_id,))
    item = dict_from_row(cur.fetchone())
    conn.close()
    return jsonify(item) if item else jsonify({'error': 'Not found'}), 404

@app.route('/api/items', methods=['POST'])
def add_item():
    data = request.json
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO item (kategori, nama, satuan, lokasi, stok, min_stok, high_stok, low_stok, supplier, price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('kategori', '').upper(),
        data.get('item', '').upper(),
        data.get('satuan', '').upper(),
        data.get('lokasi', '').upper(),
        data.get('stok', 0),
        data.get('min_stok', 0),
        data.get('high_stok', 0),
        data.get('low_stok', 0),
        data.get('supplier', '').upper(),
        data.get('price', 0)
    ))
    conn.commit()
    item_id = cur.lastrowid
    conn.close()
    return jsonify({'id': item_id}), 201

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data = request.json
    conn = get_db()
    conn.execute("""
        UPDATE item SET
            kategori = ?, nama = ?, satuan = ?, lokasi = ?,
            stok = ?, min_stok = ?, high_stok = ?, low_stok = ?,
            supplier = ?, price = ?
        WHERE id = ?
    """, (
        data.get('kategori', '').upper(),
        data.get('item', '').upper(),
        data.get('satuan', '').upper(),
        data.get('lokasi', '').upper(),
        data.get('stok', 0),
        data.get('min_stok', 0),
        data.get('high_stok', 0),
        data.get('low_stok', 0),
        data.get('supplier', '').upper(),
        data.get('price', 0),
        item_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_db()
    conn.execute("DELETE FROM item WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ==================== SETTINGS API ====================

@app.route('/api/settings', methods=['GET'])
def get_settings():
    conn = get_db()
    cur = conn.execute("SELECT * FROM settings ORDER BY type, value")
    settings = [dict_from_row(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(settings)

@app.route('/api/settings/<setting_type>', methods=['GET'])
def get_settings_by_type(setting_type):
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM settings WHERE type = ? ORDER BY value",
        (setting_type.upper(),)
    )
    settings = [dict_from_row(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def add_setting():
    data = request.json
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO settings (type, value) VALUES (?, ?)",
            (data.get('type', '').upper(), data.get('value', '').upper())
        )
        conn.commit()
        setting_id = cur.lastrowid
        conn.close()
        return jsonify({'id': setting_id}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Duplicate setting'}), 400

@app.route('/api/settings/<int:setting_id>', methods=['PUT'])
def update_setting(setting_id):
    data = request.json
    conn = get_db()
    conn.execute(
        "UPDATE settings SET value = ? WHERE id = ?",
        (data.get('value', '').upper(), setting_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/settings/<int:setting_id>', methods=['DELETE'])
def delete_setting(setting_id):
    conn = get_db()
    conn.execute("DELETE FROM settings WHERE id = ?", (setting_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ==================== MOVEMENTS API ====================

@app.route('/api/movements', methods=['GET'])
def get_movements():
    item_id = request.args.get('item_id')
    conn = get_db()
    if item_id:
        cur = conn.execute(
            "SELECT * FROM movements WHERE item_id = ? ORDER BY tanggal DESC, id DESC",
            (item_id,)
        )
    else:
        cur = conn.execute(
            "SELECT * FROM movements ORDER BY tanggal DESC, id DESC LIMIT 100"
        )
    movements = [dict_from_row(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(movements)

@app.route('/api/movements', methods=['POST'])
def add_movement():
    data = request.json
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO movements (item_id, tanggal, jumlah, type, keterangan, user)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get('item_id'),
        data.get('tanggal', ''),
        data.get('jumlah', 0),
        data.get('type', '').upper(),
        data.get('keterangan', '').upper(),
        data.get('user', 'ADMIN')
    ))
    conn.commit()
    
    # Update item stok
    if data.get('type', '').upper() == 'MASUK':
        conn.execute("UPDATE item SET stok = stok + ? WHERE id = ?",
                      (data.get('jumlah', 0), data.get('item_id')))
    else:
        conn.execute("UPDATE item SET stok = stok - ? WHERE id = ?",
                      (data.get('jumlah', 0), data.get('item_id')))
    conn.commit()
    
    movement_id = cur.lastrowid
    conn.close()
    return jsonify({'id': movement_id}), 201

# ==================== USERS API ====================

@app.route('/api/login', methods=['POST'])
def login():
    print('DEBUG login:', request.data)
    data = request.json
    username = data.get('username', '').upper()
    password = data.get('password', '')
    print('DEBUG username:', repr(username), 'password:', repr(password))
    
    conn = get_db()
    cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = dict_from_row(cur.fetchone())
    conn.close()
    
    print('DEBUG user:', user)
    
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    # Check password (plain text comparison as stored in DB)
    if user.get('password', '') != password:
        return jsonify({'error': 'Wrong password'}), 401
    
    # Get permissions for this role
    conn = get_db()
    cur = conn.execute("SELECT * FROM permissions WHERE role = ?", (user.get('role', ''),))
    perms = {}
    for row in cur.fetchall():
        perms[row['perm']] = bool(row['value'])
    conn.close()
    
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'permissions': perms
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db()
    cur = conn.execute("SELECT id, username, role, created, lastlogin FROM users ORDER BY username")
    users = [dict_from_row(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/users/<username>', methods=['GET'])
def get_user(username):
    conn = get_db()
    cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = dict_from_row(cur.fetchone())
    conn.close()
    return jsonify(user) if user else jsonify({'error': 'Not found'}), 404

@app.route('/api/users', methods=['POST'])
def add_user():
    data = request.json
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (data.get('username', '').upper(), data.get('password', ''), data.get('role', 'user'))
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return jsonify({'id': user_id}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Duplicate username'}), 400

# ==================== PERMISSIONS API ====================

@app.route('/api/permissions/<role>', methods=['GET'])
def get_permissions(role):
    conn = get_db()
    cur = conn.execute("SELECT * FROM permissions WHERE role = ?", (role,))
    perms = [dict_from_row(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(perms)

# ==================== STATS API ====================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    cur = conn.execute("SELECT COUNT(*) as total FROM item")
    total = cur.fetchone()['total']
    
    cur = conn.execute("SELECT COUNT(*) as total FROM item WHERE stok = 0")
    zero = cur.fetchone()['total']
    
    conn.close()
    return jsonify({
        'total_items': total,
        'zero_stok': zero,
        'normal_stok': total - zero
    })

if __name__ == '__main__':
    # Ensure db directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Run server
    print("=" * 50)
    print("Stock Gudang Utama - Flask API Server")
    print("=" * 50)
    print(f"Database: {DB_PATH}")
    print(f"URL: http://localhost:8789")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8789, debug=True)