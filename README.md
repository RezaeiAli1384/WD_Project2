Thought for a couple of seconds


در ادامه خط‌به‌خط و بخش‌به‌بخش، تمام کد «اپلیکیشن Flask با MongoDB» را تشریح می‌کنم؛ از اولین تا آخرین خط. در هر بخش:

* **شرح دقیق** معنای هر دستور و دلیل استفاده
* **نکات ریز** و ممکنِ مغفول
* **مثال عملی** برای درک بهتر کاربرد

> **نکتهٔ کلی پیش از شروع:**
>
> * این اپلیکیشن یک RESTful API ساده برای مدیریت تسک‌ها (وظایف) است.
> * از Flask برای وب‌سرور، از flask\_pymongo برای کار با MongoDB، و از threading برای یادآور پس‌زمینه استفاده می‌کند.

---

## 1. وارد کردن کتابخانه‌ها و پیکربندی اولیه

```python
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime, timedelta
import threading, time
```

1. `from flask import Flask, jsonify, request`

   * **Flask**: کلاس اصلی برای ایجاد اپلیکیشن.
   * **jsonify**: تابعی که دیکشنری پایتون را به JSON تبدیل می‌کند و هدر `Content-Type: application/json` می‌فرستد.

     * *نکته*: اگر مستقیم از `json.dumps` استفاده کنید، هدر به‌درستی تنظیم نمی‌شود.
   * **request**: شی تبدیل‌شدهٔ درخواست کاربر، برای خواندن پارامترها و body.
   * **مثال**: در یک endpoint `POST /tasks`، با `request.get_json()` می‌توانید داده‌های JSON ارسالی را بگیرید.

2. `from flask_pymongo import PyMongo`

   * افزونه‌ای که اتصال به MongoDB را در Flask ساده می‌کند.
   * **نکته**: این flask\_pymongo از `pymongo` زیرِ کاپوت استفاده می‌کند اما مدیریت کانفیگ دارد.

3. `from bson.objectid import ObjectId`

   * برای تبدیل رشته‌های ۲۴ کاراکتری MongoDB به شیء ObjectId.
   * **چرا لازم است**: وقتی از URL یا پارامترها ID دریافت می‌کنیم، باید آن را به ObjectId تبدیل کنیم تا در کوئری‌ها استفاده شود.

4. `from pymongo import UpdateOne`

   * برای انجام Bulk write (عملیات گروهی) به صورت atomically و بهینه.
   * **مثال**: وقتی چند تسک را در یک درخواست PUT به‌روز می‌کنیم، با لیستی از `UpdateOne` سرعت و کارایی بالاتر می‌رود.

5. `from datetime import datetime, timedelta`

   * ابزار کار با تاریخ و زمان.
   * `datetime.utcnow()` زمان فعلی به UTC را می‌دهد.
   * `timedelta(days=1)` برای محاسبه بازهٔ یک روز استفاده می‌شود.

6. `import threading, time`

   * برای راه‌اندازی یک ترد پس‌زمینه که وظیفهٔ ارسال یادآور (Reminder) را بر عهده دارد.
   * `time.sleep(60)` باعث می‌شود هر ۶۰ ثانیه یک‌بار چرخه تکرار شود.

---

## 2. ساخت اپلیکیشن و اتصال به MongoDB

```python
app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'
mongo = PyMongo(app)
```

1. `app = Flask(__name__)`

   * یک نمونهٔ Flask می‌سازد. پارامتر `__name__` کمک می‌کند Flask مسیر فایل‌ها (مثل قالب‌ها و استاتیک) را بیابد.

2. `app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_db'`

   * آدرس دیتابیس MongoDB محلی با نام `todo_db`.
   * **نکته**: اگر رمز عبور یا یوزر داشتید، در URI می‌توانستید اضافه کنید:

     ```
     mongodb://user:pass@host:port/todo_db?authSource=admin
     ```

3. `mongo = PyMongo(app)`

   * شیء متصل به MongoDB که می‌توانید با `mongo.db` به کالکشن‌ها دسترسی داشته باشید.
   * **مثال**: `mongo.db.tasks.find({})` برای خواندن تمام تسک‌ها.

---

## 3. Home Route – صفحهٔ خوش‌آمدگویی

```python
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Welcome to the Task API! Use /tasks to list or add tasks, /tasks/bulk for bulk operations, and /tasks/search for advanced search."
    }), 200
```

* **@app.route('/', methods=\['GET'])**

  * دکوریتور Flask برای تعریف URL.
  * `/` ریشهٔ وب‌سایت است.
  * `methods=['GET']` مشخص می‌کند فقط درخواست‌های GET را قبول کند.

* **def home(): …**

  * تابع handler که وقتی کاربر `GET /` می‌زند اجرا می‌شود.

* **return jsonify(...), 200**

  * بدنهٔ پاسخ JSON است و ۲۰۰ کد وضعیت موفق را می‌فرستد.

* **مثال**:

  ```
  GET http://localhost:8000/
  Response:
  {
    "message": "Welcome to the Task API! …"
  }
  ```

---

## 4. ایجاد یک تسک تکی (POST /tasks)

```python
@app.route('/tasks', methods=['POST'])
def create_single_task():
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
```

### گام‌به‌گام

1. **دکوریتور و متد**

   * `POST /tasks` برای ایجاد یک مورد جدید.

2. **دریافت داده‌ها**

   * `data = request.get_json(force=True)`

     * `force=True` تضمین می‌کند حتی اگر هدرها نادرست باشند، JSON خوانده شود.
     * *نکته*: معمولاً بهتر است `force=False` و چک کردن `Content-Type` با `request.is_json`.

3. **اعتبارسنجی عنوان**

   * `if not title: return … 400`

     * اگر عنوان نیامده باشد، ۴۰۰ (Bad Request) بازمی‌گردد.

4. **ساخت داکیومنت MongoDB**

   * `created_at`: زمان فعلی UTC
   * `due_date` و `reminder_time`:

     * اگر ارسال شده باشند، با `fromisoformat` رشته ISO8601 به `datetime` تبدیل می‌شوند.
     * وگرنه `None`.

5. **درج در پایگاه**

   * `insert_one(task).inserted_id`

     * شناسهٔ تازه‌ساخته شده (ObjectId) برمی‌گردد.
   * پاسخ `201 Created` به همراه `inserted_id`.

### مثال

```bash
POST /tasks
Content-Type: application/json

{
  "title": "Buy groceries",
  "description": "Milk, Eggs, Bread",
  "due_date": "2025-05-04T12:00:00",
  "reminder_time": "2025-05-04T09:00:00"
}
```

> پاسخ:
>
> ```json
> {
>   "inserted_id": "641234abcd5678ef90123456"
> }
> ```

---

## 5. لیست وظایف با فیلتر، مرتب‌سازی، صفحه‌بندی و شمارهٔ ردیف (GET /tasks)

```python
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    q = {}
    # filter by completion status
    if 'completed' in request.args:
        q['completed'] = request.args.get('completed').lower() == 'true'
    # filter by created_at range
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
```

### شرح اجزاء

1. **پارامترهای query string**

   * `completed=true|false` → فیلتر بر اساس وضعیت تکمیل
   * `from_date=YYYY-MM-DD` → شروع بازهٔ ایجاد
   * `to_date=YYYY-MM-DD` → پایان بازه

     * `+ timedelta(days=1) - timedelta(seconds=1)` تضمین می‌کند ساعت تا انتهای آن روز باشد.
   * `sort_by=field` و `order=asc|desc`
   * `page` و `per_page` برای صفحه‌بندی

2. **ساخت کوئری MongoDB**

   * با اضافه کردن کلیدهای `$gte` و `$lte` به فیلتر `created_at`.
   * *نکته:* اگر کاربر قالب اشتباه بدهد، با `ValueError` ۴۰۰ بازمی‌گردد.

3. **شمارش کل مستندات**

   * `count_documents(q)` برای نمایش تعداد کل نتایج (بدون صفحه‌بندی).

4. **مرتب‌سازی و صفحه‌بندی**

   * `sort()`, `skip()`, `limit()`.
   * `skip = (page-1)*per_page`.

5. **تبدیل فیلدها برای خروجی JSON**

   * **\_id**: از ObjectId به رشته
   * **created\_at**, **due\_date**, **reminder\_time**: با `isoformat()`
   * **remaining\_time**: اختلاف بین `due_date` و زمان فعلی؛ اگر منفی باشد، صفر می‌شود.

     * *مثال*: اگر `due_date` ساعت ۱۵ باشد و الان ۱۴:۳۰ است، خروجی ۱۸۰۰ ثانیه.
   * **row\_number**: شماره ردیف واقعی در کل نتایج (برای UI راحت).

6. **نمونه درخواست**

   ```bash
   GET /tasks?completed=false&from_date=2025-05-01&to_date=2025-05-03&sort_by=due_date&order=asc&page=2&per_page=5
   ```

   → نمایش صفحهٔ دوم با ۵ آیتم در روزهای مشخص.

---

## 6. عملیات گروهی (Bulk) – درج، به‌روزرسانی و حذف

### 6.1 درج گروهی (POST /tasks/bulk)

```python
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
```

* **اعتبارسنجی** که ورودی لیست باشد و خالی نباشد.
* برای هر آیتمِ لیست، مثل تک‌تسک `fromisoformat`.
* با `insert_many` تمام داکیومنت‌ها یک‌جا درج می‌شوند (سریع‌تر از تکرار `insert_one`).
* خروجی: لیست `inserted_ids`.

### 6.2 به‌روزرسانی گروهی (PUT /tasks/bulk)

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
```

* **ObjectId.is\_valid**: بررسی می‌کند رشته‌ی ارسالی قالب معتبری داشته باشد.
* `UpdateOne(filter, {'$set': u})`: اگر فیلد جدیدی ارسال شده باشد، آن را ست می‌کند.
* **bulk\_write** با `ordered=False`: مشکلات یک آپدیت خطا نداشته باشد بقیه اجرا شوند.

### 6.3 حذف گروهی (DELETE /tasks/bulk)

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

* بدنه باید `{ "ids": ["id1","id2",…] }` باشد.
* `delete_many({'_id': {'$in': valid_ids}})`: حذف همهٔ اسنادی که در لیست باشند.

---

## 7. جستجوی پیشرفته (GET /tasks/search)

```python
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    q = {}
    # by IDs
    ids = request.args.getlist('id')
    if ids:
        oids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
        if oids:
            q['_id'] = {'$in': oids}
    # regex search
    for field in ('title', 'description'):
        v = request.args.get(field)
        if v:
            q[field] = {'$regex': v, '$options': 'i'}
    # completion filter
    if 'completed' in request.args:
        q['completed'] = request.args.get('completed').lower() == 'true'
    # date range filters
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
        t['_id'] = str(t['_id'])
        t['created_at'] = t['created_at'].isoformat()
        if t.get('due_date'):
            t['due_date'] = t['due_date'].isoformat()
        if t.get('reminder_time'):
            t['reminder_time'] = t['reminder_time'].isoformat()
        tasks.append(t)

    return jsonify(tasks), 200
```

### امکانات این endpoint

1. **جستجوی بر اساس چند `id`**

   * `?id=…&id=…`
2. **جستجوی متنی (Regex) با گزینه‌ی غیرحساس به حروف بزرگ/کوچک**

   * `?title=buy` → همهٔ عنوان‌هایی که شامل «buy» (Buy, BUY, buy) باشند
3. **فیلتر وضعیت**

   * `?completed=true`
4. **فیلتر بازه تاریخ**

   * مثل بخش قبل.

> **مثال کامل:**
>
> ```
> GET /tasks/search?description=milk&from_date=2025-05-01&completed=false
> ```

---

## 8. یادآور پس‌زمینه (Background Reminder)

```python
def reminder_loop():
    while True:
        now = datetime.utcnow()
        for t in mongo.db.tasks.find({'reminder_time': {'$ne': None}}):
            if now >= t['reminder_time']:
                print(f"🔔 Reminder: Task '{t['title']}' is due!")
                mongo.db.tasks.update_one({'_id': t['_id']}, {'$unset': {'reminder_time': ""}})
        time.sleep(60)

threading.Thread(target=reminder_loop, daemon=True).start()
```

* **کارکرد:**

  1. هر ۶۰ ثانیه اجرا می‌شود.
  2. تمام تسک‌هایی که `reminder_time` دارند را چک می‌کند.
  3. اگر زمان فعلی گذشته بود → پیام در کنسول چاپ می‌کند و فیلد `reminder_time` را حذف می‌کند (تا یک بار چاپ شود).
* **نکته‌های مخفی:**

  * `daemon=True` یعنی وقتی سرور اصلی متوقف شود، ترد هم متوقف می‌شود.
  * اگر حجم تسک‌ها زیاد باشد، بهتر است ایندکس روی `reminder_time` بگذارید تا جستجو سریع باشد.

---

## 9. شمارش تسک‌ها (GET /tasks/counts)

```python
@app.route('/tasks/counts', methods=['GET'])
def count_tasks():
    total = mongo.db.tasks.count_documents({})
    completed = mongo.db.tasks.count_documents({'completed': True})
    return jsonify({
        "total_tasks": total,
        "completed_tasks": completed,
        "remaining_tasks": total - completed
    }), 200
```

* تعداد کل، تعداد تکمیل‌شده و تعداد باقی‌مانده را برمی‌گرداند.
* **مثال:**

  ```
  GET /tasks/counts
  Response:
  {
    "total_tasks": 42,
    "completed_tasks": 17,
    "remaining_tasks": 25
  }
  ```

---

## 10. حذف کامل دیتابیس (DELETE /database/drop)

```python
@app.route('/database/drop', methods=['DELETE'])
def drop_database():
    mongo.cx.drop_database('todo_db')
    return jsonify({"message": "Database 'todo_db' dropped successfully"}), 200
```

* `mongo.cx` شیء `MongoClient` است؛
* `drop_database('todo_db')` تمام داده‌های دیتابیس را پاک می‌کند.
* **احتیاط:** هر زمان اجرا شود، همهٔ داده‌ها از بین می‌رود! در محیط تولید (production) معمولاً غیرفعال می‌کنند.

---

## 11. اجرای سرور

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
```

* وقتی اسکریپت به‌صورت مستقیم اجرا شود، وب‌سرور Flask روی پورت ۸۰۰۰ شروع به کار می‌کند.
* `host='0.0.0.0'` اجازه می‌دهد از هر آدرس شبکه‌ای به آن متصل شد.
* `debug=True`

  * **نکتهٔ مهم:** در محیط توسعه مفید است (hot reload، نمایش خطا)، اما در production نباید فعال باشد.

---

## جمع‌بندی با مثال‌های واقعی

* **ایجاد تسک:**

  ```bash
  POST /tasks
  { "title": "تمرین پایتون", "due_date": "2025-05-05T18:00:00" }
  ```
* **گرفتن همهٔ تسک‌ها بین تاریخ‌ها و مرتب‌شده بر اساس موعد:**

  ```bash
  GET /tasks?from_date=2025-05-01&to_date=2025-05-04&sort_by=due_date&order=asc
  ```
* **جستجوی عنوان حاوی “گزارش”:**

  ```bash
  GET /tasks/search?title=گزارش
  ```
* **به‌روزرسانی چند تسک:**

  ```bash
  PUT /tasks/bulk
  [
    {"id":"6412…","completed":true},
    {"id":"6413…","due_date":"2025-05-06T12:00:00"}
  ]
  ```
* **حذف دیتابیس (فقط در تست):**

  ```bash
  DELETE /database/drop
  ```

با تشکر
