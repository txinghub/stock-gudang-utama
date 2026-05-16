#!/usr/bin/env python3
"""
Flask API Server for Stock Gudang Utama
Connects to SQLite database in db/stock.db
"""

import sqlite3
import json
import os
from datetime import datetime
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
        data.get('nama', '').upper(),
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
    # Return full created item
    cur = conn.execute("SELECT * FROM item WHERE id = ?", (item_id,))
    created = dict_from_row(cur.fetchone())
    conn.close()
    return jsonify(created), 201

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
        data.get('nama', '').upper(),
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
    # Return full updated item
    cur = conn.execute("SELECT * FROM item WHERE id = ?", (item_id,))
    updated = dict_from_row(cur.fetchone())
    conn.close()
    return jsonify(updated)

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_db()
    # Check if item has movements (history) — cannot delete if yes
    movements = conn.execute(
        "SELECT COUNT(*) FROM movements WHERE item_id = ?", (item_id,)
    ).fetchone()[0]
    if movements > 0:
        conn.close()
        return jsonify({'success': False, 'error': 'Item sudah punya history transaksi, tidak boleh dihapus'}), 400
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

# ==================== PEMBELIAN & PENGELUARAN API ====================

def generate_next_faktur(prefix, tanggal):
    """
    Generate next faktur number: AD-PBL/2605/0001
    Format: PREFIX + / + YYMM + / + 4-digit sequential (reset per month)
    """
    year = tanggal[2:4]  # '26'
    month = tanggal[5:7]  # '05'
    prefix_str = f"{prefix}/{year}{month}"  # 'AD-PBL/2605'
    
    # Find highest existing faktur for this prefix
    pattern = f"{prefix_str}%"
    conn = get_db()
    cur = conn.execute(
        "SELECT no_faktur FROM (SELECT no_faktur FROM pembelian WHERE no_faktur LIKE ? UNION ALL SELECT no_faktur FROM pengeluaran WHERE no_faktur LIKE ?) ORDER BY no_faktur DESC LIMIT 1",
        (pattern, pattern)
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        last = row['no_faktur']  # e.g. "AD-PBL/2605/0037"
        parts = last.split('/')
        if len(parts) == 3:
            seq = int(parts[2]) + 1
        else:
            seq = 1
    else:
        seq = 1
    
    return f"{prefix_str}/{seq:04d}"

@app.route('/api/next-faktur', methods=['GET'])
def get_next_faktur():
    """Get next auto-generated faktur number"""
    t_type = request.args.get('type', 'PEMBELIAN').upper()
    tanggal = request.args.get('tanggal', '')
    if not tanggal:
        tanggal = datetime.now().strftime('%Y-%m-%d')
    
    prefix = 'AD-PBL' if t_type == 'PEMBELIAN' else 'AD-MTS'
    next_no = generate_next_faktur(prefix, tanggal)
    return jsonify({'no_faktur': next_no, 'prefix': prefix})

# ----- PEMBELIAN -----

@app.route('/api/pembelian', methods=['GET'])
def get_pembelian():
    conn = get_db()
    cur = conn.execute("SELECT * FROM pembelian ORDER BY tanggal DESC, id DESC LIMIT 100")
    rows = [dict_from_row(row) for row in cur.fetchall()]
    for r in rows:
        ci = conn.execute("SELECT COUNT(*) as c FROM pembelian_items WHERE pembelian_id = ?", (r['id'],)).fetchone()
        r['items_count'] = ci['c'] if ci else 0
    conn.close()
    return jsonify(rows)

@app.route('/api/pembelian/<int:pembelian_id>', methods=['GET'])
def get_pembelian_detail(pembelian_id):
    conn = get_db()
    cur = conn.execute("SELECT * FROM pembelian WHERE id = ?", (pembelian_id,))
    header = dict_from_row(cur.fetchone())
    if not header:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    cur = conn.execute("SELECT * FROM pembelian_items WHERE pembelian_id = ?", (pembelian_id,))
    items = [dict_from_row(row) for row in cur.fetchall()]
    conn.close()
    header['items'] = items
    return jsonify(header)

@app.route('/api/pembelian', methods=['POST'])
def add_pembelian():
    data = request.json
    conn = get_db()
    try:
        no_faktur = data.get('no_faktur', '').strip()
        tanggal = data.get('tanggal', '')
        if not no_faktur:
            no_faktur = generate_next_faktur('AD-PBL', tanggal)
        else:
            no_faktur = no_faktur.upper()

        cur = conn.execute("""
            INSERT INTO pembelian (no_faktur, tanggal, supplier, total, keterangan, user, created)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            no_faktur,
            tanggal,
            data.get('supplier', '').upper(),
            data.get('total', 0),
            data.get('keterangan', '').upper(),
            data.get('user', 'ADMIN')
        ))
        pembelian_id = cur.lastrowid

        for ti in data.get('items', []):
            conn.execute("""
                INSERT INTO pembelian_items (pembelian_id, item_id, nama, satuan, qty, harga, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pembelian_id,
                ti.get('item_id'),
                ti.get('nama', '').upper(),
                ti.get('satuan', '').upper(),
                ti.get('qty', 0),
                ti.get('harga', 0),
                ti.get('subtotal', 0)
            ))
            item_id = ti.get('item_id')
            qty = ti.get('qty', 0)
            conn.execute("UPDATE item SET stok = stok + ? WHERE id = ?", (qty, item_id))
            conn.execute("""
                INSERT INTO movements (item_id, item_nama, kode, type, jumlah, satuan, tanggal, catatan)
                VALUES (?, ?, '', 'MASUK', ?, ?, ?, ?)
            """, (item_id, ti.get('nama', '').upper(), qty, ti.get('satuan', '').upper(),
                  tanggal, no_faktur))

        conn.commit()
        conn.close()
        return jsonify({'id': pembelian_id, 'no_faktur': no_faktur}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'No faktur sudah ada'}), 400

@app.route('/api/pembelian/<int:pembelian_id>', methods=['DELETE'])
def delete_pembelian(pembelian_id):
    conn = get_db()
    cur = conn.execute("SELECT * FROM pembelian WHERE id = ?", (pembelian_id,))
    t = dict_from_row(cur.fetchone())
    if t:
        cur = conn.execute("SELECT * FROM pembelian_items WHERE pembelian_id = ?", (pembelian_id,))
        for ti in cur.fetchall():
            conn.execute("UPDATE item SET stok = stok - ? WHERE id = ?", (ti['qty'], ti['item_id']))
        conn.execute("DELETE FROM pembelian_items WHERE pembelian_id = ?", (pembelian_id,))
        conn.execute("DELETE FROM movements WHERE catatan = ?", (t['no_faktur'],))
    conn.execute("DELETE FROM pembelian WHERE id = ?", (pembelian_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ----- PENGELUARAN -----

@app.route('/api/pengeluaran', methods=['GET'])
def get_pengeluaran():
    conn = get_db()
    cur = conn.execute("SELECT * FROM pengeluaran ORDER BY tanggal DESC, id DESC LIMIT 100")
    rows = [dict_from_row(row) for row in cur.fetchall()]
    for r in rows:
        ci = conn.execute("SELECT COUNT(*) as c FROM pengeluaran_items WHERE pengeluaran_id = ?", (r['id'],)).fetchone()
        r['items_count'] = ci['c'] if ci else 0
    conn.close()
    return jsonify(rows)

@app.route('/api/pengeluaran/<int:pengeluaran_id>', methods=['GET'])
def get_pengeluaran_detail(pengeluaran_id):
    conn = get_db()
    cur = conn.execute("SELECT * FROM pengeluaran WHERE id = ?", (pengeluaran_id,))
    header = dict_from_row(cur.fetchone())
    if not header:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    cur = conn.execute("SELECT * FROM pengeluaran_items WHERE pengeluaran_id = ?", (pengeluaran_id,))
    items = [dict_from_row(row) for row in cur.fetchall()]
    conn.close()
    header['items'] = items
    return jsonify(header)

@app.route('/api/pengeluaran', methods=['POST'])
def add_pengeluaran():
    data = request.json
    conn = get_db()
    try:
        no_faktur = data.get('no_faktur', '').strip()
        tanggal = data.get('tanggal', '')
        if not no_faktur:
            no_faktur = generate_next_faktur('AD-MTS', tanggal)
        else:
            no_faktur = no_faktur.upper()

        cur = conn.execute("""
            INSERT INTO pengeluaran (no_faktur, tanggal, customer, total, keterangan, user, created)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            no_faktur,
            tanggal,
            data.get('customer', '').upper(),
            data.get('total', 0),
            data.get('keterangan', '').upper(),
            data.get('user', 'ADMIN')
        ))
        pengeluaran_id = cur.lastrowid

        for ti in data.get('items', []):
            conn.execute("""
                INSERT INTO pengeluaran_items (pengeluaran_id, item_id, nama, satuan, qty, harga, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pengeluaran_id,
                ti.get('item_id'),
                ti.get('nama', '').upper(),
                ti.get('satuan', '').upper(),
                ti.get('qty', 0),
                ti.get('harga', 0),
                ti.get('subtotal', 0)
            ))
            item_id = ti.get('item_id')
            qty = ti.get('qty', 0)
            conn.execute("UPDATE item SET stok = stok - ? WHERE id = ?", (qty, item_id))
            conn.execute("""
                INSERT INTO movements (item_id, item_nama, kode, type, jumlah, satuan, tanggal, catatan)
                VALUES (?, ?, '', 'KELUAR', ?, ?, ?, ?)
            """, (item_id, ti.get('nama', '').upper(), qty, ti.get('satuan', '').upper(),
                  tanggal, no_faktur))

        conn.commit()
        conn.close()
        return jsonify({'id': pengeluaran_id, 'no_faktur': no_faktur}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'No faktur sudah ada'}), 400

@app.route('/api/pengeluaran/<int:pengeluaran_id>', methods=['DELETE'])
def delete_pengeluaran(pengeluaran_id):
    conn = get_db()
    cur = conn.execute("SELECT * FROM pengeluaran WHERE id = ?", (pengeluaran_id,))
    t = dict_from_row(cur.fetchone())
    if t:
        cur = conn.execute("SELECT * FROM pengeluaran_items WHERE pengeluaran_id = ?", (pengeluaran_id,))
        for ti in cur.fetchall():
            conn.execute("UPDATE item SET stok = stok + ? WHERE id = ?", (ti['qty'], ti['item_id']))
        conn.execute("DELETE FROM pengeluaran_items WHERE pengeluaran_id = ?", (pengeluaran_id,))
        conn.execute("DELETE FROM movements WHERE catatan = ?", (t['no_faktur'],))
    conn.execute("DELETE FROM pengeluaran WHERE id = ?", (pengeluaran_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ==================== USERS API ====================

@app.route('/api/login', methods=['POST'])
def login():
    print('DEBUG login:', request.data)
    data = request.json
    username = data.get('username', '').upper()
    password = data.get('password', '')
    print('DEBUG username:', repr(username), 'password:', repr(password))
    
    conn = get_db()
    cur = conn.execute("SELECT * FROM users WHERE UPPER(username) = ?", (username,))
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

@app.route('/api/users/<username>', methods=['GET', 'DELETE'])
def get_or_delete_user(username):
    # If username is numeric, treat as user_id (Flask can't distinguish int vs string in same rule)
    if username.isdigit():
        user_id = int(username)
        conn = get_db()
        if request.method == 'DELETE':
            cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            deleted = cur.rowcount
            conn.close()
            if deleted == 0:
                return jsonify({'error': 'User tidak ditemukan'}), 404
            return jsonify({'ok': True, 'deleted': deleted})
        else:
            cur = conn.execute("SELECT id, username, role, created, lastlogin FROM users WHERE id = ?", (user_id,))
            user = dict_from_row(cur.fetchone())
            conn.close()
            return jsonify(user) if user else jsonify({'error': 'Not found'}), 404
    # String username lookup (for login/other uses)
    conn = get_db()
    cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = dict_from_row(cur.fetchone())
    conn.close()
    return jsonify(user) if user else jsonify({'error': 'Not found'}), 404

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db()
    cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({'error': 'User tidak ditemukan'}), 404
    return jsonify({'ok': True, 'deleted': deleted})
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
    # Auto-backup before server starts
    import shutil
    import glob
    BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'db', 'backups')
    NAS_DIR = '/Users/linggothioputro/NAS_Hermes/stock-gudang-utama/backups'
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    local_dest = os.path.join(BACKUP_DIR, f'stock_{ts}.db')
    shutil.copy2(DB_PATH, local_dest)
    # Keep only 10 newest local backups
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'stock_*.db')))
    while len(backups) > 10:
        os.remove(backups.pop(0))
    # NAS backup
    try:
        os.makedirs(NAS_DIR, exist_ok=True)
        shutil.copy2(DB_PATH, os.path.join(NAS_DIR, f'stock_{ts}.db'))
        print(f"✓ Backup NAS: stock_{ts}.db")
    except:
        print("⚠ NAS backup skipped (not available)")
    print(f"✓ Backup local: stock_{ts}.db")
    
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