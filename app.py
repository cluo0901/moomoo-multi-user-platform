from flask import Flask, jsonify, request, render_template_string, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///moomoo_trading.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
from models import db, Trade, Order, Position
db.init_app(app)

# Import routes
from api_routes import api_bp

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

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