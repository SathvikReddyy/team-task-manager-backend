from bson import ObjectId
from flask import Flask, Blueprint, request
from pymongo import MongoClient
from config import Config
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from middleware.role_middleware import admin_required
from datetime import datetime
client= MongoClient(Config.MONGO_URI)
db=client['team_task_manager']
task_collection=db['tasks']
project_collection=db['projects']
user_collection=db['users']

task_bp=Blueprint('task',__name__,url_prefix='/tasks')
@task_bp.route('/create',methods=['POST'])
@jwt_required()
@admin_required
def create_task():
    current_user_id=get_jwt_identity()
    data=request.get_json()
    title=data.get('title')
    description=data.get('description') 
    project_id=data.get('project_id')
    assigned_to_email = data.get("assigned_to_email")
    due_date=data.get('due_date')
    priority=data.get('priority')

    if(not title or not description or not project_id or not assigned_to_email or not due_date or not priority):
        return {
            "message": "All fields are required"
        },400
    allowed_priorities=['low','medium','high']
    user = user_collection.find_one({
        "email": assigned_to_email
    })

    if not user:
        return {
            "message": "User not found"
        },404

    assigned_to = str(user["_id"])
    if(priority not in allowed_priorities): 
        return {
            "message": "Priority must be one of 'low', 'medium', or 'high'"
        },400
    try:
        project=project_collection.find_one({"_id":ObjectId(project_id)})
        if(not project):
            return {
                "message": "Project not found"
            },404
    except:
        return {
            "message": "Invalid project ID"
        },400
    if not project:
        return {
            "message": "Project not found"
        },404
    if project['created_by']!=current_user_id:
        return{
            "message": "Only project creator can create tasks"
        },403
    if assigned_to not in project['members']:
        return {
            "message": "Assigned user must be a member of the project"
        },400
    existing_task = task_collection.find_one({
        "title": title,
        "project_id": project_id,
        "assigned_to": assigned_to
    })

    if existing_task:
        return {
            "message": "Task already exists"
        },400
    task_data={
        "title":title,
        "description":description,
        "project_id":project_id,
        "assigned_to":assigned_to,
        "assigned_by":current_user_id,
        "due_date":due_date,
        "priority":priority,
        "status":"pending",
        "created_at": datetime.utcnow()
    }
    task_collection.insert_one(task_data)
    return {
        "message": "Task created successfully"
    },201

@task_bp.route("/my-tasks", methods=["GET"])
@jwt_required()
def my_tasks():

    current_user_id = get_jwt_identity()

    tasks = list(task_collection.find({
        "assigned_to": current_user_id
    }))

    formatted_tasks = []

    for task in tasks:

        formatted_tasks.append({
            "id": str(task["_id"]),
            "title": task["title"],
            "description": task["description"],
            "priority": task["priority"],
            "status": task["status"],
            "project_id": task["project_id"],
            "due_date": task["due_date"]
        })

    return {
        "tasks": formatted_tasks
    },200

@task_bp.route("/update-status/<task_id>", methods=["PATCH"])
@jwt_required()
def update_status(task_id):
    current_user_id=get_jwt_identity()
    data=request.get_json()
    new_status=data.get('status')
    new_status = new_status.upper()
    allowed_status = [
        "PENDING",
        "IN_PROGRESS",
        "DONE"
    ]
    if new_status not in allowed_status:
        return {
            "message": "INVALID STATUS"
        },400
    try:
        task=task_collection.find_one({"_id":ObjectId(task_id)})
    except:
        return {
            "message": "Invalid task ID"
        },400
    if not task:
        return {
            "message": "Task not found"
        },404
    if task['assigned_to']!=current_user_id:
        return {
            "message": "Only assigned user can update status"
        },403
    task_collection.update_one(
        {"_id":ObjectId(task_id)},
        {"$set":{"status":new_status}}
    )
    return {
        "message": "Task status updated successfully"    
    },200
@task_bp.route("/project/<project_id>", methods=["GET"])
@jwt_required()
@admin_required
def get_project_tasks(project_id):

    current_user_id = get_jwt_identity()

    # =========================
    # VALIDATE PROJECT ID
    # =========================

    try:

        project = project_collection.find_one({
            "_id": ObjectId(project_id)
        })

    except:
        return {
            "message": "Invalid project id"
        },400

    if not project:
        return {
            "message": "Project not found"
        },404

    # =========================
    # ONLY PROJECT CREATOR
    # =========================

    if project["created_by"] != current_user_id:
        return {
            "message": "Only creator can view project tasks"
        },403

    # =========================
    # FETCH TASKS
    # =========================

    tasks = list(task_collection.find({
        "project_id": project_id
    }))

    formatted_tasks = []

    for task in tasks:
        user = user_collection.find_one({
            "_id": ObjectId(task["assigned_to"])
        })
        formatted_tasks.append({

            "id": str(task["_id"]),
            "title": task["title"],
            "description": task["description"],
            "priority": task["priority"],
            "status": task["status"],
            "assigned_to": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"]
            },
            "due_date": task["due_date"]

        })

    return {
        "tasks": formatted_tasks
    },200
@task_bp.route("/edit/<task_id>", methods=["PATCH"])
@jwt_required()
@admin_required
def edit_task(task_id):

    current_user_id = get_jwt_identity()

    data = request.get_json()

    # =========================
    # FIND TASK
    # =========================

    try:

        task = task_collection.find_one({
            "_id": ObjectId(task_id)
        })

    except:

        return {
            "message": "Invalid task id"
        },400

    if not task:
        return {
            "message": "Task not found"
        },404

    # =========================
    # VERIFY PROJECT OWNERSHIP
    # =========================

    project = project_collection.find_one({
        "_id": ObjectId(task["project_id"])
    })

    if not project:
        return {
            "message": "Project not found"
        },404

    if project["created_by"] != current_user_id:
        return {
            "message": "Only project creator can edit tasks"
        },403

    # =========================
    # UPDATE FIELDS
    # =========================

    update_fields = {}

    if "title" in data:
        update_fields["title"] = data["title"]

    if "description" in data:
        update_fields["description"] = data["description"]

    if "priority" in data:
        update_fields["priority"] = data["priority"].upper()

    if "due_date" in data:
        update_fields["due_date"] = data["due_date"]

    # =========================
    # ASSIGNED USER UPDATE
    # =========================

    if "assigned_to_email" in data:

        user = user_collection.find_one({
            "email": data["assigned_to_email"]
        })

        if not user:
            return {
                "message": "Assigned user not found"
            },404

        update_fields["assigned_to"] = str(user["_id"])

    # =========================
    # UPDATE TASK
    # =========================

    task_collection.update_one(
        {
            "_id": ObjectId(task_id)
        },
        {
            "$set": update_fields
        }
    )

    return {
        "message": "Task updated successfully"
    },200
@task_bp.route("/delete/<task_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_task(task_id):

    current_user_id = get_jwt_identity()

    # =========================
    # FIND TASK
    # =========================

    try:

        task = task_collection.find_one({
            "_id": ObjectId(task_id)
        })

    except:

        return {
            "message": "Invalid task id"
        },400

    if not task:
        return {
            "message": "Task not found"
        },404

    # =========================
    # FIND PROJECT
    # =========================

    project = project_collection.find_one({
        "_id": ObjectId(task["project_id"])
    })

    if not project:
        return {
            "message": "Project not found"
        },404

    # =========================
    # ONLY CREATOR CAN DELETE
    # =========================

    if project["created_by"] != current_user_id:
        return {
            "message": "Only project creator can delete tasks"
        },403

    # =========================
    # DELETE TASK
    # =========================

    task_collection.delete_one({
        "_id": ObjectId(task_id)
    })

    return {
        "message": "Task deleted successfully"
    },200