from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'
mongo = PyMongo(app)

# 🏠 صفحه خوش آمدگویی
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Task API! Use /tasks to see all tasks."}), 200

# 📋 دریافت همه تسک‌ها
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    tasks = list(mongo.db.tasks.find())
    for task in tasks:
        task['_id'] = str(task['_id'])
    return jsonify(tasks), 200

# ➕ ایجاد چندین تسک همزمان
@app.route('/tasks/bulk', methods=['POST'])
def create_tasks_bulk():
    data = request.get_json(force=True)
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Provide a non-empty list"}), 400

    docs = []
    for item in data:
        if 'title' not in item:
            return jsonify({"error": "Each task must have a title"}), 400
        docs.append({
            'title': item['title'],
            'description': item.get('description', ''),
            'completed': bool(item.get('completed', False)),
            'created_at': datetime.utcnow(),
            'reminder_time': item.get('reminder_time')  # اختیاری
        })
    result = mongo.db.tasks.insert_many(docs)
    return jsonify({"inserted_ids": [str(_id) for _id in result.inserted_ids]}), 201

# ✏️ به‌روزرسانی چندین تسک همزمان
@app.route('/tasks/bulk', methods=['PUT'])
def update_tasks_bulk():
    data = request.get_json(force=True)
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Provide a non-empty list"}), 400

    operations = []
    for item in data:
        tid = item.get('id')
        if not tid or not ObjectId.is_valid(tid):
            continue
        oid = ObjectId(tid)
        updates = {}
        for field in ('title', 'description', 'completed', 'reminder_time'):
            if field in item:
                updates[field] = bool(item[field]) if field == 'completed' else item[field]
        if updates:
            operations.append(UpdateOne({'_id': oid}, {'$set': updates}))

    if not operations:
        return jsonify({"error": "No valid updates provided"}), 400

    res = mongo.db.tasks.bulk_write(operations, ordered=False)
    return jsonify({
        "matched_count": res.matched_count,
        "modified_count": res.modified_count
    }), 200

# ❌ حذف چندین تسک همزمان
@app.route('/tasks/bulk', methods=['DELETE'])
def delete_tasks_bulk():
    data = request.get_json(force=True)
    if not data or 'ids' not in data or not isinstance(data['ids'], list):
        return jsonify({"error": "Provide an array of ids"}), 400

    valid_ids = [ObjectId(i) for i in data['ids'] if ObjectId.is_valid(i)]
    if not valid_ids:
        return jsonify({"error": "No valid IDs provided"}), 400

    res = mongo.db.tasks.delete_many({'_id': {'$in': valid_ids}})
    return jsonify({
        "deleted_count": res.deleted_count
    }), 200

# 🔍 جستجو براساس title یا description یا تاریخ
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    query = {}
    title = request.args.get('title')
    description = request.args.get('description')
    created_at = request.args.get('created_at')

    if title:
        query['title'] = {'$regex': title, '$options': 'i'}
    if description:
        query['description'] = {'$regex': description, '$options': 'i'}
    if created_at:
        try:
            date = datetime.strptime(created_at, "%Y-%m-%d")
            next_day = date + timedelta(days=1)
            query['created_at'] = {'$gte': date, '$lt': next_day}
        except:
            return jsonify({"error": "created_at format should be YYYY-MM-DD"}), 400

    tasks = list(mongo.db.tasks.find(query))
    for task in tasks:
        task['_id'] = str(task['_id'])
    return jsonify(tasks), 200

# 🕰️ Reminder Function (Notification شبیه سازی شده)
def check_reminders():
    while True:
        now = datetime.utcnow()
        tasks = mongo.db.tasks.find({
            'reminder_time': {'$exists': True, '$ne': None}
        })
        for task in tasks:
            reminder_time = datetime.strptime(task['reminder_time'], "%Y-%m-%dT%H:%M:%S")
            if now >= reminder_time:
                print(f"🔔 Reminder: Task '{task['title']}' is due!")
                # بعد از نمایش، ریمایندر حذف شود
                mongo.db.tasks.update_one({'_id': task['_id']}, {'$unset': {'reminder_time': ""}})
        time.sleep(30)  # هر ۳۰ ثانیه یکبار چک شود

# 📋 شمارش تعداد تسک ها
@app.route('/tasks/count', methods=['GET'])
def count_tasks():
    total = mongo.db.tasks.count_documents({})
    completed = mongo.db.tasks.count_documents({'completed': True})
    incomplete = mongo.db.tasks.count_documents({'completed': False})
    return jsonify({
        "total_tasks": total,
        "completed_tasks": completed,
        "incomplete_tasks": incomplete
    }), 200

# 🚀 اجرای چکر ریمایندر در پس زمینه
threading.Thread(target=check_reminders, daemon=True).start()

# ⚙️ اجرای اپلیکیشن
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
