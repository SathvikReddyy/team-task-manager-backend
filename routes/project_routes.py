from datetime import datetime

from bson import ObjectId
from flask import Flask, Blueprint, request
from pymongo import MongoClient 
from config import Config
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from middleware.role_middleware import admin_required

client= MongoClient(Config.MONGO_URI)
db=client['team_task_manager']
task_collection = db["tasks"]
user_collection = db["users"]
project_collection = db["projects"]
project_bp=Blueprint('project',__name__,url_prefix='/projects')
@project_bp.route('/create',methods=['POST'])
@jwt_required()
@admin_required
def create_project():
    data=request.get_json()
    title=data.get('title')
    description=data.get('description')
    if(not title or not description ):
        return {
            "message": "Title and description are required"  
        },400
    current_user_id=get_jwt_identity()
    project_data={
        "title":title,
        "description":description,
        "created_by":current_user_id,
        "members":[],
        "created_at": datetime.utcnow()
    }
    project_collection.insert_one(project_data)
    return {
        "message": "Project created successfully"
    },201

@project_bp.route("/my-projects",methods=['GET'])
@jwt_required()
def my_projects():
    current_user_id=get_jwt_identity()
    projects=project_collection.find({
        "$or":[
            {"created_by":current_user_id},
            {"members":current_user_id}
        ]
    })
    project_list=[]
    for project in projects:
        project_data={
            "id":str(project["_id"]),
            "title":project["title"],
            "description":project["description"],
            "created_by":project["created_by"],
            "created_at":project["created_at"],
            "members":project["members"]   
        }
        project_list.append(project_data)
    return {
        "projects":project_list
    },200
    
@project_bp.route("/add-member/<project_id>", methods=["POST"])
@jwt_required()
@admin_required
def add_member(project_id):
    current_user_id=get_jwt_identity()
    data=request.get_json()
    email=data.get('email')
    if(not email):
        return {
            "message": "Email is required"
        },400
    print(project_id)
    project = project_collection.find_one({
            "_id": ObjectId(project_id)
    })
    if(not project):
        return {
            "message": "Project not found"
        },404
    if(project['created_by']!=current_user_id):
        return {
            "message": "Only project creator can add members"
        },403
    user=user_collection.find_one({"email":email})
    if(not user):
        return {
            "message": "User not found"
        },404
    if(str(user['_id']) == current_user_id):
        return {
            "message": "Admin is already a member of the project"
        },400
    project_collection.update_one(
        {
            "_id": ObjectId(project_id)
        },
        {
            "$addToSet":{
                "members": str(user['_id'])
            }
        }
)
    return {
        "message": "Member added successfully"
    },200
@project_bp.route("/delete/<project_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_project(project_id):

    current_user_id = get_jwt_identity()

    # =========================
    # FIND PROJECT
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
    # ONLY CREATOR CAN DELETE
    # =========================

    if project["created_by"] != current_user_id:
        return {
            "message": "Only project creator can delete project"
        },403

    # =========================
    # DELETE RELATED TASKS
    # =========================

    task_collection.delete_many({
        "project_id": project_id
    })

    # =========================
    # DELETE PROJECT
    # =========================

    project_collection.delete_one({
        "_id": ObjectId(project_id)
    })

    return {
        "message": "Project and related tasks deleted successfully"
    },200
@project_bp.route("/<project_id>", methods=["GET"])
@jwt_required()
def get_single_project(project_id):

    current_user_id = get_jwt_identity()

    # =========================
    # FIND PROJECT
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
    # ACCESS CHECK
    # =========================

    is_creator = (
        project["created_by"] == current_user_id
    )

    is_member = (
        current_user_id in project["members"]
    )

    if not is_creator and not is_member:
        return {
            "message": "Unauthorized access"
        },403

    # =========================
    # FETCH CREATOR DETAILS
    # =========================

    creator = user_collection.find_one({
        "_id": ObjectId(project["created_by"])
    })

    formatted_creator = None

    if creator:

        formatted_creator = {

            "id": str(creator["_id"]),
            "name": creator["name"],
            "email": creator["email"]

        }

    # =========================
    # FETCH MEMBERS
    # =========================

    formatted_members = []

    for member_id in project["members"]:

        try:

            user = user_collection.find_one({
                "_id": ObjectId(member_id)
            })

            if user:

                formatted_members.append({

                    "id": str(user["_id"]),
                    "name": user["name"],
                    "email": user["email"]

                })

        except:
            pass

    # =========================
    # FETCH TASKS
    # =========================

    tasks = list(task_collection.find({
        "project_id": project_id
    }))

    formatted_tasks = []

    for task in tasks:

        assigned_user = user_collection.find_one({
            "_id": ObjectId(task["assigned_to"])
        })

        assigned_to = None

        if assigned_user:

            assigned_to = {

                "id": str(assigned_user["_id"]),
                "name": assigned_user["name"],
                "email": assigned_user["email"]

            }

        formatted_tasks.append({

            "id": str(task["_id"]),
            "title": task["title"],
            "description": task["description"],
            "priority": task["priority"],
            "status": task["status"],
            "due_date": task["due_date"],
            "assigned_to": assigned_to

        })

    # =========================
    # FINAL RESPONSE
    # =========================

    return {

        "project": {

            "id": str(project["_id"]),
            "title": project["title"],
            "description": project["description"],

            "created_by": formatted_creator,

            "created_at": project["created_at"],

            "members": formatted_members,

            "tasks": formatted_tasks

        }

    },200