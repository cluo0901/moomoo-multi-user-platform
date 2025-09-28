from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from models import db, User, UserCredentials
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

        # Ensure user has a container_id (for backwards compatibility)
        if not user.container_id:
            user.container_id = f"alice"  # Use alice for local development
            user.container_status = 'running'  # Set as running for local dev
            print(f"Assigned container_id 'alice' to user {user.username}")

        # Clean up any existing connections for fresh start
        if user.container_id:
            try:
                cleanup_result = container_mgr.cleanup_all_connections(user.container_id)
                print(f"Login cleanup for {user.username}: {cleanup_result.get('message', 'completed')}")
            except Exception as e:
                print(f"Warning: Login cleanup failed for user {user.username}: {e}")

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

        # Save credentials to database first
        try:
            # Get or create user credentials
            credentials = UserCredentials.query.filter_by(user_id=user.id).first()
            if not credentials:
                credentials = UserCredentials(user_id=user.id)
                db.session.add(credentials)

            # Update credentials
            credentials.moomoo_username = username
            credentials.set_encrypted_password(password)
            credentials.security_firm = security_firm
            credentials.trade_market = trade_market

            # Commit to database first
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to save credentials: {str(e)}'}), 500

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
    """Logout user and cleanup all connections"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Clean up all OpenD connections and SMS state
        cleanup_results = []
        if user.container_id:
            try:
                result = container_mgr.cleanup_all_connections(user.container_id)
                cleanup_results.append(result)
            except Exception as e:
                print(f"Warning: Failed to cleanup connections for user {user.username}: {e}")
                cleanup_results.append({'success': False, 'error': str(e)})

        return jsonify({
            'message': 'Logout successful - all connections cleaned up',
            'cleanup_results': cleanup_results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/user-settings', methods=['GET'])
@jwt_required()
def get_user_settings():
    """Get current user settings and credentials"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'openapi_configured': user.openapi_configured,
            'container_id': user.container_id,
            'container_status': user.container_status,
            'last_sync': user.last_sync.isoformat() if user.last_sync else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/connect-opend', methods=['POST'])
@jwt_required()
def connect_opend():
    """Initiate OpenD connection for user's container"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if user has credentials in database
        credentials = UserCredentials.query.filter_by(user_id=user.id).first()
        if not credentials:
            return jsonify({
                'success': False,
                'error': 'moomoo credentials not configured. Please configure your credentials in Settings first.',
                'requires_config': True
            }), 400

        # Ensure container manager has the latest credentials from database
        try:
            container_mgr.configure_opend(
                user.container_id,
                {
                    'moomoo_username': credentials.moomoo_username,
                    'moomoo_password': credentials.get_decrypted_password(),
                    'security_firm': credentials.security_firm,
                    'trade_market': credentials.trade_market
                }
            )
        except Exception as e:
            print(f"Warning: Failed to update container config: {e}")

        # Use container manager to initiate connection
        result = container_mgr.initiate_opend_connection(user.container_id)

        # Check for SMS verification requirement first (regardless of success flag)
        if result.get('requires_sms_verification'):
            return jsonify({
                'success': True,
                'requires_sms_verification': True,
                'message': result.get('message', 'SMS verification required. Please check your phone for the verification code.')
            })
        elif result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Connected to moomoo successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to initiate OpenD connection')
            }), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/verify-sms', methods=['POST'])
@jwt_required()
def verify_sms():
    """Submit SMS verification code for OpenD connection"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        sms_code = data.get('sms_code')

        if not sms_code:
            return jsonify({'error': 'SMS code is required'}), 400

        # Use container manager to verify SMS code
        result = container_mgr.verify_sms_code(user.container_id, sms_code)

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'SMS verification successful! Connected to moomoo.'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'SMS verification failed')
            }), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/disconnect-opend', methods=['POST'])
@jwt_required()
def disconnect_opend():
    """Disconnect OpenD for user's container"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Use container manager to disconnect
        result = container_mgr.disconnect_opend(user.container_id)

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Disconnected from moomoo successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to disconnect from moomoo')
            }), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/connection-status', methods=['GET'])
@jwt_required()
def get_connection_status():
    """Get current OpenD connection status for user's container"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Use container manager to get status
        result = container_mgr.get_connection_status(user.container_id)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500