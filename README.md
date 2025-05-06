در اینجا به‌صورت کامل و خط‌به‌خط کد Flask با اتصال به MongoDB برای مدیریت تسک‌ها را بررسی می‌کنیم. این کد شامل ایجاد، خواندن، به‌روزرسانی و حذف (CRUD) تسک‌ها است. همچنین، برای هر بخش مثال‌هایی با استفاده از Postman و curl ارائه شده است.

---

## 📦 1. وارد کردن کتابخانه‌ها

```python
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime
```



**توضیح:**

* `Flask`: فریم‌ورک وب برای ساخت API.
* `jsonify`: تبدیل داده‌های پایتون به JSON برای پاسخ‌دهی.
* `request`: دسترسی به داده‌های درخواست‌های HTTP.
* `PyMongo`: اتصال بین Flask و MongoDB.
* `ObjectId`: برای کار با شناسه‌های یکتای MongoDB.
* `UpdateOne`: برای به‌روزرسانی‌های گروهی در MongoDB.
* `datetime`: برای مدیریت تاریخ و زمان.

---

## 🚀 2. پیکربندی برنامه Flask و اتصال به MongoDB

```python
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/todo_db"
mongo = PyMongo(app)
```



**توضیح:**

* `Flask(__name__)`: ایجاد یک نمونه از برنامه Flask.
* `app.config["MONGO_URI"]`: تنظیم URI برای اتصال به پایگاه داده MongoDB.
* `PyMongo(app)`: ایجاد اتصال بین Flask و MongoDB با استفاده از PyMongo.([AI Framework][1])

---

## 🧰 3. تابع کمکی برای سریال‌سازی تسک‌ها

```python
def serialize_task(task):
    return {
        "id": str(task["_id"]),
        "title": task.get("title", ""),
        "description": task.get("description", ""),
        "created_at": task.get("created_at", datetime.utcnow()).isoformat(),
        "completed": task.get("completed", False)
    }
```



**توضیح:**

این تابع یک سند MongoDB را به یک دیکشنری پایتون تبدیل می‌کند که می‌تواند به JSON تبدیل شود. این کار برای ارسال پاسخ‌های JSON به کلاینت‌ها ضروری است.

---

## 🏠 4. مسیر اصلی (Home Route)

```python
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
```



**توضیح:**

این مسیر اطلاعاتی درباره API و مسیرهای موجود ارائه می‌دهد.

---

## 📋 5. دریافت لیست تسک‌ها با فیلتر و صفحه‌بندی

```python
@app.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')
        completed = request.args.get('completed')
        q = request.args.get('q', '')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

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

        sort_direction = -1 if order == 'desc' else 1
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
```



**توضیح:**

این مسیر لیستی از تسک‌ها را با امکان فیلتر کردن بر اساس وضعیت تکمیل، جستجو در عنوان و توضیحات، و فیلتر بر اساس تاریخ ایجاد ارائه می‌دهد. همچنین، امکان صفحه‌بندی نتایج وجود دارد.

**مثال با curl:**

```bash
curl -X GET "http://localhost:8000/tasks?page=1&per_page=5&completed=true&q=meeting"
```



**مثال با Postman:**

* روش: GET
* URL: [http://localhost:8000/tasks](http://localhost:8000/tasks)
* پارامترها:

  * page: 1
  * per\_page: 5
  * completed: true
  * q: meeting([MongoDB][2], [Codez Up][3], [The Linux Code][4])

---

## 📝 6. ایجاد تسک جدید (تکی یا گروهی)

```python
@app.route('/tasks', methods=['POST'])
def create_tasks():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "داده‌ای ارسال نشده است"}), 400

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
```



**توضیح:**

این مسیر امکان ایجاد یک تسک جدید یا چندین تسک به‌صورت گروهی را فراهم می‌کند. در صورت ارسال لیستی از تسک‌ها، هر کدام بررسی و در پایگاه داده ذخیره می‌شوند.

**مثال با curl (تسک تکی):**

```bash
curl -X POST http://localhost:8000/tasks \
     -H "Content-Type: application/json" \
     -d '{"title": "جلسه با تیم", "description": "بررسی پیشرفت پروژه"}'
```



**مثال با Postman (تسک گروهی):**

* روش: POST
* URL: [http://localhost:8000/tasks](http://localhost:8000/tasks)
* بدنه (Body):

```json
[
    {"title": "تسک 1", "description": "توضیح 1"},
    {"title": "تسک 2", "description": "توضیح 2"}
]
```

([The Linux Code][4], [AI Framework][1])

---

## 🔍 7. دریافت یک تسک خاص

```python
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
```



**توضیح:**

این مسیر یک تسک خاص را بر اساس شناسه یکتا (ObjectId) بازمی‌گرداند.

**مثال با curl:**

```bash
curl -X GET http://localhost:8000/tasks/60f7f9e2b
::contentReference[oaicite:112]{index=112}
 
```
با توجه به درخواست شما برای ادامه توضیحات در مورد کد ارائه‌شده، در ادامه به بخش‌های جدیدی از کد و عملکرد آن‌ها می‌پردازیم. این توضیحات شامل جزئیات فنی، مثال‌های عملی، و نکات مهم برای درک بهتر نحوه عملکرد API مدیریت تسک‌ها با استفاده از Flask و MongoDB است.

---

## 🧩 بخش ۸: حذف تمام تسک‌ها

```python
@app.route('/tasks/all', methods=['DELETE'])
def delete_all_tasks():
    try:
        result = mongo.db.tasks.delete_many({})
        return jsonify({
            "message": f"تمام تسک‌ها ({result.deleted_count}) حذف شدند",
            "deleted_count": result.deleted_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### توضیحات:

* **مسیر `/tasks/all`**: این مسیر برای حذف تمام تسک‌ها از پایگاه داده طراحی شده است.
* **متد `DELETE`**: با استفاده از این متد، تمام اسناد موجود در مجموعه `tasks` حذف می‌شوند.
* **عملکرد `delete_many({})`**: این متد تمام اسناد موجود در مجموعه را حذف می‌کند. آرگومان `{}` به معنای "همه اسناد" است.
* **مدیریت خطا**: در صورت بروز خطا، پیام خطا به صورت JSON بازگشت داده می‌شود.

### مثال:

برای حذف تمام تسک‌ها، می‌توانید از دستور `curl` زیر استفاده کنید:

```bash
curl -X DELETE http://localhost:8000/tasks/all
```

پاسخ موفقیت‌آمیز:

```json
{
  "message": "تمام تسک‌ها (5) حذف شدند",
  "deleted_count": 5
}
```

---

## 🧩 بخش ۹: حذف کامل پایگاه داده

```python
@app.route('/database/delete', methods=['DELETE'])
def delete_database():
    try:
        mongo.db.client.drop_database('todo_db')
        return jsonify({"message": "پایگاه داده به طور کامل حذف شد"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### توضیحات:

* **مسیر `/database/delete`**: این مسیر برای حذف کامل پایگاه داده `todo_db` طراحی شده است.
* **متد `DELETE`**: با استفاده از این متد، پایگاه داده مورد نظر حذف می‌شود.
* **عملکرد `drop_database('todo_db')`**: این متد پایگاه داده با نام `todo_db` را از سرور MongoDB حذف می‌کند.
* **مدیریت خطا**: در صورت بروز خطا، پیام خطا به صورت JSON بازگشت داده می‌شود.

### مثال:

برای حذف پایگاه داده، می‌توانید از دستور `curl` زیر استفاده کنید:

```bash
curl -X DELETE http://localhost:8000/database/delete
```

پاسخ موفقیت‌آمیز:

```json
{
  "message": "پایگاه داده به طور کامل حذف شد"
}
```

---

## 🧩 بخش ۱۰: شمارش تسک‌ها با فیلترهای مختلف

```python
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
```

### توضیحات:

* **مسیر `/tasks/count`**: این مسیر برای شمارش تعداد تسک‌ها با اعمال فیلترهای مختلف طراحی شده است.
* **پارامترهای ورودی**:

  * `completed`: وضعیت تکمیل تسک‌ها (`true` یا `false`).
  * `date_from` و `date_to`: بازه زمانی ایجاد تسک‌ها.
  * `q`: عبارت جستجو برای عنوان یا توضیحات تسک.
* **ساخت کوئری MongoDB**: با استفاده از پارامترهای ورودی، کوئری مناسب برای شمارش تسک‌ها ساخته می‌شود.
* **عملکرد `count_documents(query)`**: این متد تعداد اسنادی که با کوئری مشخص شده مطابقت دارند را برمی‌گرداند.

### مثال:

برای شمارش تعداد تسک‌های تکمیل‌شده، می‌توانید از دستور `curl` زیر استفاده کنید:

```bash
curl "http://localhost:8000/tasks/count?completed=true"
```

پاسخ موفقیت‌آمیز:

```json
{
  "count": 3
}
```

---

## 🧩 بخش ۱۱: راه‌اندازی سرور Flask

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
```

### توضیحات:

* **اجرای سرور**: این بخش کد برای راه‌اندازی سرور Flask استفاده می‌شود.
* **پارامتر `host='0.0.0.0'`**: این پارامتر باعث می‌شود سرور بر روی تمام اینترفیس‌های شبکه در دسترس باشد.
* **پارامتر `port=8000`**: پورت ۸۰۰۰ برای دسترسی به سرور تعیین شده است.
* **پارامتر `debug=True`**: حالت اشکال‌زدایی فعال می‌شود تا در صورت بروز خطا، اطلاعات مفیدی در کنسول نمایش داده شود.

### نکات:

* **حالت تولیدی**: در محیط تولیدی، بهتر است حالت اشکال‌زدایی را غیرفعال کنید تا اطلاعات حساس در دسترس قرار نگیرد.
* **امنیت**: در محیط‌های تولیدی، اطمینان حاصل کنید که سرور فقط به آدرس‌های IP مجاز دسترسی داشته باشد.

---

## 🔄 جمع‌بندی

در این بخش‌ها، به توضیح عملکرد و جزئیات فنی مسیرهای مختلف API مدیریت تسک‌ها پرداختیم. این API با استفاده از Flask و MongoDB طراحی شده است و امکاناتی مانند ایجاد، دریافت، به‌روزرسانی، حذف، جستجو، و شمارش تسک‌ها را فراهم می‌کند. همچنین، با استفاده از دستورهای `curl`، می‌توانید هر یک از این عملکردها را تست کنید و نتایج را مشاهده نمایید.

---
