from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from models import db, User
from container_manager import ContainerManager

auth_bp = Blueprint('auth', __name__)
container_mgr = ContainerManager()

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        username = data.get('username').strip()
        email = data.get('email').strip().lower()
        password = data.get('password')

        # Validate input
        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        if '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400

        # Create new user
        user = User(
            username=username,
            email=email
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Provision container for user (async)
        try:
            container_mgr.provision_user_container(user.id)
        except Exception as e:
            print(f"Warning: Container provisioning failed for user {user.id}: {e}")

        # Create access token
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=7)
        )

        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()

        username_or_email = data.get('username') or data.get('email')
        password = data.get('password')

        if not username_or_email or not password:
            return jsonify({'error': 'Username/email and password are required'}), 400

        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) |
            (User.email == username_or_email)
        ).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Create access token
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=7)
        )

        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'user': user.to_dict()})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/container-status', methods=['GET'])
@jwt_required()
def get_container_status():
    """Get user's container status"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get real-time container status
        try:
            # Check if Kubernetes is available
            if not container_mgr.k8s_enabled:
                # Local development mode - simulate container status
                status = 'simulated_local'
                user.container_status = status
                db.session.commit()
            else:
                status = container_mgr.get_container_status(user.container_id)
                if status != user.container_status:
                    user.container_status = status
                    db.session.commit()
        except Exception as e:
            print(f"Error getting container status: {e}")
            # In local development, default to simulated status
            status = 'simulated_local' if not container_mgr.k8s_enabled else user.container_status

        return jsonify({
            'container_status': status,
            'container_id': user.container_id,
            'openapi_configured': user.openapi_configured,
            'last_sync': user.last_sync.isoformat() if user.last_sync else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/container/start', methods=['POST'])
@jwt_required()
def start_container():
    """Start user's container"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Start container
        result = container_mgr.start_container(user_id)

        if result.get('status') == 'success':
            user.container_status = 'starting'
            user.container_id = result.get('container_id')
            db.session.commit()

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/container/stop', methods=['POST'])
@jwt_required()
def stop_container():
    """Stop user's container"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Stop container
        result = container_mgr.stop_container(user.container_id)

        if result.get('status') == 'success':
            user.container_status = 'inactive'
            db.session.commit()

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/opend-config', methods=['POST'])
@jwt_required()
def configure_opend():
    """Configure OpenD credentials for user's container"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        # Required OpenD configuration - support both old and new field names
        # Old fields: moomoo_host, moomoo_port (for backward compatibility)
        # New fields: moomoo_username, moomoo_password (for real credentials)

        username = data.get('moomoo_username') or data.get('moomoo_host')
        password = data.get('moomoo_password') or data.get('moomoo_port')
        security_firm = data.get('security_firm')
        trade_market = data.get('trade_market')

        if not username:
            return jsonify({'error': 'moomoo_username or moomoo_host is required'}), 400
        if not password:
            return jsonify({'error': 'moomoo_password or moomoo_port is required'}), 400
        if not security_firm:
            return jsonify({'error': 'security_firm is required'}), 400
        if not trade_market:
            return jsonify({'error': 'trade_market is required'}), 400

        # Configure OpenD in container with real moomoo credentials
        result = container_mgr.configure_opend(
            user.container_id,
            {
                'host': username,  # Pass username for backward compatibility
                'port': password,  # Pass password for backward compatibility
                'security_firm': security_firm,
                'trade_market': trade_market,
                'moomoo_username': username,  # Also pass directly
                'moomoo_password': password   # Also pass directly
            }
        )

        # For local development mode, always mark as configured
        if result.get('status') == 'success' or result.get('message') == 'Kubernetes not available':
            user.openapi_configured = True
            db.session.commit()

            # Override result for local development
            if result.get('message') == 'Kubernetes not available':
                result = {'status': 'success', 'message': 'OpenD configuration saved (local development mode)'}

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client-side token removal)"""
    return jsonify({'message': 'Logout successful'})