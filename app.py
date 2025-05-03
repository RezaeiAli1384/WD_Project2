from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime, timedelta
import threading, time

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'
mongo = PyMongo(app)

# 🏠 صفحه اصلی
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Welcome to the Task API! Use /tasks to list or add tasks. Use /tasks/bulk for bulk operations."
    }), 200

# ✅ ثبت یک تسک تکی
@app.route('/tasks', methods=['POST'])
def create_single_task():
    """
    POST /tasks
    بدنه: {
      title:str (الزامی),
      description:str?,
      completed:bool?,
      due_date:ISO8601?,
      reminder_time:ISO8601?
    }
    """
    data = request.get_json(force=True)
    title = data.get('title')
    if not title:
        return jsonify({"error": "title is required"}), 400

    task = {
        'title': title,
        'description': data.get('description', ''),
        'completed': bool(data.get('completed', False)),
        'created_at': datetime.utcnow(),
        'due_date': datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        'reminder_time': datetime.fromisoformat(data['reminder_time']) if data.get('reminder_time') else None
    }

    inserted_id = mongo.db.tasks.insert_one(task).inserted_id
    return jsonify({"inserted_id": str(inserted_id)}), 201

# 📋 گرفتن لیست تسک‌ها
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    q = {}
    if 'completed' in request.args:
        q['completed'] = request.args.get('completed').lower() == 'true'
    if 'from_date' in request.args:
        q.setdefault('created_at', {})['$gte'] = datetime.fromisoformat(request.args['from_date'])
    if 'to_date' in request.args:
        q.setdefault('created_at', {})['$lte'] = datetime.fromisoformat(request.args['to_date'])

    total = mongo.db.tasks.count_documents(q)
    sort_by = request.args.get('sort_by', 'created_at')
    order = -1 if request.args.get('order', 'desc') == 'desc' else 1

    page = max(int(request.args.get('page', 1)), 1)
    per_page = max(int(request.args.get('per_page', 10)), 1)
    skip = (page - 1) * per_page

    cursor = mongo.db.tasks.find(q).sort(sort_by, order).skip(skip).limit(per_page)

    tasks = []
    row_num = skip + 1
    for t in cursor:
        t['_id'] = str(t['_id'])
        t['created_at'] = t['created_at'].isoformat()
        t['due_date'] = t.get('due_date').isoformat() if t.get('due_date') else None
        t['reminder_time'] = t.get('reminder_time').isoformat() if t.get('reminder_time') else None
        if t.get('due_date'):
            t['remaining_time'] = max((datetime.fromisoformat(t['due_date']) - datetime.utcnow()).total_seconds(), 0)
        else:
            t['remaining_time'] = None
        t['row_number'] = row_num
        row_num += 1
        tasks.append(t)

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "tasks": tasks
    }), 200

# ➕ درج گروهی تسک‌ها
@app.route('/tasks/bulk', methods=['POST'])
def create_tasks_bulk():
    data = request.get_json(force=True)
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Provide a non-empty list"}), 400

    docs = []
    for it in data:
        if 'title' not in it:
            return jsonify({"error": "Each task must have title"}), 400
        docs.append({
            'title': it['title'],
            'description': it.get('description', ''),
            'completed': bool(it.get('completed', False)),
            'created_at': datetime.utcnow(),
            'due_date': datetime.fromisoformat(it['due_date']) if it.get('due_date') else None,
            'reminder_time': datetime.fromisoformat(it['reminder_time']) if it.get('reminder_time') else None
        })

    res = mongo.db.tasks.insert_many(docs)
    return jsonify({"inserted_ids": [str(_id) for _id in res.inserted_ids]}), 201

# ✏️ بروزرسانی گروهی
@app.route('/tasks/bulk', methods=['PUT'])
def update_tasks_bulk():
    data = request.get_json(force=True)
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Provide a non-empty list"}), 400

    ops = []
    for it in data:
        tid = it.get('id')
        if not tid or not ObjectId.is_valid(tid):
            continue
        u = {}
        for f in ('title', 'description', 'completed', 'due_date', 'reminder_time'):
            if f in it:
                if f in ('due_date', 'reminder_time') and it[f]:
                    u[f] = datetime.fromisoformat(it[f])
                elif f == 'completed':
                    u[f] = bool(it[f])
                else:
                    u[f] = it[f]
        if u:
            ops.append(UpdateOne({'_id': ObjectId(tid)}, {'$set': u}))

    if not ops:
        return jsonify({"error": "No valid updates provided"}), 400

    res = mongo.db.tasks.bulk_write(ops, ordered=False)
    return jsonify({
        "matched_count": res.matched_count,
        "modified_count": res.modified_count
    }), 200

# ❌ حذف گروهی
@app.route('/tasks/bulk', methods=['DELETE'])
def delete_tasks_bulk():
    data = request.get_json(force=True)
    ids = data.get('ids') if isinstance(data, dict) else None
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "Provide a list of ids"}), 400

    valid_ids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
    if not valid_ids:
        return jsonify({"error": "No valid IDs provided"}), 400

    res = mongo.db.tasks.delete_many({'_id': {'$in': valid_ids}})
    return jsonify({"deleted_count": res.deleted_count}), 200

# 🔍 جستجو
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    q = {}
    ids = request.args.getlist('id')
    if ids:
        oids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
        if oids:
            q['_id'] = {'$in': oids}

    for field in ('title', 'description'):
        v = request.args.get(field)
        if v:
            q[field] = {'$regex': v, '$options': 'i'}

    ca = request.args.get('created_at')
    if ca:
        try:
            d = datetime.fromisoformat(ca)
            q['created_at'] = {'$gte': d, '$lt': d + timedelta(days=1)}
        except:
            return jsonify({"error": "created_at must be YYYY-MM-DD"}), 400

    results = []
    for t in mongo.db.tasks.find(q):
        t['_id'] = str(t['_id'])
        t['created_at'] = t['created_at'].isoformat()
        results.append(t)

    return jsonify(results), 200

# 🔔 یادآور پس‌زمینه
def reminder_loop():
    while True:
        now = datetime.utcnow()
        tasks = mongo.db.tasks.find({'reminder_time': {'$ne': None}})
        for t in tasks:
            if now >= t['reminder_time']:
                print(f"🔔 Reminder: Task '{t['title']}' is due!")
                mongo.db.tasks.update_one({'_id': t['_id']}, {'$unset': {'reminder_time': ""}})
        time.sleep(60)

threading.Thread(target=reminder_loop, daemon=True).start()

# 🧮 شمارش تسک‌ها
@app.route('/tasks/counts', methods=['GET'])
def count_tasks():
    total = mongo.db.tasks.count_documents({})
    completed = mongo.db.tasks.count_documents({'completed': True})
    return jsonify({
        "total_tasks": total,
        "completed_tasks": completed,
        "remaining_tasks": total - completed
    }), 200

# 🗑️ حذف دیتابیس
@app.route('/database/drop', methods=['DELETE'])
def drop_database():
    mongo.cx.drop_database('todo_db')
    return jsonify({"message": "Database 'todo_db' dropped successfully"}), 200

# 🚀 اجرا
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
