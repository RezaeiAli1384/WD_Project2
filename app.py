# --------------------------
# 1. وارد کردن کتابخانه‌های لازم
# --------------------------
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime

# ایجاد برنامه Flask
app = Flask(__name__)

# تنظیمات اتصال به MongoDB
app.config["MONGO_URI"] = "mongodb://localhost:27017/todo_db"
mongo = PyMongo(app)

# --------------------------
# توابع کمکی
# --------------------------
def serialize_task(task):
    """تبدیل سند MongoDB به فرمت JSON"""
    return {
        "id": str(task["_id"]),
        "title": task.get("title", ""),
        "description": task.get("description", ""),
        "created_at": task.get("created_at", datetime.utcnow()).isoformat(),
        "completed": task.get("completed", False)
    }

# --------------------------
# نقاط پایانی (Endpoints)
# --------------------------

# (A) صفحه اصلی با راهنمایی
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "به API مدیریت تسک‌ها خوش آمدید! 🎉",
        "endpoints": {
            "get_tasks": "GET /tasks",
            "create_tasks": "POST /tasks",
            "get_task": "GET /tasks/<task_id>",
            "update_task": "PUT /tasks/<task_id>",
            "delete_task": "DELETE /tasks/<task_id>",
            "search_tasks": "GET /tasks/search?q=...",
            "bulk_update": "PUT /tasks/bulk/update",
            "bulk_delete": "DELETE /tasks/bulk/delete",
            "delete_all_tasks": "DELETE /tasks/all",
            "delete_database": "DELETE /database/delete",
            "count_tasks": "GET /tasks/count"
        }
    }), 200

# (B) دریافت تسک‌ها با صفحه‌بندی، فیلتر، مرتب‌سازی و جستجو
@app.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        # پارامترهای کوئری
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')  # 'asc' یا 'desc'
        completed = request.args.get('completed')  # 'true' یا 'false'
        q = request.args.get('q', '')  # جستجو
        date_from = request.args.get('date_from')  # YYYY-MM-DD
        date_to = request.args.get('date_to')      # YYYY-MM-DD

        # ساخت کوئری MongoDB
        query = {}
        if q:
            query['$or'] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}}
            ]
        if completed is not None:
            query['completed'] = completed.lower() == 'true'
        if date_from or date_to:
            range_query = {}
            if date_from:
                range_query['$gte'] = datetime.fromisoformat(date_from)
            if date_to:
                range_query['$lte'] = datetime.fromisoformat(date_to)
            query['created_at'] = range_query

        # مرتب‌سازی
        sort_direction = -1 if order == 'desc' else 1

        # صفحه‌بندی
        skips = per_page * (page - 1)
        cursor = mongo.db.tasks.find(query) \
            .sort(sort_by, sort_direction) \
            .skip(skips) \
            .limit(per_page)

        tasks = [serialize_task(task) for task in cursor]
        return jsonify({
            "page": page,
            "per_page": per_page,
            "tasks": tasks
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (C) ایجاد تسک (تکی یا گروهی)
@app.route('/tasks', methods=['POST'])
def create_tasks():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "داده‌ای ارسال نشده است"}), 400

        # ایجاد چندگانه
        if isinstance(data, list):
            inserted_ids = []
            for idx, task in enumerate(data, 1):
                if 'title' not in task:
                    return jsonify({"error": f"آیتم {idx}: عنوان الزامی است"}), 400
                new_task = {
                    "title": task['title'],
                    "description": task.get('description', ''),
                    "created_at": datetime.utcnow(),
                    "completed": False
                }
                result = mongo.db.tasks.insert_one(new_task)
                inserted_ids.append(str(result.inserted_id))
            return jsonify({
                "message": f"{len(inserted_ids)} تسک ایجاد شد",
                "task_ids": inserted_ids
            }), 201

        # ایجاد تک
        if 'title' not in data:
            return jsonify({"error": "عنوان الزامی است"}), 400
        new_task = {
            "title": data['title'],
            "description": data.get('description', ''),
            "created_at": datetime.utcnow(),
            "completed": False
        }
        result = mongo.db.tasks.insert_one(new_task)
        return jsonify(serialize_task({**new_task, '_id': result.inserted_id})), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (D) دریافت یک تسک خاص
@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    try:
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "شناسه تسک نامعتبر است"}), 400
        task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            return jsonify({"error": "تسک یافت نشد"}), 404
        return jsonify(serialize_task(task)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (E) به‌روزرسانی یک تسک
@app.route('/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    try:
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "شناسه تسک نامعتبر است"}), 400
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "داده‌ای برای به‌روزرسانی ارسال نشده"}), 400

        updates = {}
        for field in ['title', 'description', 'completed']:
            if field in data:
                updates[field] = data[field] if field != 'completed' else bool(data[field])
        if not updates:
            return jsonify({"error": "فیلدی برای به‌روزرسانی مشخص نشده"}), 400

        result = mongo.db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": updates})
        if result.matched_count == 0:
            return jsonify({"error": "تسک یافت نشد"}), 404
        return jsonify({"message": "تسک با موفقیت به‌روزرسانی شد"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (F) به‌روزرسانی گروهی تسک‌ها
@app.route('/tasks/bulk/update', methods=['PUT'])
def bulk_update_tasks():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, list) or not data:
            return jsonify({"error": "لیست داده‌ها خالی است"}), 400

        ops = []
        for idx, item in enumerate(data, 1):
            if 'id' not in item or not ObjectId.is_valid(item['id']):
                return jsonify({"error": f"آیتم {idx}: شناسه نامعتبر یا وجود ندارد"}), 400
            updates = {f: item[f] for f in ['title', 'description'] if f in item}
            if 'completed' in item:
                updates['completed'] = bool(item['completed'])
            if not updates:
                return jsonify({"error": f"آیتم {idx}: هیچ فیلدی برای به‌روز‌رسانی مشخص نشده"}), 400
            ops.append(UpdateOne({"_id": ObjectId(item['id'])}, {"$set": updates}))

        result = mongo.db.tasks.bulk_write(ops, ordered=False)
        return jsonify({
            "message": "به‌روزرسانی گروهی با موفقیت انجام شد",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (K) حذف گروهی تسک‌ها
@app.route('/tasks/bulk/delete', methods=['DELETE'])
def bulk_delete_tasks():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, list) or not data:
            return jsonify({"error": "لیست شناسه‌ها خالی است"}), 400

        task_ids = []
        for tid in data:
            if not ObjectId.is_valid(tid):
                return jsonify({"error": f"شناسه '{tid}' نامعتبر است"}), 400
            task_ids.append(ObjectId(tid))

        result = mongo.db.tasks.delete_many({"_id": {"$in": task_ids}})
        return jsonify({
            "message": f"{result.deleted_count} تسک حذف شد",
            "deleted_count": result.deleted_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (G) حذف یک تسک
@app.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "شناسه تسک نامعتبر است"}), 400
        result = mongo.db.tasks.delete_one({"_id": ObjectId(task_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "تسک یافت نشد"}), 404
        return jsonify({"message": "تسک با موفقیت حذف شد"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (H) جستجوی آزاد تسک‌ها (هر فیلد)
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    try:
        q = request.args.get('q', '')
        if not q:
            return jsonify({"error": "عبارت جستجو خالی است"}), 400
        regex = {"$regex": q, "$options": "i"}
        query = {
            "$or": [
                {"title": regex},
                {"description": regex}
            ]
        }
        tasks = list(mongo.db.tasks.find(query))
        return jsonify([serialize_task(t) for t in tasks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (I) حذف تمام تسک‌ها
@app.route('/tasks/all', methods=['DELETE'])
def delete_all_tasks():
    try:
        result = mongo.db.tasks.delete_many({})
        return jsonify({"message": f"تمام تسک‌ها ({result.deleted_count}) حذف شدند", "deleted_count": result.deleted_count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (J) حذف کامل پایگاه داده
@app.route('/database/delete', methods=['DELETE'])
def delete_database():
    try:
        mongo.db.client.drop_database('todo_db')
        return jsonify({"message": "پایگاه داده به طور کامل حذف شد"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# شمارش تسک‌ها با فیلترهای مختلف
@app.route('/tasks/count', methods=['GET'])
def count_tasks():
    try:
        completed = request.args.get('completed')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        q = request.args.get('q', '')

        query = {}
        if completed is not None:
            query['completed'] = completed.lower() == 'true'
        if q:
            query['$or'] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}}
            ]
        if date_from or date_to:
            range_q = {}
            if date_from:
                range_q['$gte'] = datetime.fromisoformat(date_from)
            if date_to:
                range_q['$lte'] = datetime.fromisoformat(date_to)
            query['created_at'] = range_q

        count = mongo.db.tasks.count_documents(query)
        return jsonify({"count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# اجرای سرور
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
