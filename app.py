# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime, timedelta
import threading
import time

# ایجاد برنامه Flask و تنظیمات اولیه
app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'  # اتصال به MongoDB محلی
mongo = PyMongo(app)  # ایجاد شی مدیریت دیتابیس

# 🏠 اندپوینت صفحه اصلی
@app.route('/', methods=['GET'])
def home():
    """
    نمایش صفحه اصلی و راهنمای API
    
    مثال:
    درخواست: GET /
    پاسخ نمونه:
    {
        "message": "خوش آمدید! برای مدیریت تسکها از /tasks استفاده کنید..."
    }
    """
    return jsonify({
        "message": "خوش آمدید! برای مدیریت تسکها از /tasks استفاده کنید، /tasks/bulk برای عملیات گروهی و /tasks/search برای جستجوی پیشرفته"
    }), 200

# ✅ ایجاد یک تسک جدید
@app.route('/tasks', methods=['POST'])
def create_single_task():
    """
    ایجاد یک تسک جدید
    
    پارامترهای ورودی (JSON):
    - title (الزامی): عنوان تسک
    - description: توضیحات تسک
    - completed: وضعیت انجام (پیشفرض: False)
    - due_date: تاریخ انجام (فرمت ISO8601)
    - reminder_time: زمان یادآوری (فرمت ISO8601)
    
    مثال درخواست:
    POST /tasks
    {
        "title": "تهیه سالاد سزار",
        "description": "کاهو، سس مخصوص، croutons",
        "due_date": "2025-05-10T12:00:00",
        "reminder_time": "2025-05-10T09:00:00"
    }
    
    پاسخ موفق:
    {
        "id": "665b4a6e8c1d7e12a4c3b5a8",
        "message": "تسک با موفقیت ایجاد شد"
    }
    """
    data = request.get_json(force=True)
    if 'title' not in data:
        return jsonify({"error": "عنوان تسک الزامی است"}), 400

    # ایجاد ساختار تسک با مقادیر پیشفرض
    task = {
        'title': data['title'],
        'description': data.get('description', ''),
        'completed': bool(data.get('completed', False)),
        'created_at': datetime.utcnow(),
        'due_date': datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        'reminder_time': datetime.fromisoformat(data['reminder_time']) if data.get('reminder_time') else None
    }

    # درج در دیتابیس و بازگرداندن پاسخ
    result = mongo.db.tasks.insert_one(task)
    return jsonify({
        "id": str(result.inserted_id),
        "message": "تسک با موفقیت ایجاد شد"
    }), 201

# 📋 دریافت لیست تسکها با فیلتر و صفحهبندی
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    """
    دریافت لیست تسکها با قابلیتهای:
    - فیلتر بر اساس وضعیت انجام
    - محدوده تاریخ ایجاد
    - مرتبسازی
    - صفحهبندی
    - شماره ردیف
    
    پارامترهای اختیاری:
    - completed: فیلتر وضعیت انجام (true/false)
    - from_date/to_date: محدوده تاریخ ایجاد (YYYY-MM-DD)
    - sort_by: فیلد مرتبسازی (پیشفرض: created_at)
    - order: ترتیب (asc/desc - پیشفرض: desc)
    - page: شماره صفحه (پیشفرض: 1)
    - per_page: تعداد در هر صفحه (پیشفرض: 10)
    
    مثال درخواست:
    GET /tasks?completed=false&sort_by=due_date&order=asc&page=2
    
    پاسخ نمونه:
    {
        "total": 15,
        "page": 2,
        "per_page": 10,
        "tasks": [
            {
                "row_number": 11,
                "id": "665b4a6e8c1d7e12a4c3b5a8",
                "title": "تهیه سالاد سزار",
                "description": "کاهو، سس مخصوص، croutons",
                "created_at": "2025-05-03T18:45:09.934Z",
                "due_date": "2025-05-10T12:00:00",
                "reminder_time": "2025-05-10T09:00:00",
                "remaining_time": 578339.38369,
                "completed": false
            }
        ]
    }
    """
    # ساخت کوئری فیلتر
    query = {}
    
    # فیلتر وضعیت انجام
    if 'completed' in request.args:
        query['completed'] = request.args.get('completed').lower() == 'true'
    
    # فیلتر محدوده تاریخ
    if 'from_date' in request.args:
        try:
            start_date = datetime.fromisoformat(request.args['from_date'])
            query.setdefault('created_at', {})['$gte'] = start_date
        except ValueError:
            return jsonify({"error": "فرمت تاریخ شروع نادرست است"}), 400
    
    if 'to_date' in request.args:
        try:
            end_date = datetime.fromisoformat(request.args['to_date'])
            query.setdefault('created_at', {})['$lte'] = end_date + timedelta(days=1)
        except ValueError:
            return jsonify({"error": "فرمت تاریخ پایان نادرست است"}), 400

    # تنظیمات مرتبسازی
    sort_field = request.args.get('sort_by', 'created_at')
    sort_order = -1 if request.args.get('order', 'desc') == 'desc' else 1

    # محاسبات صفحهبندی
    page = max(int(request.args.get('page', 1)), 1)
    per_page = max(int(request.args.get('per_page', 10)), 1)
    skip = (page - 1) * per_page

    # اجرای کوئری
    cursor = mongo.db.tasks.find(query).sort(sort_field, sort_order).skip(skip).limit(per_page)
    total = mongo.db.tasks.count_documents(query)

    # پردازش نتایج
    tasks = []
    for index, task in enumerate(cursor, start=skip + 1):
        # تبدیل ObjectId به رشته و تغییر نام
        task['id'] = str(task.pop('_id'))
        # تبدیل تاریخها به فرمت ISO
        task['created_at'] = task['created_at'].isoformat()
        if task.get('due_date'):
            task['due_date'] = task['due_date'].isoformat()
            remaining = (datetime.fromisoformat(task['due_date']) - datetime.utcnow()).total_seconds()
            task['remaining_time'] = max(remaining, 0)
        else:
            task['remaining_time'] = None
        
        if task.get('reminder_time'):
            task['reminder_time'] = task['reminder_time'].isoformat()
        
        # اضافه کردن شماره ردیف با ترتیب جدید
        processed_task = {
            "row_number": index,
            "id": task['id'],
            "title": task['title'],
            "description": task['description'],
            "created_at": task['created_at'],
            "due_date": task.get('due_date'),
            "reminder_time": task.get('reminder_time'),
            "remaining_time": task.get('remaining_time'),
            "completed": task['completed']
        }
        tasks.append(processed_task)

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "tasks": tasks
    }), 200

# ➕ ایجاد گروهی تسکها
@app.route('/tasks/bulk', methods=['POST'])
def create_tasks_bulk():
    """
    ایجاد همزمان چندین تسک
    
    پارامتر ورودی باید آرایهای از اشیاء تسک باشد
    
    مثال درخواست:
    POST /tasks/bulk
    [
        {
            "title": "تسک گروهی ۱",
            "completed": true
        },
        {
            "title": "تسک گروهی ۲",
            "description": "توضیحات نمونه"
        }
    ]
    """
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "ورودی باید یک آرایه باشد"}), 400

    # اعتبارسنجی و ساخت اسناد
    tasks = []
    for item in data:
        if 'title' not in item:
            return jsonify({"error": "هر تسک باید عنوان داشته باشد"}), 400
        task = {
            'title': item['title'],
            'description': item.get('description', ''),
            'completed': bool(item.get('completed', False)),
            'created_at': datetime.utcnow(),
            'due_date': datetime.fromisoformat(item['due_date']) if item.get('due_date') else None,
            'reminder_time': datetime.fromisoformat(item['reminder_time']) if item.get('reminder_time') else None
        }
        tasks.append(task)

    # درج گروهی
    result = mongo.db.tasks.insert_many(tasks)
    return jsonify({
        "inserted_ids": [str(id) for id in result.inserted_ids],
        "message": f"{len(result.inserted_ids)} تسک ایجاد شد"
    }), 201

# ✏️ به‌روزرسانی گروهی
@app.route('/tasks/bulk', methods=['PUT'])
def update_tasks_bulk():
    """
    به‌روزرسانی همزمان چندین تسک
    
    ساختار درخواست:
    [
        {
            "id": "شناسه تسک",
            "فیلدها": "مقادیر جدید"
        }
    ]
    
    مثال:
    [
        {
            "id": "665b4a6e8c1d7e12a4c3b5a8",
            "completed": true
        }
    ]
    """
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "ورودی باید یک آرایه باشد"}), 400

    operations = []
    for item in data:
        # اعتبارسنجی شناسه
        task_id = item.get('id')
        if not task_id or not ObjectId.is_valid(task_id):
            continue
        
        # ساخت عملیات به‌روزرسانی
        update_data = {}
        for field in ['title', 'description', 'completed', 'due_date', 'reminder_time']:
            if field in item:
                # تبدیل تاریخها
                if field in ['due_date', 'reminder_time'] and item[field]:
                    update_data[field] = datetime.fromisoformat(item[field])
                else:
                    update_data[field] = item[field]
        
        if update_data:
            operations.append(
                UpdateOne(
                    {'_id': ObjectId(task_id)},
                    {'$set': update_data}
                )
            )

    if not operations:
        return jsonify({"error": "هیچ عملیات معتبری یافت نشد"}), 400

    # اجرای عملیات گروهی
    result = mongo.db.tasks.bulk_write(operations)
    return jsonify({
        "matched_count": result.matched_count,
        "modified_count": result.modified_count
    }), 200

# ❌ حذف گروهی
@app.route('/tasks/bulk', methods=['DELETE'])
def delete_tasks_bulk():
    """
    حذف چندین تسک بر اساس شناسه
    
    مثال درخواست:
    DELETE /tasks/bulk
    {
        "ids": ["665b4a6e8c1d7e12a4c3b5a8"]
    }
    """
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({"error": "فیلد ids الزامی است"}), 400
    
    # اعتبارسنجی شناسه‌ها
    valid_ids = []
    for task_id in data['ids']:
        if ObjectId.is_valid(task_id):
            valid_ids.append(ObjectId(task_id))
    
    if not valid_ids:
        return jsonify({"error": "هیچ شناسه معتبری یافت نشد"}), 400

    # اجرای حذف
    result = mongo.db.tasks.delete_many({'_id': {'$in': valid_ids}})
    return jsonify({
        "deleted_count": result.deleted_count,
        "message": f"{result.deleted_count} تسک حذف شد"
    }), 200

# 🔍 جستجوی پیشرفته
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    """
    جستجوی پیشرفته با قابلیت:
    - جستجوی متنی
    - فیلتر بر اساس شناسه
    - فیلترهای ترکیبی
    
    پارامترها:
    - id: شناسه(های) تسک
    - title: جستجو در عنوان
    - description: جستجو در توضیحات
    - completed: وضعیت انجام
    
    مثال:
    GET /tasks/search?title=سالاد&completed=false
    """
    query = {}
    
    # فیلتر شناسه‌ها
    if 'id' in request.args:
        ids = request.args.getlist('id')
        valid_ids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
        if valid_ids:
            query['_id'] = {'$in': valid_ids}
    
    # جستجوی متنی
    text_fields = ['title', 'description']
    for field in text_fields:
        value = request.args.get(field)
        if value:
            query[field] = {'$regex': value, '$options': 'i'}  # جستجوی حساس به بزرگی حروف
    
    # فیلتر وضعیت انجام
    if 'completed' in request.args:
        query['completed'] = request.args.get('completed').lower() == 'true'
    
    # اجرای کوئری و فرمت‌دهی نتایج
    results = []
    for task in mongo.db.tasks.find(query):
        task['id'] = str(task.pop('_id'))
        task['created_at'] = task['created_at'].isoformat()
        if task.get('due_date'):
            task['due_date'] = task['due_date'].isoformat()
        if task.get('reminder_time'):
            task['reminder_time'] = task['reminder_time'].isoformat()
        results.append(task)
    
    return jsonify(results), 200

# 🔔 سیستم یادآوری خودکار
def reminder_checker():
    """
    بررسی دوره‌ای یادآوری‌ها هر 60 ثانیه
    """
    while True:
        now = datetime.utcnow()
        # یافتن تسکهای دارای یادآوری
        for task in mongo.db.tasks.find({'reminder_time': {'$lte': now}}):
            print(f"⏰ یادآوری: '{task['title']}' - زمان باقیمانده: {(task['due_date'] - now).total_seconds()} ثانیه")
            # حذف یادآوری پس از فعال شدن
            mongo.db.tasks.update_one(
                {'_id': task['_id']},
                {'$unset': {'reminder_time': ""}}
            )
        time.sleep(60)

# شروع سرویس یادآوری در پس‌زمینه
threading.Thread(target=reminder_checker, daemon=True).start()

# 🧮 آمار کلی
@app.route('/tasks/stats', methods=['GET'])
def get_stats():
    """
    دریافت آمار کلی تسکها
    
    پاسخ نمونه:
    {
        "total": 25,
        "completed": 10,
        "pending": 15,
        "with_due_date": 20
    }
    """
    total = mongo.db.tasks.count_documents({})
    completed = mongo.db.tasks.count_documents({'completed': True})
    with_due_date = mongo.db.tasks.count_documents({'due_date': {'$exists': True}})
    
    return jsonify({
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "with_due_date": with_due_date
    }), 200

# 🗑️ ریست دیتابیس (فقط برای محیط توسعه)
@app.route('/admin/reset', methods=['DELETE'])
def reset_database():
    """
    ریست کامل دیتابیس - فقط برای محیط توسعه
    """
    mongo.db.tasks.delete_many({})
    return jsonify({
        "message": "تمامی تسکها با موفقیت حذف شدند"
    }), 200

# اجرای سرور
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
