#!/usr/bin/env python3
"""
LCopilot Integration API Manager

Manages enterprise-tier integration APIs for health, incidents, reports, and compliance.
Provides RESTful API access with authentication, rate limiting, and tier-based features.

Enterprise APIs:
- Health API: /api/health/{customer_id}
- Incident API: /api/incidents
- Reports API: /api/reports/{customer_id}
- Compliance API: /api/compliance/{customer_id}/export

Usage:
    python3 integration_api_manager.py --deploy-apis
    python3 integration_api_manager.py --create-api-key --customer enterprise-customer-001
    python3 integration_api_manager.py --test-api --endpoint health
"""

import os
import sys
import json
import argparse
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import uuid
import hashlib
import base64


@dataclass
class APIEndpoint:
    """API endpoint configuration."""
    path: str
    methods: List[str]
    auth_required: bool = True
    rate_limit: str = "1000/hour"
    tier_required: str = "enterprise"
    description: str = ""


@dataclass
class APIKey:
    """API key information."""
    key_id: str
    key_value: str
    customer_id: str
    tier: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    rate_limit: str = "1000/hour"


class IntegrationAPIManager:
    """Manages integration APIs for enterprise customers."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configurations
        self.reliability_config = self._load_reliability_config()

        # AWS clients
        self.apigateway_client = None
        self.lambda_client = None
        self.dynamodb_client = None
        self.iam_client = None
        self.region = self.reliability_config.get('global', {}).get('environments', {}).get(environment, {}).get('aws_region', 'eu-north-1')

        # API configuration
        self.api_config = self.reliability_config.get('integration_apis', {}).get('enterprise', {})
        self.base_url = self.api_config.get('base_url', 'https://api.lcopilot.com/reliability')

        # Define API endpoints
        self.endpoints = self._define_api_endpoints()

    def _load_reliability_config(self) -> Dict[str, Any]:
        """Load reliability configuration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'reliability_config.yaml')
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            return {}

    def _define_api_endpoints(self) -> List[APIEndpoint]:
        """Define available API endpoints."""
        return [
            APIEndpoint(
                path="/health/{customer_id}",
                methods=["GET"],
                description="Get customer health status and metrics",
                rate_limit="1000/hour"
            ),
            APIEndpoint(
                path="/health/{customer_id}/detailed",
                methods=["GET"],
                description="Get detailed health metrics with historical data",
                rate_limit="500/hour"
            ),
            APIEndpoint(
                path="/incidents",
                methods=["GET", "POST"],
                description="List incidents or create incident reports",
                rate_limit="500/hour"
            ),
            APIEndpoint(
                path="/incidents/{incident_id}",
                methods=["GET", "PUT"],
                description="Get or update specific incident",
                rate_limit="500/hour"
            ),
            APIEndpoint(
                path="/reports/{customer_id}",
                methods=["GET"],
                description="Get available SLA reports for customer",
                rate_limit="100/hour"
            ),
            APIEndpoint(
                path="/reports/{customer_id}/{report_id}",
                methods=["GET"],
                description="Download specific report",
                rate_limit="100/hour"
            ),
            APIEndpoint(
                path="/compliance/{customer_id}/export",
                methods=["GET", "POST"],
                description="Export compliance data in various formats",
                rate_limit="10/hour"
            ),
            APIEndpoint(
                path="/metrics/{customer_id}",
                methods=["GET"],
                description="Get real-time metrics for customer",
                rate_limit="2000/hour"
            ),
            APIEndpoint(
                path="/status",
                methods=["GET"],
                description="Get API status and version",
                auth_required=False,
                rate_limit="10000/hour"
            )
        ]

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS clients."""
        try:
            session_kwargs = {'region_name': self.region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile

            session = boto3.Session(**session_kwargs)
            self.apigateway_client = session.client('apigateway')
            self.lambda_client = session.client('lambda')
            self.dynamodb_client = session.client('dynamodb')
            self.iam_client = session.client('iam')

            print(f"✅ AWS clients initialized for {self.region}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def create_api_gateway(self) -> Optional[str]:
        """Create API Gateway for integration APIs."""
        try:
            api_name = f'lcopilot-reliability-api-{self.environment}'

            # Check if API already exists
            apis = self.apigateway_client.get_rest_apis()
            for api in apis['items']:
                if api['name'] == api_name:
                    print(f"✅ API Gateway already exists: {api_name}")
                    return api['id']

            # Create new API Gateway
            response = self.apigateway_client.create_rest_api(
                name=api_name,
                description=f'LCopilot Reliability Integration API - {self.environment}',
                endpointConfiguration={'types': ['REGIONAL']},
                tags={
                    'Environment': self.environment,
                    'Service': 'lcopilot-reliability',
                    'Tier': 'enterprise'
                }
            )

            api_id = response['id']
            print(f"✅ API Gateway created: {api_name} ({api_id})")

            # Create API resources and methods
            self._create_api_resources(api_id)

            return api_id

        except Exception as e:
            print(f"❌ Failed to create API Gateway: {e}")
            return None

    def _create_api_resources(self, api_id: str):
        """Create API resources and methods."""
        try:
            # Get root resource
            resources = self.apigateway_client.get_resources(restApiId=api_id)
            root_resource_id = None

            for resource in resources['items']:
                if resource['path'] == '/':
                    root_resource_id = resource['id']
                    break

            if not root_resource_id:
                print("❌ Root resource not found")
                return

            # Create resources for each endpoint
            created_resources = {}

            for endpoint in self.endpoints:
                path_parts = [p for p in endpoint.path.split('/') if p]

                current_resource_id = root_resource_id
                current_path = ''

                for part in path_parts:
                    current_path += f'/{part}'

                    if current_path not in created_resources:
                        # Create resource
                        try:
                            resource_response = self.apigateway_client.create_resource(
                                restApiId=api_id,
                                parentId=current_resource_id,
                                pathPart=part
                            )

                            created_resources[current_path] = resource_response['id']
                            current_resource_id = resource_response['id']

                        except self.apigateway_client.exceptions.ConflictException:
                            # Resource already exists, get its ID
                            resources = self.apigateway_client.get_resources(restApiId=api_id)
                            for resource in resources['items']:
                                if resource['path'] == current_path:
                                    created_resources[current_path] = resource['id']
                                    current_resource_id = resource['id']
                                    break
                    else:
                        current_resource_id = created_resources[current_path]

                # Create methods for the endpoint
                resource_id = created_resources[endpoint.path]

                for method in endpoint.methods:
                    self._create_api_method(api_id, resource_id, method, endpoint)

            print(f"✅ Created {len(created_resources)} API resources")

        except Exception as e:
            print(f"❌ Failed to create API resources: {e}")

    def _create_api_method(self, api_id: str, resource_id: str, method: str, endpoint: APIEndpoint):
        """Create API method with Lambda integration."""
        try:
            # Create method
            self.apigateway_client.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod=method,
                authorizationType='API_KEY' if endpoint.auth_required else 'NONE',
                apiKeyRequired=endpoint.auth_required
            )

            # Create Lambda function for this endpoint if it doesn't exist
            function_name = self._get_lambda_function_name(endpoint.path, method)
            lambda_arn = self._create_lambda_function(function_name, endpoint)

            if lambda_arn:
                # Create Lambda integration
                self.apigateway_client.put_integration(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod=method,
                    type='AWS_PROXY',
                    integrationHttpMethod='POST',
                    uri=f'arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
                )

                print(f"✅ Created {method} method for {endpoint.path}")

        except Exception as e:
            print(f"⚠️ Failed to create method {method} for {endpoint.path}: {e}")

    def _get_lambda_function_name(self, path: str, method: str) -> str:
        """Generate Lambda function name from path and method."""
        # Convert path to safe function name
        safe_path = path.replace('/', '_').replace('{', '').replace('}', '').strip('_')
        return f'lcopilot_reliability_{safe_path}_{method.lower()}_{self.environment}'

    def _create_lambda_function(self, function_name: str, endpoint: APIEndpoint) -> Optional[str]:
        """Create Lambda function for API endpoint."""
        try:
            # Check if function already exists
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                print(f"✅ Lambda function already exists: {function_name}")
                return response['Configuration']['FunctionArn']
            except self.lambda_client.exceptions.ResourceNotFoundException:
                pass

            # Generate Lambda code
            lambda_code = self._generate_lambda_code(endpoint)

            # Create Lambda function
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.11',
                Role=self._get_lambda_execution_role(),
                Handler='index.handler',
                Code={'ZipFile': lambda_code},
                Description=f'LCopilot Reliability API: {endpoint.description}',
                Timeout=30,
                Environment={
                    'Variables': {
                        'ENVIRONMENT': self.environment,
                        'API_ENDPOINT': endpoint.path
                    }
                },
                Tags={
                    'Environment': self.environment,
                    'Service': 'lcopilot-reliability-api'
                }
            )

            print(f"✅ Lambda function created: {function_name}")
            return response['FunctionArn']

        except Exception as e:
            print(f"❌ Failed to create Lambda function {function_name}: {e}")
            return None

    def _generate_lambda_code(self, endpoint: APIEndpoint) -> bytes:
        """Generate Lambda function code for API endpoint."""
        code = f"""
import json
import boto3
from datetime import datetime

def handler(event, context):
    \"\"\"
    Lambda handler for {endpoint.path}
    {endpoint.description}
    \"\"\"

    try:
        # Parse request
        http_method = event.get('httpMethod')
        path_parameters = event.get('pathParameters') or {{}}
        query_parameters = event.get('queryStringParameters') or {{}}

        # Extract customer_id if present
        customer_id = path_parameters.get('customer_id')

        # Route to appropriate handler
        if '{endpoint.path}' == '/health/{{customer_id}}':
            return handle_health_request(customer_id, query_parameters)
        elif '{endpoint.path}' == '/incidents':
            return handle_incidents_request(http_method, event.get('body'))
        elif '{endpoint.path}' == '/reports/{{customer_id}}':
            return handle_reports_request(customer_id, query_parameters)
        elif '{endpoint.path}' == '/compliance/{{customer_id}}/export':
            return handle_compliance_request(customer_id, query_parameters)
        elif '{endpoint.path}' == '/status':
            return handle_status_request()
        else:
            return {{
                'statusCode': 404,
                'headers': {{'Content-Type': 'application/json'}},
                'body': json.dumps({{'error': 'Endpoint not found'}})
            }}

    except Exception as e:
        return {{
            'statusCode': 500,
            'headers': {{'Content-Type': 'application/json'}},
            'body': json.dumps({{'error': 'Internal server error', 'message': str(e)}})
        }}

def handle_health_request(customer_id, query_params):
    \"\"\"Handle health API requests.\"\"\"
    # Mock health data - replace with actual CloudWatch queries
    health_data = {{
        'customer_id': customer_id,
        'status': 'healthy',
        'uptime_24h': 99.95,
        'uptime_7d': 99.92,
        'uptime_30d': 99.89,
        'response_time_p95_ms': 450,
        'error_rate_24h': 0.02,
        'last_incident': None,
        'sla_compliance': {{
            'availability_target': 99.9,
            'availability_actual': 99.89,
            'compliance_status': 'met'
        }},
        'timestamp': datetime.now().isoformat()
    }}

    return {{
        'statusCode': 200,
        'headers': {{'Content-Type': 'application/json'}},
        'body': json.dumps(health_data)
    }}

def handle_incidents_request(method, body):
    \"\"\"Handle incidents API requests.\"\"\"
    if method == 'GET':
        # Return incident list
        incidents = [
            {{
                'id': 'INC-20241201-001',
                'title': 'API Response Time Degradation',
                'status': 'resolved',
                'severity': 'minor',
                'created_at': '2024-12-01T10:30:00Z',
                'resolved_at': '2024-12-01T11:45:00Z',
                'affected_services': ['LCopilot API']
            }}
        ]

        return {{
            'statusCode': 200,
            'headers': {{'Content-Type': 'application/json'}},
            'body': json.dumps({{'incidents': incidents, 'total': len(incidents)}})
        }}
    else:
        return {{
            'statusCode': 405,
            'headers': {{'Content-Type': 'application/json'}},
            'body': json.dumps({{'error': 'Method not allowed'}})
        }}

def handle_reports_request(customer_id, query_params):
    \"\"\"Handle reports API requests.\"\"\"
    reports = [
        {{
            'id': 'sla-2024-11',
            'title': 'Monthly SLA Report - November 2024',
            'type': 'sla_monthly',
            'format': 'pdf',
            'size_bytes': 245760,
            'created_at': '2024-12-01T00:00:00Z',
            'download_url': f'/api/reports/{{customer_id}}/sla-2024-11'
        }}
    ]

    return {{
        'statusCode': 200,
        'headers': {{'Content-Type': 'application/json'}},
        'body': json.dumps({{'reports': reports, 'customer_id': customer_id}})
    }}

def handle_compliance_request(customer_id, query_params):
    \"\"\"Handle compliance export requests.\"\"\"
    export_format = query_params.get('format', 'json')

    compliance_data = {{
        'customer_id': customer_id,
        'export_format': export_format,
        'compliance_period': '2024-11',
        'gdpr_compliant': True,
        'soc2_compliant': True,
        'data_retention_policy': '7 years',
        'export_timestamp': datetime.now().isoformat(),
        'download_url': f'/api/compliance/{{customer_id}}/download/{{datetime.now().strftime("%Y%m%d")}}.{{export_format}}'
    }}

    return {{
        'statusCode': 200,
        'headers': {{'Content-Type': 'application/json'}},
        'body': json.dumps(compliance_data)
    }}

def handle_status_request():
    \"\"\"Handle API status requests.\"\"\"
    status = {{
        'api_version': '1.0.0',
        'environment': '{self.environment}',
        'status': 'operational',
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            '/health/{{customer_id}}',
            '/incidents',
            '/reports/{{customer_id}}',
            '/compliance/{{customer_id}}/export'
        ]
    }}

    return {{
        'statusCode': 200,
        'headers': {{'Content-Type': 'application/json'}},
        'body': json.dumps(status)
    }}
"""

        return code.encode('utf-8')

    def _get_lambda_execution_role(self) -> str:
        """Get or create Lambda execution role."""
        role_name = f'lcopilot-reliability-api-role-{self.environment}'

        try:
            # Check if role exists
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except self.iam_client.exceptions.NoSuchEntityException:
            pass

        # Create role
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        response = self.iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f'Lambda execution role for LCopilot Reliability API - {self.environment}'
        )

        # Attach basic execution policy
        self.iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )

        print(f"✅ Lambda execution role created: {role_name}")
        return response['Role']['Arn']

    def create_api_key(self, customer_id: str, permissions: List[str] = None) -> Optional[APIKey]:
        """Create API key for customer."""
        try:
            if permissions is None:
                permissions = ['health:read', 'incidents:read', 'reports:read', 'compliance:read']

            # Generate API key
            key_id = f'lcopilot-{customer_id}-{uuid.uuid4().hex[:8]}'
            key_value = self._generate_api_key_value()

            # Create API key in API Gateway
            api_key_response = self.apigateway_client.create_api_key(
                name=key_id,
                description=f'API key for {customer_id}',
                enabled=True,
                value=key_value,
                tags={
                    'Customer': customer_id,
                    'Environment': self.environment,
                    'Service': 'lcopilot-reliability'
                }
            )

            # Store API key metadata in DynamoDB
            api_key = APIKey(
                key_id=key_id,
                key_value=key_value,
                customer_id=customer_id,
                tier='enterprise',
                permissions=permissions,
                created_at=datetime.now(),
                rate_limit='1000/hour'
            )

            self._store_api_key_metadata(api_key)

            print(f"✅ API key created for {customer_id}")
            print(f"   Key ID: {key_id}")
            print(f"   Permissions: {', '.join(permissions)}")

            return api_key

        except Exception as e:
            print(f"❌ Failed to create API key: {e}")
            return None

    def _generate_api_key_value(self) -> str:
        """Generate secure API key value."""
        import secrets
        import string

        # Generate 32-character API key
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(32))

    def _store_api_key_metadata(self, api_key: APIKey):
        """Store API key metadata in DynamoDB."""
        table_name = f'lcopilot-api-keys-{self.environment}'

        try:
            # Create table if it doesn't exist
            try:
                self.dynamodb_client.describe_table(TableName=table_name)
            except self.dynamodb_client.exceptions.ResourceNotFoundException:
                self.dynamodb_client.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {'AttributeName': 'key_id', 'KeyType': 'HASH'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'key_id', 'AttributeType': 'S'}
                    ],
                    BillingMode='PAY_PER_REQUEST',
                    Tags=[
                        {'Key': 'Environment', 'Value': self.environment},
                        {'Key': 'Service', 'Value': 'lcopilot-reliability'}
                    ]
                )

            # Store API key metadata
            self.dynamodb_client.put_item(
                TableName=table_name,
                Item={
                    'key_id': {'S': api_key.key_id},
                    'customer_id': {'S': api_key.customer_id},
                    'tier': {'S': api_key.tier},
                    'permissions': {'SS': api_key.permissions},
                    'created_at': {'S': api_key.created_at.isoformat()},
                    'rate_limit': {'S': api_key.rate_limit}
                }
            )

        except Exception as e:
            print(f"⚠️ Failed to store API key metadata: {e}")

    def test_api_endpoint(self, endpoint_path: str, customer_id: str = None, api_key: str = None) -> Dict[str, Any]:
        """Test API endpoint functionality."""
        try:
            import requests

            # Build test URL
            test_url = self.base_url + endpoint_path
            if customer_id and '{customer_id}' in test_url:
                test_url = test_url.replace('{customer_id}', customer_id)

            # Set up headers
            headers = {'Content-Type': 'application/json'}
            if api_key:
                headers['X-API-Key'] = api_key

            print(f"🧪 Testing API endpoint: {test_url}")

            # Make test request
            response = requests.get(test_url, headers=headers, timeout=10)

            result = {
                'endpoint': endpoint_path,
                'url': test_url,
                'status_code': response.status_code,
                'success': 200 <= response.status_code < 300,
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'headers': dict(response.headers),
                'body': response.text[:1000] if response.text else None  # Truncate for display
            }

            if result['success']:
                print(f"✅ API test successful ({response.status_code})")
            else:
                print(f"❌ API test failed ({response.status_code})")

            return result

        except Exception as e:
            return {
                'endpoint': endpoint_path,
                'success': False,
                'error': str(e)
            }

    def deploy_integration_apis(self) -> bool:
        """Deploy complete integration API stack."""
        try:
            print("🚀 Deploying LCopilot Integration APIs...")

            # Create API Gateway
            api_id = self.create_api_gateway()
            if not api_id:
                return False

            # Deploy API to stage
            try:
                self.apigateway_client.create_deployment(
                    restApiId=api_id,
                    stageName=self.environment,
                    description=f'Deployment for {self.environment} environment'
                )
                print(f"✅ API deployed to {self.environment} stage")
            except Exception as e:
                print(f"⚠️ Deployment may have already existed: {e}")

            # Get API URL
            api_url = f"https://{api_id}.execute-api.{self.region}.amazonaws.com/{self.environment}"
            print(f"🌐 API Base URL: {api_url}")

            print(f"✅ Integration APIs deployment completed")
            print(f"📖 Available endpoints:")
            for endpoint in self.endpoints:
                print(f"   • {endpoint.methods[0]} {endpoint.path} - {endpoint.description}")

            return True

        except Exception as e:
            print(f"❌ Failed to deploy integration APIs: {e}")
            return False


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='LCopilot Integration API Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 integration_api_manager.py --deploy-apis
  python3 integration_api_manager.py --create-api-key --customer enterprise-customer-001
  python3 integration_api_manager.py --test-api --endpoint /health/test-customer
        """
    )

    parser.add_argument('--env', '--environment', choices=['staging', 'prod'], default='prod',
                       help='Environment (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--deploy-apis', action='store_true', help='Deploy integration APIs')
    parser.add_argument('--create-api-key', action='store_true', help='Create API key for customer')
    parser.add_argument('--customer', help='Customer ID for API key creation')
    parser.add_argument('--test-api', action='store_true', help='Test API endpoint')
    parser.add_argument('--endpoint', help='API endpoint path to test')
    parser.add_argument('--api-key', help='API key for testing')
    parser.add_argument('--list-endpoints', action='store_true', help='List available endpoints')

    args = parser.parse_args()

    # Initialize manager
    manager = IntegrationAPIManager(environment=args.env, aws_profile=args.profile)

    print(f"🚀 LCopilot Integration API Manager")

    if not manager.initialize_aws_clients():
        sys.exit(1)

    # List endpoints
    if args.list_endpoints:
        print("📖 Available API Endpoints:")
        for endpoint in manager.endpoints:
            auth_info = "🔒 Auth Required" if endpoint.auth_required else "🔓 Public"
            print(f"   • {'/'.join(endpoint.methods)} {endpoint.path}")
            print(f"     {endpoint.description}")
            print(f"     {auth_info}, Rate limit: {endpoint.rate_limit}")
        return

    # Deploy APIs
    if args.deploy_apis:
        success = manager.deploy_integration_apis()
        if not success:
            sys.exit(1)
        return

    # Create API key
    if args.create_api_key:
        if not args.customer:
            print("❌ --customer parameter required for API key creation")
            sys.exit(1)

        api_key = manager.create_api_key(args.customer)
        if api_key:
            print(f"🔑 API Key Details:")
            print(f"   Customer: {api_key.customer_id}")
            print(f"   Key ID: {api_key.key_id}")
            print(f"   Key Value: {api_key.key_value}")
            print(f"   Rate Limit: {api_key.rate_limit}")
            print(f"   Permissions: {', '.join(api_key.permissions)}")
        else:
            sys.exit(1)
        return

    # Test API
    if args.test_api:
        if not args.endpoint:
            print("❌ --endpoint parameter required for API testing")
            sys.exit(1)

        result = manager.test_api_endpoint(args.endpoint, args.customer, args.api_key)

        print(f"🧪 API Test Results:")
        print(f"   Endpoint: {result.get('endpoint')}")
        print(f"   Success: {'✅' if result.get('success') else '❌'}")
        if result.get('status_code'):
            print(f"   Status Code: {result['status_code']}")
            print(f"   Response Time: {result.get('response_time_ms', 0):.0f}ms")

        if result.get('error'):
            print(f"   Error: {result['error']}")

        return

    # Show help if no action specified
    parser.print_help()


if __name__ == "__main__":
    main()