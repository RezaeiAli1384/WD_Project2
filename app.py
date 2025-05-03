# وارد کردن ماژول‌های مورد نیاز
# Flask برای ساخت وب‌اپلیکیشن، jsonify برای تبدیل خروجی به JSON، request برای دریافت داده‌های ورودی
from flask import Flask, jsonify, request  
# Flask-PyMongo برای راحتی کار با MongoDB در Flask
from flask_pymongo import PyMongo            
# ObjectId برای تبدیل رشته به شناسهٔ MongoDB و برعکس
from bson.objectid import ObjectId             
# UpdateOne برای انجام عملیات گروهی و بهینه در به‌روزرسانی bulk
from pymongo import UpdateOne                  
# datetime برای کار با تاریخ، timedelta برای بازه‌های زمانی
from datetime import datetime, timedelta       
# threading برای راه‌اندازی ترد پس‌زمینه، time برای خواباندن ترد
import threading, time                         

# ایجاد نمونهٔ Flask با نام ماژول فعلی
app = Flask(__name__)                          
# تنظیم URI برای اتصال به MongoDB محلی با دیتابیس todo_db
app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'  
# اتصال Flask به MongoDB
mongo = PyMongo(app)                            

# 🏠 صفحهٔ اصلی (Home)
@app.route('/', methods=['GET'])  # مسیر GET /
def home():  
    # مثال درخواست:
    # GET http://localhost:8000/
    return jsonify({
        "message": (
            # پیام خوش‌آمدگویی و معرفی مسیرهای اصلی
            "Welcome to the Task API! "
            "Use /tasks to list or add tasks, "
            "/tasks/bulk for bulk operations, "
            "and /tasks/search for advanced search."
        )
    }), 200  # کد وضعیت 200: موفقیت

# ✅ ایجاد یک تسک تکی (POST /tasks)
@app.route('/tasks', methods=['POST'])  # مسیر POST /tasks
def create_single_task():  
    # دریافت JSON ورودی از درخواست
    data = request.get_json(force=True)
    # مثال دادهٔ ورودی:
    # {
    #   "title": "خرید میوه",
    #   "description": "سیب و موز",
    #   "due_date": "2025-05-10T12:00:00",
    #   "reminder_time": "2025-05-10T09:00:00"
    # }
    
    # گرفتن عنوان تسک و اعتبارسنجی وجود آن
    title = data.get('title')
    if not title:
        # اگر عنوان ارسال نشده باشد، خطای 400 برگردانده می‌شود
        return jsonify({"error": "title is required"}), 400

    # ساخت داکیومنت تسک برای ذخیره در MongoDB
    task = {
        'title': title,  # عنوان تسک
        'description': data.get('description', ''),  # توضیح اختیاری
        'completed': bool(data.get('completed', False)),  # وضعیت تکمیل (پیش‌فرض False)
        'created_at': datetime.utcnow(),  # زمان ایجاد به فرمت UTC
        # اگر due_date ارسال شده، تبدیل رشته ISO به datetime، در غیر این صورت None
        'due_date': datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        # مشابه due_date برای reminder_time
        'reminder_time': datetime.fromisoformat(data['reminder_time']) if data.get('reminder_time') else None
    }
    # درج تسک در کالکشن tasks و دریافت شناسهٔ جدید
    inserted_id = mongo.db.tasks.insert_one(task).inserted_id
    # برگرداندن شناسه به‌صورت رشته‌ای و کد وضعیت 201: ایجاد شده
    return jsonify({"inserted_id": str(inserted_id)}), 201

# 📋 لیست تسک‌ها با فیلتر، مرتب‌سازی، صفحه‌بندی و شمارهٔ ردیف (GET /tasks)
@app.route('/tasks', methods=['GET'])  # مسیر GET /tasks
def get_all_tasks():
    q = {}  # دیکشنری کوئری برای MongoDB
    # مثال درخواست:
    # GET /tasks?completed=false&from_date=2025-05-01&to_date=2025-05-03&sort_by=due_date&order=asc&page=2

    # فیلتر بر اساس وضعیت تکمیل
    if 'completed' in request.args:
        q['completed'] = request.args.get('completed').lower() == 'true'
    # فیلتر بازهٔ تاریخ ایجاد: از تاریخ start تا تاریخ end
    if 'from_date' in request.args:
        try:
            dt_from = datetime.fromisoformat(request.args['from_date'])
            q.setdefault('created_at', {})['$gte'] = dt_from
        except ValueError:
            return jsonify({"error": "from_date must be YYYY-MM-DD"}), 400
    if 'to_date' in request.args:
        try:
            dt_to = datetime.fromisoformat(request.args['to_date'])
            q.setdefault('created_at', {})['$lte'] = dt_to + timedelta(days=1) - timedelta(seconds=1)
        except ValueError:
            return jsonify({"error": "to_date must be YYYY-MM-DD"}), 400

    # شمارش کل مستندات مطابق کوئری (برای UI)
    total = mongo.db.tasks.count_documents(q)
    # دریافت پارامترهای مرتب‌سازی
    sort_by = request.args.get('sort_by', 'created_at')
    order = -1 if request.args.get('order', 'desc') == 'desc' else 1

    # صفحه‌بندی: page و per_page
    page = max(int(request.args.get('page', 1)), 1)
    per_page = max(int(request.args.get('per_page', 10)), 1)
    skip = (page - 1) * per_page

    # اجرای کوئری با فیلتر، مرتب‌سازی، اسکیپ و لیمیت
    cursor = mongo.db.tasks.find(q).sort(sort_by, order).skip(skip).limit(per_page)

    tasks = []
    row_num = skip + 1  # شمارهٔ شروع ردیف
    for t in cursor:
        # تبدیل ObjectId به رشته در کلید id و حذف _id
        id_str = str(t['_id'])
        # تبدیل فیلدهای تاریخ به رشته ISO
        created = t['created_at'].isoformat()
        due = t.get('due_date').isoformat() if t.get('due_date') else None
        rem = t.get('reminder_time').isoformat() if t.get('reminder_time') else None
        # محاسبهٔ remaining_time به ثانیه و جلوگیری از منفی بودن
        if due:
            delta = (datetime.fromisoformat(due) - datetime.utcnow()).total_seconds()
            remaining = max(delta, 0)
        else:
            remaining = None
        # ساخت دیکشنری جدید با ترتیب id در ابتدا
        new_t = {
            'id': id_str,
            'title': t['title'],
            'description': t.get('description', ''),
            'completed': t.get('completed', False),
            'created_at': created,
            'due_date': due,
            'reminder_time': rem,
            'remaining_time': remaining,
            'row_number': row_num
        }
        row_num += 1  # افزایش شماره ردیف
        tasks.append(new_t)

    return jsonify({
        "total": total,      # تعداد کل رکوردها
        "page": page,        # صفحهٔ فعلی
        "per_page": per_page,# تعداد در هر صفحه
        "tasks": tasks       # لیست تسک‌ها
    }), 200  # کد وضعیت 200

# ➕ درج گروهی تسک‌ها (POST /tasks/bulk)
@app.route('/tasks/bulk', methods=['POST'])
def create_tasks_bulk():
    # دریافت ورودی JSON به‌صورت لیست
    data = request.get_json(force=True)
    # مثال:
    # [
    #   {"title":"مطالعه کتاب","due_date":"2025-05-07T20:00:00"},
    #   {"title":"نوشتن گزارش","completed":false}
    # ]
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
    # مثال پاسخ:
    # {"inserted_ids":["642...","642..."]}
    return jsonify({"inserted_ids": [str(_id) for _id in res.inserted_ids]}), 201

# ✏️ به‌روزرسانی گروهی تسک‌ها (PUT /tasks/bulk)
@app.route('/tasks/bulk', methods=['PUT'])
def update_tasks_bulk():
    # دریافت لیست آپدیت‌ها از کاربر
    data = request.get_json(force=True)
    # مثال:
    # [
    #   {"id":"642...","completed":true},
    #   {"id":"642...","due_date":"2025-05-08T15:00:00"}
    # ]
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Provide a non-empty list"}), 400
    ops = []
    for it in data:
        tid = it.get('id')
        if not tid or not ObjectId.is_valid(tid):
            continue
        u = {}
        # بررسی هر فیلد برای به‌روزرسانی
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
    # مثال پاسخ:
    # {"matched_count":2,"modified_count":2}
    return jsonify({
        "matched_count": res.matched_count,
        "modified_count": res.modified_count
    }), 200

# ❌ حذف گروهی تسک‌ها (DELETE /tasks/bulk)
@app.route('/tasks/bulk', methods=['DELETE'])
def delete_tasks_bulk():
    # ورودی باید دیکشنری با کلید ids باشد
    data = request.get_json(force=True)
    ids = data.get('ids') if isinstance(data, dict) else None
    # مثال:
    # {"ids":["642...","642..."]}
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "Provide a list of ids"}), 400
    valid_ids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
    if not valid_ids:
        return jsonify({"error": "No valid IDs provided"}), 400
    res = mongo.db.tasks.delete_many({'_id': {'$in': valid_ids}})
    # مثال پاسخ:
    # {"deleted_count":2}
    return jsonify({"deleted_count": res.deleted_count}), 200

# 🔍 جستجوی پیشرفته با فیلترهای متعدد (GET /tasks/search)
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    q = {}
    # فیلتر بر اساس لیست ID: ?id=...&id=...
    ids = request.args.getlist('id')
    if ids:
        oids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
        if oids:
            q['_id'] = {'$in': oids}
    # جستجوی متنی در title و description به‌صورت regex غیرحساس به بزرگ/کوچک
    for field in ('title', 'description'):
        v = request.args.get(field)
        if v:
            q[field] = {'$regex': v, '$options': 'i'}
    # فیلتر تکمیل‌شده یا نشده
    if 'completed' in request.args:
        q['completed'] = request.args.get('completed').lower() == 'true'
    # فیلتر بازهٔ تاریخ
    if 'from_date' in request.args:
        try:
            d1 = datetime.fromisoformat(request.args['from_date'])
            q.setdefault('created_at', {})['$gte'] = d1
        except ValueError:
            return jsonify({"error": "from_date must be YYYY-MM-DD"}), 400
    if 'to_date' in request.args:
        try:
            d2 = datetime.fromisoformat(request.args['to_date'])
            q.setdefault('created_at', {})['$lte'] = d2 + timedelta(days=1) - timedelta(seconds=1)
        except ValueError:
            return jsonify({"error": "to_date must be YYYY-MM-DD"}), 400

    tasks = []
    for t in mongo.db.tasks.find(q):
        # ابتدا id سپس سایر فیلدها
        new_t = {'id': str(t['_id'])}
        new_t.update({
            'title': t['title'],
            'description': t.get('description', ''),
            'completed': t.get('completed', False),
            'created_at': t['created_at'].isoformat(),
            **({'due_date': t['due_date'].isoformat()} if t.get('due_date') else {'due_date': None}),
            **({'reminder_time': t['reminder_time'].isoformat()} if t.get('reminder_time') else {'reminder_time': None})
        })
        tasks.append(new_t)
    # مثال درخواست:
    # GET /tasks/search?title=گزارش&from_date=2025-05-02
    return jsonify(tasks), 200

# 🔔 یادآور پس‌زمینه
def reminder_loop():
    # اجرای مداوم هر 60 ثانیه
    while True:
        now = datetime.utcnow()
        # جستجوی تسک‌هایی که reminder_time دارند
        for t in mongo.db.tasks.find({'reminder_time': {'$ne': None}}):
            if now >= t['reminder_time']:
                # چاپ پیام در کنسول
                print(f"🔔 Reminder: Task '{t['title']}' is due!")
                # حذف فیلد reminder_time تا دوباره اعلان نشود
                mongo.db.tasks.update_one({'_id': t['_id']}, {'$unset': {'reminder_time': ""}})
        time.sleep(60)  # خواب 60 ثانیه
# راه‌اندازی ترد پس‌زمینه به‌صورت daemon
threading.Thread(target=reminder_loop, daemon=True).start()

# 🧮 شمارش تسک‌ها (GET /tasks/counts)
@app.route('/tasks/counts', methods=['GET'])
def count_tasks():
    # شمارش کل تسک‌ها
    total = mongo.db.tasks.count_documents({})
    # شمارش تسک‌های تکمیل‌شده
    completed = mongo.db.tasks.count_documents({'completed': True})
    # مثال درخواست: GET /tasks/counts
    return jsonify({
        "total_tasks": total,
        "completed_tasks": completed,
        "remaining_tasks": total - completed
    }), 200

# 🗑️ حذف کامل دیتابیس (DELETE /database/drop)
@app.route('/database/drop', methods=['DELETE'])
def drop_database():
    # حذف کل دیتابیس todo_db (فقط در محیط تست)
    mongo.cx.drop_database('todo_db')
    return jsonify({"message": "Database 'todo_db' dropped successfully"}), 200

# 🚀 اجرای سرور
if __name__ == '__main__':
    # host=0.0.0.0 برای دسترسی از بیرون، port=8000، debug=True برای توسعه
    app.run(host='0.0.0.0', port=8000, debug=True)
