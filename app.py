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
            "search_tasks": "GET /tasks/search?q=...",
            "delete_all_tasks": "DELETE /tasks/all"
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

# (D) حذف کامل تمام تسک‌ها
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

# بقیه endpointها (دریافت تک تسک، جستجو، به‌روزرسانی و ...) مانند کد قبلی بدون تغییر باقی می‌مانند

# --------------------------
# 4. اجرای سرور
# --------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
