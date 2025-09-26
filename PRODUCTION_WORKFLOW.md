# 🚀 Production Step-by-Step: Alice's Moomoo Access

## Complete Production Workflow with Real Commands

### **Step 1: Alice's Platform Login**

```bash
# 1.1 Alice opens browser
https://your-platform-domain.com/auth

# 1.2 Alice logs in via API
curl -X POST https://your-platform-domain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "her_secure_password"
  }'

# Response:
{
  "access_token": "eyJ...",
  "user": {
    "id": 5,
    "username": "alice",
    "email": "alice@company.com",
    "container_status": "inactive",
    "container_id": null,
    "openapi_configured": false
  }
}
```

### **Step 2: Platform Provisions Alice's Container**

```bash
# 2.1 Check current container status
curl -H "Authorization: Bearer ALICE_TOKEN" \
     https://your-platform-domain.com/auth/container-status

# 2.2 Start Alice's dedicated container
curl -X POST \
     -H "Authorization: Bearer ALICE_TOKEN" \
     https://your-platform-domain.com/auth/container/start

# Behind the scenes Kubernetes commands:
# kubectl create deployment moomoo-user-5 --namespace=moomoo-users
# kubectl create secret generic moomoo-secret-5 --namespace=moomoo-users
# kubectl apply -f alice-container-config.yaml

# Response:
{
  "status": "success",
  "message": "Container starting",
  "container_id": "moomoo-user-5"
}
```

### **Step 3: Alice Configures Her Moomoo Connection**

```bash
# 3.1 Alice provides her moomoo credentials
curl -X POST https://your-platform-domain.com/auth/opend-config \
  -H "Authorization: Bearer ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "moomoo_host": "127.0.0.1",
    "moomoo_port": 11111,
    "security_firm": "FUTUSG",
    "trade_market": "US",
    "moomoo_username": "alice_moomoo_user",
    "moomoo_password": "alice_moomoo_pass"
  }'

# What happens in Alice's container:
# 1. Platform updates Kubernetes secret with Alice's credentials
# 2. Container restarts with new configuration
# 3. OpenD process starts with Alice's credentials
# 4. OpenD connects to moomoo API
# 5. Container status changes to "running"
```

### **Step 4: Data Synchronization Flow**

```bash
# 4.1 Alice triggers data sync from dashboard
curl -X POST https://your-platform-domain.com/api/refresh-data \
  -H "Authorization: Bearer ALICE_TOKEN"

# Internal flow:
# Platform API → Alice's Container (moomoo-user-5:8000/sync)
# Alice's Container → Moomoo API via OpenD (localhost:11111)
# Moomoo API → Returns Alice's trading data
# Alice's Container → Platform API (with user_id=5)
# Platform → Database (INSERT WHERE user_id=5)
```

### **Step 5: Alice Accesses Her Data**

```bash
# 5.1 Get Alice's trading history
curl -H "Authorization: Bearer ALICE_TOKEN" \
     "https://your-platform-domain.com/api/trades?start_date=2024-01-01&end_date=2024-12-31"

# Database query executed:
# SELECT * FROM trades WHERE user_id = 5 AND deal_time BETWEEN '2024-01-01' AND '2024-12-31'

# 5.2 Get Alice's current positions
curl -H "Authorization: Bearer ALICE_TOKEN" \
     "https://your-platform-domain.com/api/positions"

# Database query executed:
# SELECT * FROM positions WHERE user_id = 5 AND qty > 0

# 5.3 Get Alice's order history
curl -H "Authorization: Bearer ALICE_TOKEN" \
     "https://your-platform-domain.com/api/orders"

# Database query executed:
# SELECT * FROM orders WHERE user_id = 5 ORDER BY create_time DESC
```

## **Container Architecture Detail**

### **Alice's Dedicated Container (moomoo-user-5)**

```yaml
# Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moomoo-user-5
  namespace: moomoo-users
spec:
  replicas: 1
  selector:
    matchLabels:
      user-id: "5"
  template:
    spec:
      containers:
      - name: opend-connector
        image: your-registry/moomoo-opend-connector:latest
        ports:
        - containerPort: 11111  # OpenD API
        - containerPort: 8000   # Connector API
        env:
        - name: USER_ID
          value: "5"
        - name: PLATFORM_API_URL
          value: "https://your-platform-domain.com"
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
          readOnly: true
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 1Gi
      volumes:
      - name: config-volume
        secret:
          secretName: moomoo-secret-5
```

### **Alice's Container Endpoints**

```bash
# Health check
GET http://moomoo-user-5:8000/health

# Container ready status
GET http://moomoo-user-5:8000/ready

# Trigger data sync
POST http://moomoo-user-5:8000/sync

# Container status
GET http://moomoo-user-5:8000/status
```

## **Data Flow Diagram**

```
Alice's Browser
       ↓ HTTPS
Platform Load Balancer
       ↓
Platform API (JWT Auth)
       ↓
Alice's Container (moomoo-user-5)
       ↓
OpenD Process (port 11111)
       ↓
Moomoo API Servers
       ↓
Alice's Trading Data
```

## **Security & Isolation**

### **Network Policies**

```yaml
# Only Platform API can access Alice's container
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: alice-container-isolation
spec:
  podSelector:
    matchLabels:
      user-id: "5"
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: moomoo-platform
    ports:
    - protocol: TCP
      port: 8000
```

### **RBAC Permissions**

```yaml
# Platform service account can manage Alice's container
apiVersion: v1
kind: ServiceAccount
metadata:
  name: moomoo-platform
  namespace: moomoo-platform
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: moomoo-users
  name: container-manager
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "create", "update", "delete"]
- apiGroups: [""]
  resources: ["secrets", "pods"]
  verbs: ["get", "list", "create", "update", "delete"]
```

## **Monitoring & Observability**

### **Alice's Container Metrics**

```bash
# Container resource usage
kubectl top pod moomoo-user-5 -n moomoo-users

# Container logs
kubectl logs -f moomoo-user-5 -n moomoo-users

# OpenD connection status
curl http://moomoo-user-5:8000/health

# Data sync metrics
curl http://moomoo-user-5:8000/metrics
```

### **Platform Monitoring**

```bash
# Alice's API usage
GET /api/users/5/usage-stats

# Alice's data sync history
GET /api/users/5/sync-history

# Alice's container uptime
GET /api/users/5/container-metrics
```

## **Scaling & Performance**

### **Auto-scaling Alice's Container**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: moomoo-user-5-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: moomoo-user-5
  minReplicas: 0  # Scale to zero when inactive
  maxReplicas: 2  # Scale up during heavy usage
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

This complete workflow ensures Alice has secure, isolated, and scalable access to her moomoo trading data while maintaining strict separation from other users!