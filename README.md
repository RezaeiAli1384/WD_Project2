Thought for a couple of seconds


در ادامه کد «API مدیریت تسک‌ها» را از سطر اول تا آخرین سطر گام‌به‌گام شرح می‌دهم، همراه با جزئیات فنی، نکات پنهان، مثال‌های عملی برای هر بخش و اشاره به تله‌ها و بهترین شیوه‌ها.

---

## ۱. وارد کردن کتابخانه‌ها و پیکربندی اولیه

```python
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime, timedelta
import threading, time
```
📌 مسیر حذف پایگاه داده
در ابتدای کد، مسیر زیر تعریف شده است:


@app.route('/database/drop', methods=['DELETE'])
def drop_database():
    """
    DELETE /database/drop
    این روت کل دیتابیس 'todo_db' را حذف می‌کند.
    """
    mongo.cx.drop_database('todo_db')
    return jsonify({"message": "Database 'todo_db' dropped successfully"}), 200
در این بخش:
@app.route('/database/drop', methods=['DELETE']) یک مسیر HTTP تعریف می‌کند که فقط درخواست‌های DELETE را می‌پذیرد.

تابع drop_database با استفاده از mongo.cx.drop_database('todo_db') پایگاه داده‌ای به نام 'todo_db' را حذف می‌کند.

پس از حذف پایگاه داده، یک پاسخ JSON با پیام موفقیت‌آمیز بودن عملیات بازگردانده می‌شود.

⚠️ نکات مهم
استفاده از mongo.cx.drop_database('todo_db') به این معناست که کل پایگاه داده 'todo_db' و تمامی مجموعه‌ها (collections) و اسناد (documents) درون آن حذف خواهند شد.

این عملیات غیرقابل بازگشت است؛ بنابراین، باید با احتیاط استفاده شود.

مطمئن شوید که این مسیر به صورت محافظت‌شده و فقط برای کاربران مجاز در دسترس است تا از حذف ناخواسته پایگاه داده جلوگیری شود.

✅ مثال استفاده
برای حذف پایگاه داده، می‌توانید از ابزارهایی مانند curl یا Postman استفاده کنید:

curl -X DELETE http://localhost:8000/database/drop
پاسخ:

{
  "message": "Database 'todo_db' dropped successfully"
}
پس از اجرای این درخواست، پایگاه داده 'todo_db' از سرور MongoDB حذف خواهد شد.

🔒 پیشنهاد امنیتی
برای افزایش امنیت، می‌توانید اقدامات زیر را در نظر بگیرید:

افزودن احراز هویت (authentication) برای اطمینان از اینکه فقط کاربران مجاز می‌توانند این عملیات را انجام دهند.

محدود کردن دسترسی به این مسیر بر اساس نقش کاربران یا آدرس IP.

افزودن تأییدیه‌های اضافی (مانند درخواست تأیید از کاربر) قبل از انجام عملیات حذف.





1. **Flask**

   * `Flask` برای ساخت اپلیکیشن وب
   * `jsonify` برای برگرداندن پاسخ JSON
   * `request` برای دسترسی به پارامترها و بدنه درخواست
   * **مثال**:

     ```python
     @app.route('/ping')
     def ping():
         return jsonify({"pong": True}), 200
     ```

2. **flask\_pymongo**

   * ساده‌سازی ارتباط با MongoDB
   * `PyMongo(app)` خودکار URI را می‌خواند و کلاینت می‌سازد

3. **bson.objectid.ObjectId**

   * برای تبدیل رشته‌ی ID به شیء‌ی ObjectId MongoDB
   * **نکته پنهان**: اگر رشته نامعتبر باشد (`ObjectId.is_valid()`)، باعث خطا می‌شود؛ همیشه پیش از تبدیل، اعتبارسنجی کنید.

4. **pymongo.UpdateOne**

   * برای عملیات bulk write
   * هر شیء `UpdateOne(filter, update)` یک دستور به صف می‌افزاید که در `bulk_write()` اجرا می‌شود

5. **datetime, timedelta**

   * مدیریت تاریخ و زمان
   * **تله رایج**: `datetime.fromisoformat(...)` تاریخ را به منطقه زمانی محلی تبدیل می‌کند؛ برای API بهتر است همیشه UTC استفاده کنید (`datetime.utcnow()`).

6. **threading, time**

   * ایجاد یک ترد پس‌زمینه برای ارسال یادآوری‌ها
   * `time.sleep(60)` باعث می‌شود هر ۶۰ ثانیه یک‌بار حلقه اجرا شود
   * **نکته**: در پروژ‌ه‌های واقعی از task queue (مثل Celery) یا Cron بهتر است استفاده کنید تا مشکلات همزمانی و حافظه نداشته باشید.

---

## ۲. ساخت اپلیکیشن و اتصال به MongoDB

```python
app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'
mongo = PyMongo(app)
```

* **`Flask(__name__)`**: مسیرها را براساس نام ماژول تنظیم می‌کند.
* **`MONGO_URI`**:

  * آدرس دیتابیس `todo_db` روی لوکال
  * **نکته امنیتی**: در محیط واقعی بهتر است URI را از متغیر محیطی (`ENV VAR`) بخوانید و اطلاعات کاربری (username/password) را رمزنگاری کنید.
* **`mongo.db.tasks`** دسترسی به کالکشن `tasks` را فراهم می‌کند.

---

## ۳. حذف کامل دیتابیس

```python
@app.route('/database/drop', methods=['DELETE'])
def drop_database():
    """
    DELETE /database/drop
    این روت کل دیتابیس 'todo_db' را حذف می‌کند.
    """
    mongo.cx.drop_database('todo_db')
    return jsonify({"message": "Database 'todo_db' dropped successfully"}), 200
```

* **عملکرد**: پاک کردن کامل دیتابیس (تمام کالکشن‌ها)
* **مثال درخواست**:

  ```
  DELETE http://localhost:8000/database/drop
  ```
* **مثال پاسخ**:

  ```json
  {
    "message": "Database 'todo_db' dropped successfully"
  }
  ```
* **نکات**:

  * این روت در محیط عملیاتی خطرناک است؛ باید پروتکشن (authentication/authorization) داشته باشد.
  * در MongoDB شبیه‌سازی (drop) برگشت‌ناپذیر است.

---

## ۴. روت اصلی (Home)

```python
@app.route('/', methods=['GET'])
def home():
    """
    GET /
    صفحه خوش‌آمدگویی: راهنمای کار با API تسک‌ها
    """
    return jsonify({
        "message": "Welcome to the Task API! Use /tasks to list all tasks."
    }), 200
```

* **هدف**: اطلاع‌رسانی اولیه به کاربر
* **مثال پاسخ**:

  ```json
  {
    "message": "Welcome to the Task API! Use /tasks to list all tasks."
  }
  ```

---

## ۵. لیست تمام تسک‌ها با فیلتر، مرتب‌سازی و صفحه‌بندی

```python
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    q = {}
    # فیلتر وضعیت
    if 'completed' in request.args:
        q['completed'] = request.args.get('completed').lower() == 'true'
    # فیلتر تاریخ
    if 'from_date' in request.args:
        dt = datetime.fromisoformat(request.args['from_date'])
        q.setdefault('created_at', {})['$gte'] = dt
    if 'to_date' in request.args:
        dt = datetime.fromisoformat(request.args['to_date'])
        q.setdefault('created_at', {})['$lte'] = dt

    total = mongo.db.tasks.count_documents(q)
    cursor = mongo.db.tasks.find(q)

    # مرتب‌سازی
    sort_by = request.args.get('sort_by', 'created_at')
    order = -1 if request.args.get('order', 'desc') == 'desc' else 1
    cursor = cursor.sort(sort_by, order)

    # صفحه‌بندی
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    skip = (page - 1) * per_page
    cursor = cursor.skip(skip).limit(per_page)

    tasks = []
    row_num = skip + 1
    for t in cursor:
        t['_id'] = str(t['_id'])
        # محاسبه remaining_time
        if 'due_date' in t and t['due_date']:
            t['remaining_time'] = (t['due_date'] - datetime.utcnow()).total_seconds()
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
```

### ۵.۱. فیلترها

* **`completed=true|false`**
* **`from_date` و `to_date`** با فرمت `YYYY-MM-DD`
* **تله**: نپریدن بین timezoneها؛ همیشه UTC را در نظر بگیرید یا ورودی زمان را صریح کنترل کنید.

### ۵.۲. مرتب‌سازی

* **`sort_by`**: هر فیلدی در کالکشن (پیش‌فرض `created_at`)
* **`order`**: `asc` یا `desc`

### ۵.۳. صفحه‌بندی

* **`page`, `per_page`**
* **مثال به‌دست‌آوردن صفحه‌ی دوم با هر صفحه ۵ آیتم**:

  ```
  GET /tasks?page=2&per_page=5
  ```

### ۵.۴. شماره ردیف و زمان باقی‌مانده

* **`row_number`**: محاسبه با توجه به `skip`
* **`remaining_time`**: تفاضل `due_date` منهای `now`
* **نکته**: اگر `due_date` در گذشته باشد، عدد منفی برمی‌گردد.

---

## ۶. درج همزمان چندین تسک (Bulk Create)

```python
@app.route('/tasks/bulk', methods=['POST'])
def create_tasks_bulk():
    data = request.get_json(force=True)
    if not isinstance(data, list) or not data:
        return jsonify({"error": "Provide a non-empty list"}), 400

    docs = []
    for it in data:
        if 'title' not in it:
            return jsonify({"error": "Each task must have a title"}), 400
        doc = {
            'title': it['title'],
            'description': it.get('description', ''),
            'completed': bool(it.get('completed', False)),
            'created_at': datetime.utcnow(),
            'due_date': datetime.fromisoformat(it['due_date']) if it.get('due_date') else None,
            'reminder_time': datetime.fromisoformat(it['reminder_time']) if it.get('reminder_time') else None
        }
        docs.append(doc)

    res = mongo.db.tasks.insert_many(docs)
    return jsonify({"inserted_ids": [str(_id) for _id in res.inserted_ids]}), 201
```

* **ورودی**:

  ```json
  [
    {"title":"کار ۱","due_date":"2025-05-10T12:00:00"},
    {"title":"کار ۲","completed":true}
  ]
  ```
* **خروجی**:

  ```json
  {"inserted_ids":["642...","642..."]}
  ```
* **نکته**:

  * عملیات اتمیک نیست؛ اگر یکی از اسناد اشکال داشته باشد، بقیه درج می‌شوند مگر کل را در `try/except` بپیچید.
  * `force=True` باعث می‌شود حتی بدون هدر `Content-Type: application/json` نیز JSON بخواند.

---

## ۷. به‌روزرسانی همزمان چندین تسک (Bulk Update)

```python
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
            ops.append(UpdateOne({'_id': oid}, {'$set': u}))

    if not ops:
        return jsonify({"error": "No valid updates provided"}), 400

    res = mongo.db.tasks.bulk_write(ops, ordered=False)
    return jsonify({
        "matched_count": res.matched_count,
        "modified_count": res.modified_count
    }), 200
```

* **مکانیسم**:

  * برای هر آیتم یک دستور `UpdateOne` می‌سازد
  * `ordered=False` یعنی در صورت خطا ادامه می‌دهد
* **مثال ورودی**:

  ```json
  [
    {"id":"642...","completed":true},
    {"id":"643...","title":"ویرایش شده"}
  ]
  ```
* **خروجی**:

  ```json
  {"matched_count":2,"modified_count":2}
  ```
* **نکته**:

  * اگر `id` نامعتبر باشد، آن رکورد نادیده گرفته می‌شود.
  * در محیط واقعی باید خطاهای جزئی را گزارش کنید (مثلاً idهای نامعتبر).

---

## ۸. حذف همزمان چندین تسک (Bulk Delete)

```python
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
```

* **مثال ورودی**:

  ```json
  {"ids":["642...","643..."]}
  ```
* **مثال خروجی**:

  ```json
  {"deleted_count":2}
  ```

---

## ۹. جستجوی پیشرفته

```python
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    q = {}
    ids = request.args.getlist('id')
    if ids:
        oids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
        q['_id'] = {'$in': oids}

    for field in ('title', 'description'):
        v = request.args.get(field)
        if v:
            q[field] = {'$regex': v, '$options': 'i'}

    if 'created_at' in request.args:
        try:
            d = datetime.fromisoformat(request.args['created_at'])
            q['created_at'] = {'$gte': d, '$lt': d + timedelta(days=1)}
        except:
            return jsonify({"error": "created_at must be YYYY-MM-DD"}), 400

    tasks = list(mongo.db.tasks.find(q))
    for t in tasks:
        t['_id'] = str(t['_id'])
    return jsonify(tasks), 200
```

* **پارامترها**:

  * `?id=...&id=...`
  * `?title=foo` (حساس به حروف نیست)
  * `?description=bar`
  * `?created_at=2025-05-03`
* **مثال**:

  ```
  GET /tasks/search?title=خرید&created_at=2025-05-01
  ```
* **نکته**:

  * Regex‌های فول‌تکست نیستند؛ برای جستجوی پیشرفته‌تر از شاخص متن (`text index`) استفاده کنید.

---

## ۱۰. ترد پس‌زمینه برای Notification & Reminder

```python
def reminder_loop():
    while True:
        now = datetime.utcnow()
        tasks = mongo.db.tasks.find({'reminder_time': {'$ne': None}})
        for t in tasks:
            rt = t['reminder_time']
            if now >= rt:
                print(f"🔔 Reminder: Task '{t['title']}' is due!")
                mongo.db.tasks.update_one(
                    {'_id': t['_id']},
                    {'$unset': {'reminder_time': ""}}
                )
        time.sleep(60)

threading.Thread(target=reminder_loop, daemon=True).start()
```

* **اجرا**: با `daemon=True` ترد وقتی می‌میرد که اپ خاتمه یابد.
* **عملکرد**:

  1. هر دقیقه لیست تسک‌هایی با `reminder_time` غیرخالی را واکشی می‌کند.
  2. اگر زمان حال بیشتر یا مساوی `reminder_time` باشد، اعلان می‌دهد (اینجا در کنسول)
  3. فیلد `reminder_time` را پاک می‌کند تا دیگر مجدد نشود.
* **تله‌ها**:

  * استفاده از `print` مناسب محیط توسعه است؛ در production باید لاگ یا سرویس ارسال ایمیل/پیامک داشته باشید.
  * اگر تعداد تسک‌ها زیاد باشد، واکشی همه در هر دقیقه ناکارآمد است؛ بهتر است کوئری محدود (`$lte: now`) و ایندکس روی `reminder_time`.

---

## ۱۱. شمارش تسک‌ها و محاسبه Remaining

```python
@app.route('/tasks/counts', methods=['GET'])
def count_tasks():
    total = mongo.db.tasks.count_documents({})
    done = mongo.db.tasks.count_documents({'completed': True})
    left = total - done
    return jsonify({
        "total_tasks": total,
        "completed_tasks": done,
        "remaining_tasks": left
    }), 200
```

* **خروجی**:

  ```json
  {
    "total_tasks": 42,
    "completed_tasks": 17,
    "remaining_tasks": 25
  }
  ```

---

## ۱۲. اجرای سرور

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
```

* **`host='0.0.0.0'`**: پذیرش درخواست از همه آدرس‌های شبکه
* **`port=8000`**: پورت اجرا
* **`debug=True`**:

  * **بارگذاری مجدد خودکار**
  * نمایش صفحه خطا با traceback
  * **نکته امنیتی**: هرگز در production روی `debug=True` نگذارید.

---

## جمع‌بندی نکات کلیدی و توصیه‌ها

1. **UTC vs Local Time**

   * برای یکنواختی از `datetime.utcnow()` و ذخیره زمان‌ها با منطقه UTC استفاده کنید.
2. **اعتبارسنجی ورودی**

   * همیشه `ObjectId.is_valid()` را چک کنید.
   * روی پارامترهای رشته‌ای (`from_date`، `to_date`) `try/except` بگذارید.
3. **امنیت**

   * APIهای حذف و drop باید پشت احراز هویت/مجوز باشند.
   * از متغیر محیطی برای URI و credentials استفاده کنید.
4. **بهینه‌سازی**

   * برای فیلدهایی که مرتب‌سازی یا جستجو می‌شوند ایندکس‌گذاری کنید.
   * در عملیات bulk از ordered=False برای کارایی بهتر بهره ببرید.
5. **Production-Ready**

   * به جای ترد ساده، از صف پیام (RabbitMQ/Celery) استفاده کنید.
   * لاگ مناسب جای `print` بگذارید.
   * خطاها و استثناها را مدیریت و به کلاینت پاسخ مناسب دهید.

با رعایت این توضیحات و مثال‌ها، شما اکنون درک کاملی از جزییات و ریزترین نکات این API دارید. اگر سوال یا نکته‌ی خاصی داشتید، خوشحال می‌شوم بیشتر توضیح دهم!
