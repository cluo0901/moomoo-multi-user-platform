# 🚀 Production Deployment Guide

Complete guide for deploying the multi-user moomoo trading platform to production.

## 📋 Prerequisites

### Infrastructure Requirements
- **Kubernetes Cluster** (v1.20+)
  - AWS EKS, Google GKE, Azure AKS, or local cluster
  - Minimum 4 GB RAM, 2 CPU cores available
  - Storage class for persistent volumes

- **Container Registry**
  - Docker Hub, AWS ECR, Google GCR, or Azure ACR
  - Push access configured

- **Database** (Production)
  - PostgreSQL 12+ (recommended)
  - Or SQLite for smaller deployments

### Tools Required
- `kubectl` configured for your cluster
- `docker` for building images
- `helm` (optional, for easier deployment)

## 🛠️ Build & Push Container Images

### 1. Build Platform Image
```bash
# Build the main platform
docker build -t your-registry/moomoo-platform:latest .

# Push to registry
docker push your-registry/moomoo-platform:latest
```

### 2. Build OpenD Connector Image
```bash
# Build the per-user connector
docker build -t your-registry/moomoo-opend-connector:latest \
  -f docker/opend-connector/Dockerfile .

# Push to registry
docker push your-registry/moomoo-opend-connector:latest
```

## ⚙️ Configuration

### 1. Update Kubernetes Manifests

Edit `k8s/platform-deployment.yaml`:
```yaml
# Update image references
image: your-registry/moomoo-platform:latest

# Update secrets
stringData:
  database-url: "postgresql://user:password@postgres:5432/moomoo_platform"
  jwt-secret: "your-super-secret-jwt-key-256-bits-minimum"
```

Edit `container_manager.py`:
```python
# Update default image
self.opend_image = os.getenv('OPEND_CONTAINER_IMAGE', 'your-registry/moomoo-opend-connector:latest')
```

### 2. Environment Variables
```bash
# Required environment variables
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export JWT_SECRET_KEY="your-super-secret-jwt-key"
export K8S_NAMESPACE="moomoo-users"
export OPEND_CONTAINER_IMAGE="your-registry/moomoo-opend-connector:latest"
```

## 🚀 Deploy to Kubernetes

### 1. Create Namespaces
```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Deploy PostgreSQL (if needed)
```bash
# Using Helm (recommended)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install postgres bitnami/postgresql \
  --namespace moomoo-platform \
  --set auth.postgresPassword=your-secure-password \
  --set primary.persistence.size=20Gi
```

### 3. Update Secrets
```bash
# Create or update platform secrets
kubectl create secret generic platform-secrets \
  --namespace=moomoo-platform \
  --from-literal=database-url="postgresql://postgres:your-secure-password@postgres:5432/postgres" \
  --from-literal=jwt-secret="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 4. Deploy Platform
```bash
kubectl apply -f k8s/platform-deployment.yaml
```

### 5. Verify Deployment
```bash
# Check pods
kubectl get pods -n moomoo-platform

# Check service
kubectl get svc -n moomoo-platform

# View logs
kubectl logs -f deployment/moomoo-platform -n moomoo-platform
```

## 🌐 Expose to Internet

### Option 1: LoadBalancer (Cloud Providers)
```yaml
# Add to platform-deployment.yaml
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 5000
```

### Option 2: Ingress (Recommended)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: moomoo-platform-ingress
  namespace: moomoo-platform
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: moomoo-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: moomoo-platform
            port:
              number: 5000
```

## 🔒 Security Configuration

### 1. RBAC for Container Management
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: moomoo-platform
  namespace: moomoo-platform
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: moomoo-container-manager
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["secrets", "pods"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: moomoo-container-manager
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: moomoo-container-manager
subjects:
- kind: ServiceAccount
  name: moomoo-platform
  namespace: moomoo-platform
```

### 2. Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: moomoo-isolation
  namespace: moomoo-users
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: moomoo-platform
```

## 📊 Monitoring & Observability

### 1. Health Checks
The platform includes built-in health endpoints:
- `GET /health` - Application health
- `GET /api` - API status

### 2. Prometheus Metrics (Optional)
Add monitoring annotations:
```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "5000"
    prometheus.io/path: "/metrics"
```

### 3. Logging
Configure log aggregation:
```bash
# Using Fluentd/ELK stack
kubectl apply -f https://raw.githubusercontent.com/fluent/fluentd-kubernetes-daemonset/master/fluentd-daemonset-elasticsearch.yaml
```

## 🔧 Database Migration

### For Existing Single-User Installations
```bash
# Run migration script
python migrations/init_multiuser.py

# Verify migration
python migrations/init_multiuser.py --verify-only
```

### For Fresh Installations
Database tables are created automatically on first startup.

## 🎯 Performance Tuning

### 1. Resource Limits
```yaml
resources:
  requests:
    cpu: 200m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### 2. Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: moomoo-platform-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: moomoo-platform
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 3. Database Connection Pooling
Update `app.py`:
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

## 🛡️ Backup & Disaster Recovery

### 1. Database Backups
```bash
# PostgreSQL backup
kubectl exec -it postgres-0 -n moomoo-platform -- \
  pg_dump -U postgres postgres > backup-$(date +%Y%m%d).sql
```

### 2. Configuration Backup
```bash
# Backup all Kubernetes resources
kubectl get all,secrets,configmaps -n moomoo-platform -o yaml > k8s-backup.yaml
```

## 📈 Scaling Considerations

### User Container Scaling
- Each user gets a dedicated container
- Containers auto-scale to zero when inactive
- Resource limits prevent resource exhaustion

### Platform Scaling
- Deploy multiple platform replicas
- Use external database (PostgreSQL)
- Implement Redis for session storage (optional)

## 🔍 Troubleshooting

### Common Issues

1. **Container provisioning fails**
   ```bash
   # Check RBAC permissions
   kubectl auth can-i create deployments --as=system:serviceaccount:moomoo-platform:moomoo-platform
   ```

2. **Database connection issues**
   ```bash
   # Test database connectivity
   kubectl run postgres-client --rm -ti --restart=Never --image postgres -- \
     psql -h postgres -U postgres
   ```

3. **JWT token issues**
   ```bash
   # Verify JWT secret
   kubectl get secret platform-secrets -o yaml
   ```

4. **User containers not starting**
   ```bash
   # Check user namespace
   kubectl get pods -n moomoo-users
   kubectl logs deployment/moomoo-user-123 -n moomoo-users
   ```

### Debug Commands
```bash
# Platform logs
kubectl logs -f deployment/moomoo-platform -n moomoo-platform

# User container logs
kubectl logs -f deployment/moomoo-user-{USER_ID} -n moomoo-users

# Check resource usage
kubectl top pods -n moomoo-platform
kubectl top pods -n moomoo-users

# Describe problematic resources
kubectl describe pod {POD_NAME} -n {NAMESPACE}
```

## 📱 Post-Deployment Steps

1. **Create Admin User**
   - Access the platform at your domain
   - Register the first admin user
   - Configure moomoo OpenD credentials

2. **Test User Container**
   - Register a test user
   - Verify container provisioning
   - Test data synchronization

3. **Security Audit**
   - Change all default passwords
   - Review RBAC permissions
   - Enable network policies
   - Configure SSL certificates

4. **Monitoring Setup**
   - Configure alerts for failures
   - Set up log aggregation
   - Monitor resource usage
   - Set up backup schedules

## 🎉 Success Checklist

- [ ] Platform accessible via HTTPS
- [ ] User registration working
- [ ] Container provisioning functional
- [ ] Database migrations completed
- [ ] SSL certificates configured
- [ ] Monitoring enabled
- [ ] Backups configured
- [ ] Security policies applied
- [ ] Documentation updated
- [ ] Admin users created

## 📞 Support

For deployment issues:
1. Check the troubleshooting section above
2. Review application logs
3. Verify configuration settings
4. Check Kubernetes resource status
5. Review GitHub issues for known problems

---

**🎯 Result**: A production-ready, scalable moomoo trading platform supporting unlimited users with dedicated OpenD containers!