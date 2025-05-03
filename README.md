1. Import کتابخانه ها و تنظیمات اولیه
python

from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime, timedelta
import threading
import time

    توضیح:

        Flask برای ساخت وب اپلیکیشن.

        jsonify برای تبدیل دیکشنریهای پایتون به پاسخهای JSON.

        request برای دسترسی به دادههای ارسالی در درخواستها.

        PyMongo برای ادغام Flask با MongoDB.

        ObjectId برای کار با شناسههای منحصر به فرد MongoDB.

        UpdateOne برای عملیات bulk update در MongoDB.

        datetime و timedelta برای مدیریت زمان (مثلاً زمان ایجاد تسک).

        threading و time برای اجرای تایمر بررسی ریمایندرها در پسزمینه.

2. ایجاد برنامه Flask و اتصال به MongoDB
python

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'
mongo = PyMongo(app)

    توضیح:

        app شیء اصلی Flask است.

        MONGO_URI آدرس دیتابیس MongoDB را مشخص میکند (todo_db نام دیتابیس است).

        mongo شیئی از PyMongo برای تعامل با دیتابیس.

    نکته: اگر دیتابیس وجود نداشته باشد، MongoDB به طور خودکار آن را ایجاد میکند.

    مثال: اگر دیتابیس در حال اجرا نباشد، خطای ConnectionFailure رخ میدهد.

3. روت اصلی (صفحه خوشآمدگویی)
python

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Task API! Use /tasks to see all tasks."}), 200

    توضیح:

        با دسترسی به آدرس اصلی (/)، پیام خوشآمدگویی نمایش داده میشود.

        کد وضعیت 200 به معنای موفقیتآمیز بودن درخواست است.

    مثال:
    

curl http://localhost:8000/

خروجی:
json

    {"message": "Welcome to the Task API! Use /tasks to see all tasks."}

4. دریافت همه تسکها (GET /tasks)
python

@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    tasks = list(mongo.db.tasks.find())
    for task in tasks:
        task['_id'] = str(task['_id'])
    return jsonify(tasks), 200

    توضیح:

        همه داکیومنتها از collection tasks را میخواند.

        ObjectId به رشته تبدیل میشود چون JSON از آن پشتیبانی نمیکند.

    نکته: اگر collection خالی باشد، لیست خالی برگردانده میشود.

    مثال:
    

curl http://localhost:8000/tasks

خروجی:
json

    [
      {
        "_id": "60a1b2c3d4e5f6a1b2c3d4e5",
        "title": "Buy milk",
        "completed": false
      }
    ]

5. ایجاد چندین تسک همزمان (POST /tasks/bulk)
python

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
            'reminder_time': item.get('reminder_time')
        })
    result = mongo.db.tasks.insert_many(docs)
    return jsonify({"inserted_ids": [str(_id) for _id in result.inserted_ids]}), 201

    توضیح:

        force=True در get_json() حتی اگر کلاینت هدر Content-Type را تنظیم نکرده باشد، داده را به عنوان JSON پردازش میکند.

        هر تسک باید حتماً title داشته باشد.

        reminder_time اختیاری است (مثلاً 2023-05-20T15:30:00).

        created_at زمان فعلی را به وقت UTC ذخیره میکند.

    نکته: bool(item.get('completed', False)) حتی اگر مقدار completed رشته یا عدد باشد، به boolean تبدیل میشود.

    مثال:
    

curl -X POST -H "Content-Type: application/json" -d '[{"title": "Task 1"}, {"title": "Task 2", "completed": "true"}]' http://localhost:8000/tasks/bulk

خروجی:
json

    {"inserted_ids": ["60a1b2c3d4e5f6a1b2c3d4e5", "60a1b2c3d4e5f6a1b2c3d4e6"]}

6. بهروزرسانی چندین تسک همزمان (PUT /tasks/bulk)
python

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

    توضیح:

        هر آیتم در لیست داده باید id معتبر (ObjectId) داشته باشد.

        ordered=False باعث میشود عملیاتها به ترتیب اجرا نشوند و خطا در یکی، بقیه را متوقف نکند.

        $set در MongoDB فقط فیلدهای مشخص شده را بهروز میکند.

    نکته: اگر reminder_time به null تنظیم شود، حذف نمیشود. برای حذف باید از $unset استفاده کرد.

    مثال:
    

curl -X PUT -H "Content-Type: application/json" -d '[{"id": "60a1b2c3d4e5f6a1b2c3d4e5", "title": "New Title"}, {"id": "invalid_id", "completed": true}]' http://localhost:8000/tasks/bulk

خروجی:
json

    {"matched_count": 1, "modified_count": 1}

7. حذف چندین تسک همزمان (DELETE /tasks/bulk)
python

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

    توضیح:

        ids باید لیستی از شناسههای معتبر باشد.

        $in در MongoDB برای تطابق هر یک از شناسهها استفاده میشود.

    نکته: شناسههای نامعتبر نادیده گرفته میشوند.

    مثال:
    

curl -X DELETE -H "Content-Type: application/json" -d '{"ids": ["60a1b2c3d4e5f6a1b2c3d4e5", "invalid_id"]}' http://localhost:8000/tasks/bulk

خروجی:
json

    {"deleted_count": 1}

8. جستجوی تسکها (GET /tasks/search)
python

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

    توضیح:

        $regex برای جستجوی متن با حساسیت به حروف (با i برای بیحساسی به حروف).

        created_at باید به فرمت YYYY-MM-DD باشد و تمام تسکهای آن روز را برمیگرداند.

    مثال:
    

curl "http://localhost:8000/tasks/search?title=work&created_at=2023-05-20"

خروجی:
json

    [{"_id": "60a1b2c3d4e5f6a1b2c3d4e5", "title": "Work on project", "created_at": "2023-05-20T00:00:00"}]

9. تابع بررسی ریمایندرها (پسزمینه)
python

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
                mongo.db.tasks.update_one({'_id': task['_id']}, {'$unset': {'reminder_time': ""}})
        time.sleep(30)

    توضیح:

        هر ۳۰ ثانیه یکبار تسکهایی که reminder_time دارند را بررسی میکند.

        اگر زمان ریمایندر فرا رسیده باشد، پیام چاپ شده و reminder_time حذف میشود.

    نکته: فرمت reminder_time باید دقیقاً %Y-%m-%dT%H:%M:%S باشد (مثلاً 2023-05-20T15:30:00).

    مثال: اگر reminder_time یک تسک برابر با زمان فعلی باشد، در کنسول سرور پیام نمایش داده میشود.

10. شمارش تسکها (GET /tasks/count)
python

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

    توضیح:

        تعداد کل، تکمیل شده و نشده تسکها را برمیگرداند.

    مثال:
    

curl http://localhost:8000/tasks/count

خروجی:
json

    {"total_tasks": 5, "completed_tasks": 2, "incomplete_tasks": 3}

11. اجرای تابع چکر ریمایندر در پسزمینه
python

threading.Thread(target=check_reminders, daemon=True).start()

    توضیح:

        تابع check_reminders در یک thread جداگانه به عنوان دیمن (پسزمینه) اجرا میشود.

        daemon=True باعث میشود با بسته شدن برنامه اصلی، این thread نیز پایان یابد.

12. اجرای برنامه
python

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

    توضیح:

        سرور روی همه آدرسهای شبکه (0.0.0.0) و پورت 8000 اجرا میشود.

        debug=True برای نمایش خطاها در مرورگر (فقط در محیط توسعه).

نکات کلی و امنیتی

    اعتبارسنجی دادهها:

        برخی اعتبارسنجیها مانند بررسی وجود title انجام شده، اما برای فیلدهایی مانند reminder_time اعتبارسنجی فرمت وجود ندارد.

    امنیت:

        استفاده از force=True در get_json() ممکن است خطراتی داشته باشد اگر کلاینت داده غیر JSON ارسال کند.

        عدم وجود احراز هویت (Authentication) برای دسترسی به API.

    خطاها:

        برخی خطاها (مانند duplicate key) هندل نشدهاند.

    کارایی:

        استفاده از bulk_write برای عملیاتهای حجیم کارایی را بهبود میبخشد.

مثال جامع

سناریو: ایجاد تسک، تنظیم ریمایندر، آپدیت و حذف.

    ایجاد تسک:
    

curl -X POST -H "Content-Type: application/json" -d '[{"title": "Finish report", "reminder_time": "2023-05-20T15:30:00"}]' http://localhost:8000/tasks/bulk

بررسی ریمایندر:

    در زمان مشخص شده، پیام در کنسول چاپ میشود و reminder_time حذف میگردد.

آپدیت تسک:


curl -X PUT -H "Content-Type: application/json" -d '[{"id": "60a1b2c3d4e5f6a1b2c3d4e5", "completed": true}]' http://localhost:8000/tasks/bulk

حذف تسک:


curl -X DELETE -H "Content-Type: application/json" -d '{"ids": ["60a1b2c3d4e5f6a1b2c3d4e5"]}' http://localhost:8000/tasks/bulk
