from flask import Blueprint, request
from pymongo import MongoClient
from config import Config
from flask_jwt_extended import create_access_token, current_user, get_jwt, get_jwt_identity,jwt_required

from utilites.hash import hash_password,check_password
from config import Config
from middleware.role_middleware import admin_required
print("executing auth_routes.py")
client = MongoClient(Config.MONGO_URI)

auth_bp = Blueprint('auth', __name__,url_prefix='/auth')
db=client['team_task_manager'] 
users_collection=db['users']
@auth_bp.route('/signup', methods=['POST'])
def signup():
    data=request.get_json()

    name=data.get('name')
    email=data.get('email')
    password=data.get('password')   
    role=data.get('role')

    if( not name or not email or not password or not role):
        return {
            "message": "All fields are required"
        },400
    
    if(role not in ['admin','member']):
        return {
            "message": "Role must be either 'admin' or 'member'"
        },400
    existing_user=users_collection.find_one({"email":email})

    if(existing_user):
        return {
            "message": "User with this email already exists"
        },400
    hashed_password=hash_password(password)
    user_data={
        "name":name,
        "email":email,
        "password":hashed_password,
        "role":role

    }
    users_collection.insert_one(user_data)
    return {
        "message": "User registered successfully"
    },201

@auth_bp.route('/login',methods=['POST'])
def login():
    data=request.get_json()
    email=data.get('email')
    password=data.get('password')   
    if(not email or not password):
        return{
            "message": "Email and password are required"
        },400
    user=users_collection.find_one({"email":email})
    if(not user):
        return {
            "message": "user not found"
        },401
    if(not(check_password(password,user['password']))):
        return {
            "message": "Invalid password"
        },401
    access_token=create_access_token(
        identity=str(user['_id']),
        additional_claims={"role": user['role']}

        )   
    return{
        "message": "Login successful",
        "access_token": access_token,
        "role": user['role'],
        "email": user['email']
    },200
@auth_bp.route('/profile',methods=['GET'])
@jwt_required()
def profile():
    current_user_id=get_jwt_identity()
    claims=get_jwt()  
    print("PROFILE ROUTE HIT")
  
    return {
        "message": "Profile endpoint",
        "user": current_user_id,
        "role":claims['role']
    },200

@auth_bp.route("/admin-test",methods=['GET'])
@jwt_required()
@admin_required
def admin_test():
    return {
        "message": "Welcome Admin "
    },200
@auth_bp.route("/hello")
def hello():
    return {
        "message": "hello"
    }
print("END OF FILE REACHED")