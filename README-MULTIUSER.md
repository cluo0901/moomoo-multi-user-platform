# Moomoo Multi-User Trading Platform

A scalable, containerized multi-user platform for moomoo trading data with per-user OpenD instances.

## Architecture Overview

### Core Components

1. **Platform API** - Main Flask application with user management and authentication
2. **Container Manager** - Kubernetes orchestrator for per-user OpenD instances
3. **Per-User Containers** - Isolated OpenD + Connector service for each user
4. **Database** - PostgreSQL with user-isolated data models

### Multi-User Flow

```
User Registration → Container Provisioning → OpenD Setup → Data Sync → Dashboard
```

## Features

### 🔐 Authentication & Security
- JWT-based authentication with 7-day tokens
- Bcrypt password hashing
- Per-user data isolation at database level
- Container-level tenant isolation

### 🐳 Container Orchestration
- Kubernetes-based per-user deployments
- Auto-scaling (scale-to-zero for inactive users)
- Resource limits and health monitoring
- Automatic container lifecycle management

### 📊 Multi-Currency Trading Data
- Real-time sync from individual moomoo OpenD instances
- Currency conversion with live/static rates
- Historical data (2+ years) with chunked retrieval
- Interactive charts and analytics

### 🔄 Managed OpenD Integration
- One-click container provisioning
- Secure credential storage via Kubernetes secrets
- Container status monitoring
- Automated restarts and configuration updates

## Quick Start

### Prerequisites

- Kubernetes cluster (local or cloud)
- Docker registry access
- PostgreSQL database
- kubectl configured

### 1. Build Container Images

```bash
# Platform image
docker build -t moomoo/platform:latest .

# OpenD connector image
docker build -t moomoo/opend-connector:latest -f docker/opend-connector/Dockerfile .

# Push to your registry
docker push moomoo/platform:latest
docker push moomoo/opend-connector:latest
```

### 2. Deploy to Kubernetes

```bash
# Create namespaces
kubectl apply -f k8s/namespace.yaml

# Deploy platform
kubectl apply -f k8s/platform-deployment.yaml

# Update secrets with your values
kubectl edit secret platform-secrets -n moomoo-platform
```

### 3. Configure Environment

```bash
export PLATFORM_URL="http://your-platform-url"
export JWT_SECRET="your-super-secret-jwt-key"
export DATABASE_URL="postgresql://user:pass@host:5432/db"
```

### 4. Access Platform

```bash
# Get platform URL
kubectl get service moomoo-platform -n moomoo-platform

# Access at http://<EXTERNAL-IP>:5000
```

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user
- `POST /auth/logout` - Logout

### Container Management
- `GET /auth/container-status` - Get container status
- `POST /auth/container/start` - Start user container
- `POST /auth/container/stop` - Stop user container
- `POST /auth/opend-config` - Configure OpenD credentials

### Trading Data (JWT Required)
- `GET /api/trades` - Get user's trades
- `GET /api/orders` - Get user's orders
- `GET /api/positions` - Get user's positions
- `GET /api/dashboard-stats` - Get dashboard statistics
- `POST /api/refresh-data` - Trigger data sync

## User Journey

### 1. Registration & Setup
```bash
curl -X POST $PLATFORM_URL/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "trader123",
    "email": "trader@example.com",
    "password": "securepass123"
  }'
```

### 2. Container Provisioning (Automatic)
- Container automatically provisioned on registration
- Initial status: `inactive`
- User can start when ready

### 3. OpenD Configuration
```bash
curl -X POST $PLATFORM_URL/auth/opend-config \\
  -H "Authorization: Bearer $JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "moomoo_host": "127.0.0.1",
    "moomoo_port": 11111,
    "security_firm": "FUTUSG",
    "trade_market": "US"
  }'
```

### 4. Data Synchronization
```bash
curl -X POST $PLATFORM_URL/api/refresh-data \\
  -H "Authorization: Bearer $JWT_TOKEN"
```

## Database Schema

### Users
- `id`, `username`, `email`, `password_hash`
- `container_id`, `container_status`, `openapi_configured`
- `created_at`, `last_login`, `last_sync`

### Trades (User-Isolated)
- `user_id` (FK), `deal_id`, `code`, `stock_name`
- `deal_time`, `qty`, `price`, `val`, `side`

### Orders (User-Isolated)
- `user_id` (FK), `order_id`, `code`, `trd_side`
- `order_status`, `qty`, `price`, `create_time`

### Positions (User-Isolated)
- `user_id` (FK), `code`, `qty`, `market_val`
- `unrealized_pl`, `snapshot_time`

## Security Considerations

### Container Isolation
- Each user gets dedicated Kubernetes namespace
- Network policies prevent cross-user access
- Resource limits prevent resource exhaustion

### Data Privacy
- All database queries filtered by `user_id`
- JWT tokens include user identity
- No cross-user data leakage possible

### Credential Management
- OpenD credentials stored in Kubernetes secrets
- Per-user secret encryption at rest
- API keys for container-platform communication

## Monitoring & Observability

### Container Health
- Liveness probes on port 8000/health
- Readiness probes for OpenD status
- Automatic restart on failure

### Platform Metrics
- User registration and activity
- Container resource utilization
- Data sync success rates
- API response times

## Cost Optimization

### Auto-Scaling
- Scale containers to 0 when inactive
- Burst scaling during market hours
- Resource requests/limits optimization

### Resource Sharing
- Shared base images
- Efficient container scheduling
- Database connection pooling

## Deployment Options

### Cloud Providers

**AWS EKS**
```bash
eksctl create cluster --name moomoo-platform --region us-west-2
```

**Google GKE**
```bash
gcloud container clusters create moomoo-platform --zone us-central1-a
```

**Azure AKS**
```bash
az aks create --resource-group myResourceGroup --name moomoo-platform
```

### Local Development
```bash
# Using minikube
minikube start
kubectl apply -f k8s/
```

## Troubleshooting

### Container Issues
```bash
# Check container status
kubectl get pods -n moomoo-users

# View container logs
kubectl logs -f deployment/moomoo-user-123 -n moomoo-users

# Debug container
kubectl exec -it deployment/moomoo-user-123 -n moomoo-users -- /bin/bash
```

### Database Issues
```bash
# Check database connectivity
kubectl port-forward svc/postgresql 5432:5432

# View platform logs
kubectl logs -f deployment/moomoo-platform -n moomoo-platform
```

### Authentication Issues
- Verify JWT_SECRET_KEY is consistent across deployments
- Check token expiration (7-day default)
- Ensure user registration completed successfully

## Production Checklist

- [ ] Update all default secrets and passwords
- [ ] Configure proper SSL/TLS termination
- [ ] Set up database backups and monitoring
- [ ] Configure resource limits and requests
- [ ] Set up logging aggregation (ELK/Fluentd)
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Set up alerting for critical failures
- [ ] Test disaster recovery procedures
- [ ] Configure network policies
- [ ] Set up CI/CD pipelines

## Support & Contributing

For issues and feature requests, please use the GitHub repository issue tracker.

## License

MIT License - see LICENSE file for details.