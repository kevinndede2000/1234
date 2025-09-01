from flask import Flask
from .auth import auth
from .views import views
from .exam_routes import exam_bp
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = "exam_portal_secret_key_2024"
    
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Register blueprints
    app.register_blueprint(auth)
    app.register_blueprint(views)
    app.register_blueprint(exam_bp)
    
    return app