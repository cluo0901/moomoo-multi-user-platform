from flask import Flask, jsonify, request, render_template_string, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'local-dev-jwt-secret-key-moomoo-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['JWT_ALGORITHM'] = 'HS256'
# Completely disable CSRF protection for JWT tokens in all forms
app.config['JWT_CSRF_CHECK_FORM'] = False
app.config['JWT_CSRF_IN_COOKIES'] = False
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
# Additional CSRF disable options for different Flask-JWT-Extended versions
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_ACCESS_CSRF_HEADER_NAME'] = None

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///moomoo_trading.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
jwt = JWTManager(app)

# Initialize database with app
from models import db, User, Trade, Order, Position, bcrypt
db.init_app(app)
bcrypt.init_app(app)

# Import routes
from api_routes import api_bp
from auth_routes import auth_bp
from local_dev_routes import local_dev_bp

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(local_dev_bp, url_prefix='/')

# JWT Error Handlers
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': 'Token has expired', 'code': 'token_expired'}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'error': 'Invalid token', 'code': 'invalid_token'}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'error': 'Authorization token required', 'code': 'missing_token'}), 401

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/auth')
@app.route('/auth/')
def auth():
    return send_from_directory(app.static_folder, 'auth.html')

@app.route('/api')
def api_info():
    return jsonify({
        'message': 'Moomoo Trading Dashboard API',
        'endpoints': [
            '/api/trades',
            '/api/orders',
            '/api/positions',
            '/api/dashboard-stats',
            '/api/currency-info',
            '/api/refresh-data'
        ]
    })

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)