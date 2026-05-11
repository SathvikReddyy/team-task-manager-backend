from flask import  Flask
from flask_cors import CORS
from pymongo import MongoClient
from config import Config
from routes.auth_routes import auth_bp
from flask_jwt_extended import JWTManager
from routes.project_routes import project_bp
from routes.task_routes import task_bp

app=Flask(__name__)
CORS(app)
client = MongoClient(Config.MONGO_URI)

app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
jwt= JWTManager(app)

@app.route("/")
def home():
    return {
        "message": "Welcome to Team Task Manager API"
    }
app.register_blueprint(auth_bp)
app.register_blueprint(project_bp)
app.register_blueprint(task_bp)

if(__name__=="__main__"):
    app.run(debug=True) 