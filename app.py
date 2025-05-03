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
# 2. توابع کمکی
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
# 3. نقاط پایانی (Endpoints)
# --------------------------

# (A) صفحه اصلی با راهنمایی
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "به API مدیریت تسک‌ها خوش آمدید! 🎉",
        "endpoints": {
            "get_all_tasks": "GET /tasks",
            "create_task": "POST /tasks",
            "get_task": "GET /tasks/<task_id>",
            "update_task": "PUT /tasks/<task_id>",
            "delete_task": "DELETE /tasks/<task_id>",
            "search_tasks": "GET /tasks/search?q=...",
            "delete_all_tasks": "DELETE /tasks/all",
            "bulk_update": "PUT /tasks/bulk/update",
            "delete_database": "DELETE /database/delete"
        },
        "example": "برای مشاهده تمام تسک‌ها به آدرس زیر مراجعه کنید:",
        "example_url": "http://192.168.1.107:8000/tasks"
    }), 200

# (B) دریافت تمام تسک‌ها
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    try:
        tasks = list(mongo.db.tasks.find())
        return jsonify([serialize_task(task) for task in tasks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (C) ایجاد تسک (تکی یا گروهی)
@app.route('/tasks', methods=['POST'])
def create_task():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "داده‌ای ارسال نشده است"}), 400

        # ایجاد چندین تسک
        if isinstance(data, list):
            inserted_ids = []
            for task in data:
                if "title" not in task:
                    return jsonify({"error": "عنوان برای همه تسک‌ها الزامی است"}), 400
                new_task = {
                    "title": task["title"],
                    "description": task.get("description", ""),
                    "created_at": datetime.utcnow(),
                    "completed": False
                }
                result = mongo.db.tasks.insert_one(new_task)
                inserted_ids.append(str(result.inserted_id))
            return jsonify({
                "message": f"{len(inserted_ids)} تسک ایجاد شد",
                "task_ids": inserted_ids
            }), 201

        # ایجاد یک تسک
        if "title" not in data:
            return jsonify({"error": "عنوان الزامی است"}), 400
        new_task = {
            "title": data["title"],
            "description": data.get("description", ""),
            "created_at": datetime.utcnow(),
            "completed": False
        }
        result = mongo.db.tasks.insert_one(new_task)
        return jsonify(serialize_task({**new_task, "_id": result.inserted_id})), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (D) دریافت یک تسک خاص
@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    try:
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "شناسه تسک نامعتبر است"}), 400
        task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
        if task:
            return jsonify(serialize_task(task)), 200
        return jsonify({"error": "تسک یافت نشد"}), 404
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
        if "title" in data:
            updates["title"] = data["title"]
        if "description" in data:
            updates["description"] = data["description"]
        if "completed" in data:
            updates["completed"] = bool(data["completed"])

        if not updates:
            return jsonify({"error": "فیلدی برای به‌روزرسانی مشخص نشده"}), 400

        result = mongo.db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": updates}
        )
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

        operations = []
        for idx, item in enumerate(data, 1):
            if "id" not in item:
                return jsonify({"error": f"آیتم {idx}: شناسه تسک وجود ندارد"}), 400
            
            if not ObjectId.is_valid(item["id"]):
                return jsonify({"error": f"آیتم {idx}: شناسه تسک نامعتبر است"}), 400
            
            updates = {}
            if "title" in item:
                updates["title"] = item["title"]
            if "description" in item:
                updates["description"] = item["description"]
            if "completed" in item:
                updates["completed"] = bool(item["completed"])
            
            if not updates:
                return jsonify({"error": f"آیتم {idx}: هیچ فیلدی برای به‌روزرسانی مشخص نشده"}), 400
            
            operations.append(
                UpdateOne(
                    {"_id": ObjectId(item["id"])},
                    {"$set": updates}
                )
            )

        result = mongo.db.tasks.bulk_write(operations, ordered=False)
        return jsonify({
            "message": "به‌روزرسانی گروهی با موفقیت انجام شد",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count
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

# (H) جستجوی تسک‌ها
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    try:
        search_term = request.args.get('q', '')
        query = {
            "$or": [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}}
            ]
        }
        tasks = list(mongo.db.tasks.find(query))
        return jsonify([serialize_task(task) for task in tasks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (I) حذف تمام تسک‌ها
@app.route('/tasks/all', methods=['DELETE'])
def delete_all_tasks():
    try:
        result = mongo.db.tasks.delete_many({})
        return jsonify({
            "message": f"تمام تسک‌ها ({result.deleted_count} مورد) حذف شدند",
            "deleted_count": result.deleted_count
        }), 200
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

# --------------------------
# 4. اجرای سرور
# --------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
