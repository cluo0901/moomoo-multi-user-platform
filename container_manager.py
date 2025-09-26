import os
import time
import secrets
import base64
import json
from datetime import datetime

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    print("Warning: Kubernetes client not available. Container management will be disabled.")

class ContainerManager:
    """Manages per-user Kubernetes deployments for OpenD containers"""

    def __init__(self):
        if not KUBERNETES_AVAILABLE:
            self.k8s_enabled = False
            return

        # Load Kubernetes config
        try:
            config.load_incluster_config()  # If running in cluster
        except:
            try:
                config.load_kube_config()  # If running locally with kubeconfig
            except:
                print("Warning: Kubernetes config not found. Container management disabled.")
                self.k8s_enabled = False
                return

        self.k8s_enabled = True
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = os.getenv('K8S_NAMESPACE', 'moomoo-users')

        # Container image settings
        self.opend_image = os.getenv('OPEND_CONTAINER_IMAGE', 'moomoo/opend-connector:latest')

        # Resource limits
        self.cpu_request = os.getenv('CONTAINER_CPU_REQUEST', '100m')
        self.cpu_limit = os.getenv('CONTAINER_CPU_LIMIT', '500m')
        self.memory_request = os.getenv('CONTAINER_MEMORY_REQUEST', '256Mi')
        self.memory_limit = os.getenv('CONTAINER_MEMORY_LIMIT', '1Gi')

    def _ensure_namespace(self):
        """Ensure the namespace exists"""
        if not self.k8s_enabled:
            return False

        try:
            self.core_v1.read_namespace(name=self.namespace)
        except ApiException as e:
            if e.status == 404:
                # Create namespace
                namespace = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=self.namespace)
                )
                self.core_v1.create_namespace(body=namespace)
                print(f"Created namespace: {self.namespace}")
        return True

    def _get_deployment_name(self, user_id):
        """Get deployment name for user"""
        return f"moomoo-user-{user_id}"

    def _get_secret_name(self, user_id):
        """Get secret name for user"""
        return f"moomoo-secret-{user_id}"

    def _create_user_secret(self, user_id, config_data):
        """Create secret for user's OpenD configuration"""
        secret_name = self._get_secret_name(user_id)

        # Encode configuration as base64
        config_json = json.dumps(config_data)
        config_b64 = base64.b64encode(config_json.encode()).decode()

        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=secret_name, namespace=self.namespace),
            type="Opaque",
            data={
                'config.json': config_b64,
                'api-key': base64.b64encode(secrets.token_urlsafe(32).encode()).decode()
            }
        )

        try:
            self.core_v1.create_namespaced_secret(namespace=self.namespace, body=secret)
        except ApiException as e:
            if e.status == 409:  # Already exists
                self.core_v1.replace_namespaced_secret(
                    name=secret_name, namespace=self.namespace, body=secret
                )

    def _create_deployment_manifest(self, user_id):
        """Create Kubernetes deployment manifest for user"""
        deployment_name = self._get_deployment_name(user_id)
        secret_name = self._get_secret_name(user_id)

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=deployment_name,
                namespace=self.namespace,
                labels={
                    'app': 'moomoo-connector',
                    'user-id': str(user_id)
                }
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={
                        'app': 'moomoo-connector',
                        'user-id': str(user_id)
                    }
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            'app': 'moomoo-connector',
                            'user-id': str(user_id)
                        }
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name='opend-connector',
                                image=self.opend_image,
                                ports=[
                                    client.V1ContainerPort(container_port=11111, name='opend-api'),
                                    client.V1ContainerPort(container_port=8000, name='connector-api')
                                ],
                                env=[
                                    client.V1EnvVar(name='USER_ID', value=str(user_id)),
                                    client.V1EnvVar(name='PLATFORM_API_URL', value=os.getenv('PLATFORM_API_URL', 'http://platform-api:5000')),
                                    client.V1EnvVar(
                                        name='API_KEY',
                                        value_from=client.V1EnvVarSource(
                                            secret_key_ref=client.V1SecretKeySelector(
                                                name=secret_name,
                                                key='api-key'
                                            )
                                        )
                                    )
                                ],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        name='config-volume',
                                        mount_path='/app/config',
                                        read_only=True
                                    )
                                ],
                                resources=client.V1ResourceRequirements(
                                    requests={
                                        'cpu': self.cpu_request,
                                        'memory': self.memory_request
                                    },
                                    limits={
                                        'cpu': self.cpu_limit,
                                        'memory': self.memory_limit
                                    }
                                ),
                                liveness_probe=client.V1Probe(
                                    http_get=client.V1HTTPGetAction(
                                        path='/health',
                                        port=8000
                                    ),
                                    initial_delay_seconds=30,
                                    period_seconds=10
                                ),
                                readiness_probe=client.V1Probe(
                                    http_get=client.V1HTTPGetAction(
                                        path='/ready',
                                        port=8000
                                    ),
                                    initial_delay_seconds=10,
                                    period_seconds=5
                                )
                            )
                        ],
                        volumes=[
                            client.V1Volume(
                                name='config-volume',
                                secret=client.V1SecretVolumeSource(
                                    secret_name=secret_name
                                )
                            )
                        ],
                        restart_policy='Always'
                    )
                )
            )
        )

        return deployment

    def provision_user_container(self, user_id):
        """Provision a new container for user"""
        if not self.k8s_enabled:
            return {'status': 'error', 'message': 'Kubernetes not available'}

        try:
            self._ensure_namespace()

            # Create default configuration secret
            default_config = {
                'moomoo_host': '127.0.0.1',
                'moomoo_port': 11111,
                'security_firm': 'FUTUSG',
                'trade_market': 'US',
                'configured': False
            }
            self._create_user_secret(user_id, default_config)

            # Create deployment
            deployment = self._create_deployment_manifest(user_id)
            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace,
                body=deployment
            )

            return {
                'status': 'success',
                'message': 'Container provisioned successfully',
                'container_id': self._get_deployment_name(user_id)
            }

        except ApiException as e:
            return {'status': 'error', 'message': f'Kubernetes API error: {e.reason}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def start_container(self, user_id):
        """Start user's container (scale up from 0)"""
        if not self.k8s_enabled:
            return {'status': 'error', 'message': 'Kubernetes not available'}

        deployment_name = self._get_deployment_name(user_id)

        try:
            # Scale deployment to 1 replica
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )

            deployment.spec.replicas = 1

            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
                body=deployment
            )

            return {
                'status': 'success',
                'message': 'Container starting',
                'container_id': deployment_name
            }

        except ApiException as e:
            if e.status == 404:
                # Deployment doesn't exist, create it
                return self.provision_user_container(user_id)
            return {'status': 'error', 'message': f'Kubernetes API error: {e.reason}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def stop_container(self, container_id):
        """Stop user's container (scale to 0)"""
        if not self.k8s_enabled:
            return {'status': 'error', 'message': 'Kubernetes not available'}

        try:
            # Scale deployment to 0 replicas
            deployment = self.apps_v1.read_namespaced_deployment(
                name=container_id,
                namespace=self.namespace
            )

            deployment.spec.replicas = 0

            self.apps_v1.patch_namespaced_deployment(
                name=container_id,
                namespace=self.namespace,
                body=deployment
            )

            return {'status': 'success', 'message': 'Container stopped'}

        except ApiException as e:
            return {'status': 'error', 'message': f'Kubernetes API error: {e.reason}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_container_status(self, container_id):
        """Get container status"""
        if not self.k8s_enabled or not container_id:
            return 'inactive'

        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=container_id,
                namespace=self.namespace
            )

            replicas = deployment.spec.replicas or 0
            ready_replicas = deployment.status.ready_replicas or 0

            if replicas == 0:
                return 'inactive'
            elif ready_replicas == 0:
                return 'starting'
            elif ready_replicas < replicas:
                return 'starting'
            else:
                return 'running'

        except ApiException as e:
            if e.status == 404:
                return 'not_found'
            return 'error'
        except Exception:
            return 'error'

    def configure_opend(self, container_id, config):
        """Update OpenD configuration in container"""
        if not self.k8s_enabled:
            # Local development mode - simulate configuration by calling container API
            print(f"Local dev mode: OpenD config for container {container_id}")
            print(f"Config: {config}")

            # For local development, try to call the container's config API
            try:
                user_id = container_id.replace('moomoo-user-', '')
                container_url = self.get_container_service_url(user_id)

                # Transform config to match what the connector expects
                connector_config = {
                    'moomoo_username': config.get('moomoo_username') or config.get('host'),  # Try direct first, fallback to old mapping
                    'moomoo_password': config.get('moomoo_password') or config.get('port'),  # Try direct first, fallback to old mapping
                    'security_firm': config.get('security_firm', 'FUTUSG'),
                    'trade_market': config.get('trade_market', 'US'),
                    'configured': True
                }

                import requests
                response = requests.post(
                    f"{container_url}/config",
                    json=connector_config,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    return result if result.get('success') else {'status': 'error', 'message': 'Configuration failed'}
                else:
                    return {'status': 'error', 'message': f'Container config API returned {response.status_code}'}

            except Exception as e:
                print(f"Error configuring container: {e}")
                return {'status': 'success', 'message': 'OpenD configuration updated (local dev mode)'}

        # Extract user_id from container_id
        user_id = container_id.replace('moomoo-user-', '')
        secret_name = self._get_secret_name(user_id)

        try:
            # Transform configuration for real OpenD
            opend_config = {
                'moomoo_username': config.get('moomoo_username') or config.get('host'),  # Try direct first, fallback to old mapping
                'moomoo_password': config.get('moomoo_password') or config.get('port'),  # Try direct first, fallback to old mapping
                'security_firm': config.get('security_firm', 'FUTUSG'),
                'trade_market': config.get('trade_market', 'US'),
                'configured': True
            }

            # Update secret with new configuration
            self._create_user_secret(user_id, opend_config)

            # Restart deployment to pick up new config
            deployment = self.apps_v1.read_namespaced_deployment(
                name=container_id,
                namespace=self.namespace
            )

            # Add/update restart annotation to trigger rolling update
            if not deployment.spec.template.metadata.annotations:
                deployment.spec.template.metadata.annotations = {}

            deployment.spec.template.metadata.annotations['kubectl.kubernetes.io/restartedAt'] = datetime.utcnow().isoformat()

            self.apps_v1.patch_namespaced_deployment(
                name=container_id,
                namespace=self.namespace,
                body=deployment
            )

            return {'status': 'success', 'message': 'OpenD configuration updated'}

        except ApiException as e:
            return {'status': 'error', 'message': f'Kubernetes API error: {e.reason}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def cleanup_user_resources(self, user_id):
        """Clean up all resources for a user"""
        if not self.k8s_enabled:
            return

        deployment_name = self._get_deployment_name(user_id)
        secret_name = self._get_secret_name(user_id)

        try:
            # Delete deployment
            self.apps_v1.delete_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )

            # Delete secret
            self.core_v1.delete_namespaced_secret(
                name=secret_name,
                namespace=self.namespace
            )

        except ApiException:
            pass  # Resource might not exist

    def get_container_url(self, user_id):
        """Get the internal URL for user's container"""
        if not self.k8s_enabled:
            return None

        # Internal Kubernetes service URL
        container_name = self._get_deployment_name(user_id)
        return f"http://{container_name}.{self.namespace}.svc.cluster.local:8000"

    def trigger_data_sync(self, container_id, user_id):
        """Trigger data sync in user's container"""
        if not self.k8s_enabled:
            # For local development, use the new container-based sync
            from container_data_sync import sync_user_container_data
            container_url = self.get_container_service_url(user_id)
            return sync_user_container_data(user_id, container_url, lookback_days=730)

        try:
            # In production Kubernetes environment
            container_url = self.get_container_url(user_id)
            if not container_url:
                return {'status': 'error', 'message': 'Could not determine container URL'}

            # Use the container-based sync service
            from container_data_sync import sync_user_container_data
            return sync_user_container_data(user_id, container_url, lookback_days=730)

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_container_service_url(self, user_id):
        """Get the external/internal URL to access user's container API"""
        if not self.k8s_enabled:
            # Docker Compose development mode - use container name
            return f"http://moomoo-user-{user_id}:8000"

        # Production Kubernetes URL
        return self.get_container_url(user_id)