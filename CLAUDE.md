# Moomoo Multi-User Trading Platform

A production-ready multi-user platform for moomoo trading with containerized OpenD instances and SMS verification management.

## Project Overview

This platform provides:
- Multi-user authentication and management
- Per-user containerized moomoo OpenD instances
- SMS verification handling with state recovery
- Real-time trading data synchronization
- Web-based dashboard interface

## Architecture

- **Backend**: Flask with JWT authentication
- **Database**: SQLite with SQLAlchemy ORM
- **Containers**: Docker containers for isolated OpenD instances
- **Frontend**: HTML/CSS/JavaScript dashboard
- **API**: RESTful endpoints for trading operations

## Quick Start Commands

### Development Server
```bash
# Start development server
source .venv/bin/activate && python run_local.py

# Setup fresh database
source .venv/bin/activate && python setup_fresh_database.py && python run_local.py
```

### Testing
```bash
# Test SMS recovery system
source .venv/bin/activate && python test_sms_recovery.py

# Test logout cleanup flow
source .venv/bin/activate && python test_logout_cleanup.py

# Test full SMS flow
source .venv/bin/activate && python test_full_sms_flow.py
```

### Container Management
```bash
# Check container status
docker ps | grep moomoo-user

# View container logs
docker logs moomoo-user-alice --tail 50

# Check container service directly
curl -s http://localhost:8001/status | jq
curl -s -X POST http://localhost:8001/reset-sms
```

## Key Features

### SMS Verification System
- **Automatic SMS Detection**: Detects moomoo exit codes -5, 12, 14 for SMS requirements
- **State Recovery**: 5-minute timeout mechanism prevents hanging SMS states
- **Force Reconnect**: Manual SMS state reset capability via `/reset-sms` endpoint
- **Logout Cleanup**: Automatic cleanup of all connections and SMS state on logout
- **Login Cleanup**: Fresh start guarantee on every login

### Multi-User Management
- **Isolated Containers**: Each user gets their own OpenD container instance
- **Credential Management**: Encrypted storage of moomoo credentials
- **Session Management**: JWT-based authentication with automatic cleanup

### API Endpoints

#### Authentication
- `POST /auth/login` - User login with automatic cleanup
- `POST /auth/logout` - Logout with connection cleanup
- `POST /auth/register` - User registration
- `GET /auth/me` - Current user info

#### OpenD Management
- `POST /auth/opend-config` - Configure moomoo credentials
- `POST /auth/connect-opend` - Initiate OpenD connection
- `POST /auth/verify-sms` - Submit SMS verification code
- `POST /auth/disconnect-opend` - Disconnect OpenD
- `GET /auth/connection-status` - Get connection status

#### Trading Data
- `GET /api/positions` - Get current positions
- `GET /api/trades` - Get trade history
- `GET /api/orders` - Get order history
- `GET /api/dashboard-stats` - Dashboard statistics

## File Structure

### Core Files
- `app.py` - Main Flask application
- `run_local.py` - Local development server
- `auth_routes.py` - Authentication and OpenD management routes
- `container_manager.py` - Docker container management
- `models.py` - Database models

### Container Service
- `docker/opend-connector/connector_service.py` - Core OpenD connector with SMS handling
- `docker/opend-connector/Dockerfile` - Container image definition

### Test Files
- `test_sms_recovery.py` - SMS state recovery testing
- `test_logout_cleanup.py` - Logout cleanup testing
- `test_full_sms_flow.py` - Complete SMS verification flow testing

## Configuration

### Environment Variables
- `K8S_NAMESPACE` - Kubernetes namespace (default: moomoo-users)
- `OPEND_CONTAINER_IMAGE` - OpenD container image
- `CONTAINER_CPU_REQUEST/LIMIT` - Resource limits
- `CONTAINER_MEMORY_REQUEST/LIMIT` - Memory limits

### Database
- SQLite database: `trading_dashboard.db`
- Automatic initialization on first run
- Models: User, UserCredentials, Trade, Position, Order

## Troubleshooting

### SMS Issues
1. **SMS Modal Appears but No SMS Received**:
   - Check moomoo account phone number verification
   - Verify account status in moomoo app
   - Contact moomoo support for SMS delivery issues

2. **SMS State Hanging**:
   - System automatically resets after 5 minutes
   - Manual reset: `curl -X POST http://localhost:8001/reset-sms`
   - Logout/login triggers automatic cleanup

3. **Connection Issues**:
   - Check container status: `docker logs moomoo-user-alice`
   - Verify credentials configuration
   - Check OpenD process logs for exit codes

### Container Issues
1. **Container Not Starting**:
   - Check Docker daemon status
   - Verify container image availability
   - Check resource constraints

2. **Connection Timeout**:
   - Verify network connectivity
   - Check firewall settings
   - Ensure OpenD service is responding

## Development Notes

### Adding New Features
1. Database changes require migration scripts
2. New API endpoints should include proper authentication
3. Container service changes need Docker image rebuild
4. Test coverage required for all new features

### SMS Verification Flow
1. User triggers connection → OpenD starts
2. OpenD exits with code -5 → SMS required detected
3. Frontend shows SMS modal → User enters code
4. Code submitted → OpenD verification
5. Success → Connection established
6. Timeout/Failure → State reset after 5 minutes

### Security Considerations
- All credentials encrypted in database
- JWT tokens for session management
- Container isolation between users
- No sensitive data in logs

## Recent Updates

### SMS State Recovery System (Latest)
- Implemented comprehensive SMS state recovery
- Added 5-minute timeout mechanism
- Enhanced logout cleanup to reset all connections
- Added login cleanup for fresh start guarantee
- Improved SMS detection with exit code -5
- Comprehensive test coverage for recovery scenarios

### Multi-User OpenD Integration
- Per-user Docker container provisioning
- Isolated moomoo OpenD instances
- Real-time SMS verification handling
- Production-ready deployment architecture

## Support

For issues with:
- **SMS Delivery**: Contact moomoo support
- **Platform Issues**: Check logs and container status
- **Development Questions**: Review test files for examples