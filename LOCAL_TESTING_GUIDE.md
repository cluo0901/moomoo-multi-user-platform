# 🧪 Local Testing Guide - Multi-User Moomoo Platform

This guide will help you test all features of the multi-user moomoo trading platform locally.

## 📋 Prerequisites

1. **Start the server:**
   ```bash
   python run_local.py
   ```
   The server will be available at: http://localhost:8080

2. **Verify server health:**
   ```bash
   curl http://localhost:8080/health
   # Should return: {"status": "healthy"}
   ```

## 🧪 Testing Steps

### 1. Test User Registration

**Register User 1 (Alice):**
```bash
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "password123"}'
```

**Expected Response:**
```json
{
  "access_token": "eyJ...",
  "message": "User registered successfully",
  "user": {
    "id": 5,
    "username": "alice",
    "email": "alice@example.com",
    "container_status": "inactive",
    "openapi_configured": false
  }
}
```

**Register User 2 (Bob):**
```bash
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "email": "bob@example.com", "password": "password456"}'
```

### 2. Test User Login

**Login Alice:**
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'
```

**Save the access_token from the response for API testing.**

### 3. Test API Authentication

**Test without authentication (should fail):**
```bash
curl http://localhost:8080/api/trades
# Expected: {"code": "missing_token", "error": "Authorization token required"}
```

**Test with authentication:**
```bash
# Replace YOUR_TOKEN with actual token from login
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/api/trades
```

### 4. Test Web Interface

Open these URLs in your browser:

1. **Main Dashboard:** http://localhost:8080/
   - Should redirect to auth page if not logged in
   - Shows trading dashboard after login

2. **Authentication Page:** http://localhost:8080/auth
   - Registration and login forms
   - Test creating accounts here

3. **API Info:** http://localhost:8080/api
   - Lists available endpoints
   - No authentication required

### 5. Test Multi-User Isolation

**Use the provided test script:**
```bash
python test_api.py
```

This script will:
- Login both Alice and Bob
- Test API access for each user
- Verify data isolation

### 6. Test Container Management (Simulated)

Since Kubernetes is not available locally, container management is simulated:

**Check container status:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/auth/container-status
```

**Start container:**
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/auth/container/start
```

**Stop container:**
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/auth/container/stop
```

## 🎯 What to Look For

### ✅ Success Indicators:

1. **User Registration**: New users get unique IDs and tokens
2. **Authentication**: Login returns valid JWT tokens
3. **API Security**: Endpoints require valid tokens
4. **Multi-User Support**: Different users get separate data
5. **Container Tracking**: Each user has container status
6. **Web Interface**: Pages load and show appropriate content

### ❌ Potential Issues:

1. **Token Validation**: JWT tokens may become invalid due to server restarts
2. **Database Persistence**: Local SQLite may reset between sessions
3. **Container Management**: Kubernetes features are simulated only

## 🔧 Troubleshooting

**If JWT tokens become invalid:**
- The server restarts can change JWT secrets
- Simply login again to get fresh tokens

**If database seems empty:**
- Local mode uses in-memory database
- Data persists only during server session

**If API calls fail:**
- Check server is running at localhost:8080
- Verify token is included in Authorization header
- Check server logs for detailed errors

## 🚀 Production Testing

For full production testing with real container management:

1. Set up Kubernetes cluster
2. Configure kubectl access
3. Follow DEPLOYMENT.md guide
4. Test with actual moomoo API credentials

## 📊 Expected Test Results

After running all tests, you should see:

- ✅ 2+ users registered successfully
- ✅ Login working for all users
- ✅ API endpoints protected by authentication
- ✅ Multi-user data isolation working
- ✅ Container status tracking functional
- ✅ Web interface accessible and responsive

This confirms the platform is ready for production deployment!