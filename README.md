**توضیحات کامل کد خط به خط با مثال‌ها و نکات ریز:**

---

### **1. Import کتابخانه‌ها**
```python
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime
```
- **Flask**: فریمورک اصلی برای ساخت API.
- **jsonify**: تبدیل دیکشنری پایتون به JSON.
- **request**: دسترسی به داده‌های درخواست HTTP.
- **PyMongo**: ادغام Flask با MongoDB.
- **ObjectId**: مدیریت شناسه‌های منحصر به فرد MongoDB.
- **UpdateOne**: انجام عملیات bulk update در MongoDB.
- **datetime**: مدیریت زمان ایجاد و به‌روزرسانی تسک‌ها.

---

### **2. تنظیمات اولیه Flask و MongoDB**
```python
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/todo_db"
mongo = PyMongo(app)
```
- **app**: شیء اصلی Flask.
- **MONGO_URI**: آدرس پایگاه داده MongoDB (`todo_db`).
- **mongo**: شیء اتصال به MongoDB برای انجام عملیات CRUD.

**نکته:** اگر پایگاه داده وجود نداشته باشد، MongoDB به صورت خودکار آن را ایجاد می‌کند.

---

### **3. تابع کمکی `serialize_task`**
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
- **هدف:** تبدیل سند MongoDB به فرمت JSON.
- **جزئیات:**
  - `_id` به رشته تبدیل می‌شود (چون JSON از ObjectId پشتیبانی نمی‌کند).
  - `created_at` به فرمت ISO8601 تبدیل می‌شود (مثلاً `2023-10-01T12:34:56.789Z`).
  - مقادیر پیش‌فرض برای فیلدهای اختیاری مانند `description` و `completed`.

**مثال خروجی:**
```json
{
  "id": "652a1b2c3d4e5f6a1b2c3d4e",
  "title": "خرید شیر",
  "description": "2 لیتر شیر از فروشگاه",
  "created_at": "2023-10-12T08:30:45.123Z",
  "completed": false
}
```

---

### **4. صفحه اصلی (`GET /`)**
```python
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
        "example_url": "http://192.168.1.107:8000/tasks"
    }), 200
```
- **هدف:** ارائه راهنمای API به کاربران.
- **جزئیات:**
  - لیست کامل endpointها با متدهای مربوطه.
  - مثال URL برای تست سریع.

**مثال خروجی:**
```json
{
  "message": "به API مدیریت تسک‌ها خوش آمدید! 🎉",
  "endpoints": {
    "get_all_tasks": "GET /tasks",
    "create_task": "POST /tasks",
    ...
  },
  "example_url": "http://192.168.1.107:8000/tasks"
}
```

---

### **5. دریافت تمام تسک‌ها (`GET /tasks`)**
```python
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    try:
        tasks = list(mongo.db.tasks.find())
        return jsonify([serialize_task(task) for task in tasks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```
- **هدف:** بازیابی تمام تسک‌ها از دیتابیس.
- **جزئیات:**
  - استفاده از `find()` برای دریافت تمام اسناد.
  - تبدیل هر سند با تابع `serialize_task`.
  - مدیریت خطا با کد وضعیت 500.

**مثال درخواست:**
```bash
curl http://localhost:8000/tasks
```

---

### **6. ایجاد تسک (`POST /tasks`)**
```python
@app.route('/tasks', methods=['POST'])
def create_task():
    try:
        data = request.get_json(force=True)
        # ... (ایجاد تک یا گروهی تسک)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```
- **هدف:** ایجاد یک یا چند تسک جدید.
- **جزئیات:**
  - `force=True`: حتی اگر کلاینت `Content-Type` را تنظیم نکرده باشد، داده را به عنوان JSON پردازش می‌کند.
  - پشتیبانی از ایجاد تک تسک و گروهی.

**مثال درخواست تک تسک:**
```bash
curl -X POST -H "Content-Type: application/json" -d '{"title": "تماس با مشتری"}' http://localhost:8000/tasks
```

**مثال درخواست گروهی:**
```bash
curl -X POST -H "Content-Type: application/json" -d '[{"title": "تسک 1"}, {"title": "تسک 2"}]' http://localhost:8000/tasks
```

---

### **7. دریافت تک تسک (`GET /tasks/<task_id>`)**
```python
@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    try:
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "شناسه تسک نامعتبر است"}), 400
        task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
        # ...
```
- **هدف:** دریافت جزئیات یک تسک خاص.
- **جزئیات:**
  - بررسی معتبر بودن `ObjectId`.
  - استفاده از `find_one()` برای جستجوی تسک.

**مثال خطا (شناسه نامعتبر):**
```json
{"error": "شناسه تسک نامعتبر است"}
```

---

### **8. به‌روزرسانی تک تسک (`PUT /tasks/<task_id>`)**
```python
updates = {}
if "title" in data:
    updates["title"] = data["title"]
# ...
```
- **هدف:** به‌روزرسانی بخشی از اطلاعات یک تسک.
- **جزئیات:**
  - فقط فیلدهای ارسال شده آپدیت می‌شوند.
  - استفاده از `$set` در MongoDB برای به‌روزرسانی جزئی.

**مثال درخواست:**
```bash
curl -X PUT -H "Content-Type: application/json" -d '{"completed": true}' http://localhost:8000/tasks/1234567890ab
```

---

### **9. به‌روزرسانی گروهی (`PUT /tasks/bulk/update`)**
```python
operations = []
for item in data:
    operations.append(UpdateOne(...))
result = mongo.db.tasks.bulk_write(operations, ordered=False)
```
- **هدف:** به‌روزرسانی چندین تسک در یک درخواست.
- **جزئیات:**
  - استفاده از `bulk_write` برای کارایی بهتر.
  - `ordered=False`: ادامه عملیات حتی در صورت خطا در برخی آیتم‌ها.

**مثال درخواست:**
```bash
curl -X PUT -H "Content-Type: application/json" -d '[{"id": "123", "title": "تسک جدید"}, {"id": "456", "completed": true}]' http://localhost:8000/tasks/bulk/update
```

---

### **10. حذف کامل پایگاه داده (`DELETE /database/delete`)**
```python
mongo.db.client.drop_database('todo_db')
```
- **هدف:** پاک کردن کامل پایگاه داده (فقط برای محیط توسعه!).
- **هشدار:** این عمل غیرقابل بازگشت است!

**مثال درخواست:**
```bash
curl -X DELETE http://localhost:8000/database/delete
```

---

### **نکات امنیتی و بهبودها**
- **اعتبارسنجی ورودی:** بررسی وجود `title` و فرمت `ObjectId`.
- **مدیریت خطا:** استفاده از `try-except` در تمام endpointها.
- **محدودیت‌ها:** عدم وجود احراز هویت و محدودیت نرخ.

---

**پایان!** این توضیحات کامل تمام بخش‌های کد، مثال‌ها و نکات فنی را پوشش می‌دهد.
