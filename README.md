1. 📦 وارد کردن کتابخانه‌ها
python
Copy
Edit
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime, timedelta
import threading, time
توضیح:

Flask: فریم‌ورک وب سبک برای ساخت APIها و برنامه‌های وب.

jsonify: برای تبدیل داده‌های پایتون به JSON جهت ارسال در پاسخ‌ها.

request: برای دسترسی به داده‌های درخواست HTTP (مانند پارامترها و بدنه).

PyMongo: برای اتصال و تعامل با MongoDB در برنامه‌های Flask.

ObjectId: برای مدیریت شناسه‌های یکتا در MongoDB.

UpdateOne: برای انجام عملیات به‌روزرسانی در MongoDB.

datetime, timedelta: برای مدیریت تاریخ و زمان.

threading, time: برای اجرای وظایف در پس‌زمینه و کنترل زمان‌بندی.

مثال:

اگر بخواهید یک تسک با تاریخ سررسید خاصی ایجاد کنید، از datetime برای تعیین آن استفاده می‌کنید.

2. ⚙️ پیکربندی برنامه و اتصال به پایگاه داده
python
Copy
Edit
app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'
mongo = PyMongo(app)
توضیح:

یک نمونه از برنامه Flask ایجاد می‌شود.

URI اتصال به پایگاه داده MongoDB مشخص می‌شود.

اتصال به پایگاه داده با استفاده از PyMongo برقرار می‌شود.

مثال:

اگر پایگاه داده شما در سرور دیگری باشد، URI را به‌صورت mongodb://username:password@host:port/dbname تنظیم می‌کنید.

3. 🗑️ حذف کامل پایگاه داده
python
Copy
Edit
@app.route('/database/drop', methods=['DELETE'])
def drop_database():
    mongo.cx.drop_database('todo_db')
    return jsonify({"message": "Database 'todo_db' dropped successfully"}), 200
توضیح:

این مسیر با متد DELETE، کل پایگاه داده todo_db را حذف می‌کند.

مثال:

ارسال یک درخواست DELETE به /database/drop باعث حذف کامل تمام داده‌ها می‌شود.

4. 🏠 صفحه اصلی (Home)
python
Copy
Edit
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Welcome to the Task API! Use /tasks to list, /tasks/bulk for bulk operations, /tasks/search for search, /tasks/counts for counts."
    }), 200
توضیح:

این مسیر پیام خوش‌آمدگویی و راهنمای استفاده از API را نمایش می‌دهد.

مثال:

درخواست GET به / اطلاعات کلی در مورد API ارائه می‌دهد.

5. 📋 لیست تمام تسک‌ها با فیلتر، مرتب‌سازی و صفحه‌بندی
python
Copy
Edit
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    # فیلترها
    q = {}
    if 'completed' in request.args:
        q['completed'] = request.args.get('completed').lower() == 'true'
    if 'from_date' in request.args:
        dt = datetime.fromisoformat(request.args['from_date'])
        q.setdefault('created_at', {})['$gte'] = dt
    if 'to_date' in request.args:
        dt = datetime.fromisoformat(request.args['to_date'])
        q.setdefault('created_at', {})['$lte'] = dt

    # مرتب‌سازی
    sort_by = request.args.get('sort_by', 'created_at')
    order = -1 if request.args.get('order', 'desc') == 'desc' else 1
    cursor = mongo.db.tasks.find(q).sort(sort_by, order)

    # صفحه‌بندی
    page = max(int(request.args.get('page', 1)), 1)
    per_page = max(int(request.args.get('per_page', 10)), 1)
    skip = (page - 1) * per_page
    cursor = cursor.skip(skip).limit(per_page)

    # جمع‌آوری نتایج
    tasks = []
    row_num = skip + 1
    for t in cursor:
        t['_id'] = str(t['_id'])
        t['created_at'] = t['created_at'].isoformat()
        t['due_date'] = t.get('due_date').isoformat() if t.get('due_date') else None
        t['reminder_time'] = t.get('reminder_time').isoformat() if t.get('reminder_time') else None
        if t.get('due_date'):
            due_dt = datetime.fromisoformat(t['due_date'])
            t['remaining_time'] = max((due_dt - datetime.utcnow()).total_seconds(), 0)
        else:
            t['remaining_time'] = None
        t['row_number'] = row_num
        row_num += 1
        tasks.append(t)

    return jsonify({
        "total": mongo.db.tasks.count_documents(q),
        "page": page,
        "per_page": per_page,
        "tasks": tasks
    }), 200
توضیح:

امکان فیلتر بر اساس وضعیت تکمیل، تاریخ ایجاد، مرتب‌سازی بر اساس فیلدهای مختلف و صفحه‌بندی فراهم شده است.

برای هر تسک، زمان باقی‌مانده تا سررسید محاسبه می‌شود.

مثال:

درخواست GET به /tasks?completed=false&sort_by=due_date&order=asc&page=2&per_page=5 لیست تسک‌های ناتمام را بر اساس تاریخ سررسید به‌صورت صعودی در صفحه دوم با ۵ تسک در هر صفحه نمایش می‌دهد.

6. ➕ درج همزمان چندین تسک
python
Copy
Edit
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
توضیح:

امکان درج چندین تسک به‌صورت همزمان با استفاده از یک لیست از تسک‌ها فراهم شده است.

مثال:

ارسال یک درخواست POST به /tasks/bulk با بدنه:

json
Copy
Edit
[
  {
    "title": "خرید شیر",
    "description": "شیر کم‌چرب",
    "due_date": "2025-05-10T12:00:00",
    "reminder_time": "2025-05-10T09:00:00"
  },
  {
    "title": "مطالعه کتاب",
    "description": "فصل اول",
    "due_date": "2025-05-11T18:00:00"
  }
]
دو تسک جدید را به پایگاه داده اضافه می‌کند.

7. ✏️ به‌روزرسانی همزمان چندین تسک
python
Copy
Edit
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
        oid = ObjectId(tid)
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
            ops.append(UpdateOne({'_id': oid}, {'
::contentReference[oaicite:114]{index=114}
