# --------------------------
# 1. IMPORTS AND SETUP
# --------------------------
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from pymongo import UpdateOne
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Configure MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/todo_db"
mongo = PyMongo(app)

# --------------------------
# 2. HELPER FUNCTIONS
# --------------------------
def serialize_task(task):
    """Convert MongoDB document to JSON-friendly format"""
    return {
        "id": str(task["_id"]),
        "title": task.get("title", ""),
        "description": task.get("description", ""),
        "created_at": task.get("created_at", datetime.utcnow()).isoformat(),
        "completed": task.get("completed", False)
    }

# --------------------------
# 3. API ENDPOINTS
# --------------------------

# (A) GET ALL TASKS
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    try:
        tasks = list(mongo.db.tasks.find())
        return jsonify([serialize_task(task) for task in tasks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (B) CREATE TASK(S)
@app.route('/tasks', methods=['POST'])
def create_task():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Handle multiple tasks
        if isinstance(data, list):
            inserted_ids = []
            for task in data:
                if "title" not in task:
                    return jsonify({"error": "Missing title in one or more tasks"}), 400
                new_task = {
                    "title": task["title"],
                    "description": task.get("description", ""),
                    "created_at": datetime.utcnow(),
                    "completed": False
                }
                result = mongo.db.tasks.insert_one(new_task)
                inserted_ids.append(str(result.inserted_id))
            return jsonify({
                "message": f"Created {len(inserted_ids)} tasks",
                "task_ids": inserted_ids
            }), 201

        # Handle single task
        if "title" not in data:
            return jsonify({"error": "Title is required"}), 400
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

# (C) GET SINGLE TASK
@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    try:
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "Invalid task ID"}), 400
        task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
        if task:
            return jsonify(serialize_task(task)), 200
        return jsonify({"error": "Task not found"}), 404
    except Exception:
        return jsonify({"error": "Invalid task ID"}), 400

# (D) UPDATE TASK
@app.route('/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    try:
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "Invalid task ID"}), 400
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No update data provided"}), 400

        updates = {}
        if "title" in data:
            updates["title"] = data["title"]
        if "description" in data:
            updates["description"] = data["description"]
        if "completed" in data:
            updates["completed"] = bool(data["completed"])

        if not updates:
            return jsonify({"error": "No valid fields to update"}), 400

        result = mongo.db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": updates}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Task not found"}), 404
        return jsonify({"message": "Task updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (E) DELETE TASK
@app.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "Invalid task ID"}), 400
        result = mongo.db.tasks.delete_one({"_id": ObjectId(task_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Task not found"}), 404
        return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (F) SEARCH TASKS
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

# (G) DELETE BULK
@app.route('/tasks/bulk', methods=['DELETE'])
def bulk_delete():
    try:
        data = request.get_json(force=True)
        if not data or "task_ids" not in data:
            return jsonify({"error": "Missing task_ids array"}), 400
        valid_ids = [ObjectId(i) for i in data["task_ids"] if ObjectId.is_valid(i)]
        result = mongo.db.tasks.delete_many({"_id": {"$in": valid_ids}})
        return jsonify({
            "message": f"Deleted {result.deleted_count} tasks",
            "deleted_count": result.deleted_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (H) BULK UPDATE
@app.route('/tasks/bulk', methods=['PUT'])
def bulk_update_tasks():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, list) or not data:
            return jsonify({"error": "Provide a non-empty list"}), 400

        operations = []
        for item in data:
            task_id = item.get("id")
            if not task_id or not ObjectId.is_valid(task_id):
                return jsonify({"error": f"Invalid or missing id: {task_id}"}), 400
            updates = {}
            for field in ("title", "description", "completed"):
                if field in item:
                    updates[field] = bool(item[field]) if field == "completed" else item[field]
            if updates:
                operations.append(
                    UpdateOne({"_id": ObjectId(task_id)}, {"$set": updates})
                )
        if not operations:
            return jsonify({"error": "No valid updates provided"}), 400
        result = mongo.db.tasks.bulk_write(operations, ordered=False)
        return jsonify({
            "matched_count": result.matched_count,
            "modified_count": result.modified_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------------
# 4. START THE SERVER
# --------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
