#!/usr/bin/env python3
"""
CloudWatch Logs Insights Query Manager

Manages predefined CloudWatch Logs Insights queries for enterprise monitoring.
Provides utilities for creating, updating, and executing saved queries.

Features:
- Predefined query templates for common log analysis
- Cross-environment query execution
- Cost-optimized query patterns
- Export results to various formats

Usage:
    python3 log_insights_manager.py --env prod --query TopErrorTypes
    python3 log_insights_manager.py --env staging --query ErrorFrequency --export csv
    python3 log_insights_manager.py --list-queries
"""

import os
import sys
import json
import argparse
import boto3
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv


class LogInsightsManager:
    """Manager for CloudWatch Logs Insights queries."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configuration
        self.config = self._load_config()
        self.env_config = self.config['environments'].get(environment, {})

        # Query templates
        self.query_templates = {
            'TopErrorTypes': {
                'name': 'Top Error Types',
                'description': 'Find the most common error types in the logs',
                'query': '''fields @timestamp, level, message
| filter level = "ERROR"
| stats count() as error_count by message
| sort error_count desc
| limit 20''',
                'cost_optimized': True
            },
            'ErrorFrequency': {
                'name': 'Error Frequency by Time',
                'description': 'Show error frequency over time (5-minute buckets)',
                'query': '''fields @timestamp, level
| filter level = "ERROR"
| stats count() as errors by bin(5m) as time_bucket
| sort time_bucket desc
| limit 288''',  # 24 hours of 5-minute buckets
                'cost_optimized': True
            },
            'ServiceErrorBreakdown': {
                'name': 'Service Error Breakdown',
                'description': 'Break down errors by service/component',
                'query': '''fields @timestamp, level, service, message
| filter level = "ERROR"
| stats count() as error_count by service
| sort error_count desc
| limit 50''',
                'cost_optimized': True
            },
            'ErrorDetails': {
                'name': 'Detailed Error Analysis',
                'description': 'Get detailed error information with context',
                'query': '''fields @timestamp, @message, level, service, error_code, stack_trace
| filter level = "ERROR"
| sort @timestamp desc
| limit 100''',
                'cost_optimized': False
            },
            'PerformanceMetrics': {
                'name': 'Performance Metrics',
                'description': 'Analyze response times and performance',
                'query': '''fields @timestamp, @message, response_time, endpoint
| filter ispresent(response_time)
| stats avg(response_time) as avg_response, max(response_time) as max_response, count() as requests by endpoint
| sort avg_response desc
| limit 20''',
                'cost_optimized': True
            },
            'SecurityEvents': {
                'name': 'Security Events',
                'description': 'Find potential security-related events',
                'query': '''fields @timestamp, @message, level, ip_address, user_agent
| filter @message like /authentication|authorization|login|failed|denied|blocked/
| sort @timestamp desc
| limit 50''',
                'cost_optimized': True
            },
            'HighVolumeErrors': {
                'name': 'High Volume Error Detection',
                'description': 'Identify error spikes by time period',
                'query': '''fields @timestamp, level
| filter level = "ERROR"
| stats count() as error_count by bin(1m) as time_minute
| sort error_count desc
| limit 100''',
                'cost_optimized': True
            }
        }

        # AWS clients
        self.logs_client = None
        self.region = self.env_config.get('aws_region', 'eu-north-1')

    def _load_config(self) -> Dict[str, Any]:
        """Load enterprise configuration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'enterprise_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'environments': {
                    'staging': {'aws_region': 'eu-north-1'},
                    'prod': {'aws_region': 'eu-north-1'}
                }
            }

    def initialize_aws_client(self) -> bool:
        """Initialize AWS CloudWatch Logs client."""
        try:
            session_kwargs = {'region_name': self.region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile

            session = boto3.Session(**session_kwargs)
            self.logs_client = session.client('logs')

            # Test connection
            self.logs_client.describe_log_groups(limit=1)
            print(f"✅ Connected to CloudWatch Logs in {self.region}")

            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS client: {e}")
            return False

    def list_saved_queries(self) -> List[Dict[str, Any]]:
        """List all saved query definitions."""
        try:
            response = self.logs_client.describe_query_definitions()
            return response.get('queryDefinitions', [])
        except Exception as e:
            print(f"❌ Failed to list saved queries: {e}")
            return []

    def create_saved_query(self, query_name: str, log_group_name: str) -> bool:
        """Create a saved query definition."""
        if query_name not in self.query_templates:
            print(f"❌ Unknown query template: {query_name}")
            return False

        template = self.query_templates[query_name]
        saved_name = f"lcopilot-{self.environment}-{query_name}"

        try:
            response = self.logs_client.put_query_definition(
                name=saved_name,
                queryString=template['query'],
                logGroupNames=[log_group_name]
            )

            print(f"✅ Created saved query: {saved_name}")
            print(f"   Query ID: {response['queryDefinitionId']}")
            return True

        except Exception as e:
            print(f"❌ Failed to create saved query: {e}")
            return False

    def execute_query(self, query_name: str, log_group_name: str,
                     hours_back: int = 24) -> Optional[Dict[str, Any]]:
        """Execute a query and return results."""
        if query_name not in self.query_templates:
            print(f"❌ Unknown query template: {query_name}")
            return None

        template = self.query_templates[query_name]

        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        print(f"🔍 Executing query: {template['name']}")
        print(f"   Description: {template['description']}")
        print(f"   Time range: {hours_back} hours ({start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')})")
        print(f"   Cost optimized: {'Yes' if template['cost_optimized'] else 'No'}")

        try:
            # Start query
            response = self.logs_client.start_query(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=template['query']
            )

            query_id = response['queryId']
            print(f"   Query ID: {query_id}")

            # Poll for results
            import time
            while True:
                result = self.logs_client.get_query_results(queryId=query_id)
                status = result['status']

                if status == 'Complete':
                    print(f"✅ Query completed successfully")
                    return {
                        'query_id': query_id,
                        'status': status,
                        'results': result['results'],
                        'statistics': result.get('statistics', {}),
                        'query_name': query_name,
                        'template': template
                    }
                elif status in ['Failed', 'Cancelled']:
                    print(f"❌ Query {status.lower()}")
                    return None
                else:
                    print(f"   Status: {status}...")
                    time.sleep(2)

        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            return None

    def format_results(self, results: Dict[str, Any], format_type: str = 'table') -> str:
        """Format query results for display."""
        if not results or not results.get('results'):
            return "No results found."

        query_results = results['results']
        statistics = results.get('statistics', {})

        # Format based on type
        if format_type == 'table':
            return self._format_table(query_results, results['template'])
        elif format_type == 'csv':
            return self._format_csv(query_results)
        elif format_type == 'json':
            return json.dumps(query_results, indent=2, default=str)
        else:
            return str(query_results)

    def _format_table(self, results: List[List[Dict]], template: Dict) -> str:
        """Format results as a table."""
        if not results:
            return "No results found."

        output = [f"\n📊 {template['name']} Results"]
        output.append("=" * 60)

        # Get headers from first row
        if results:
            headers = [field['field'] for field in results[0]]
            output.append(" | ".join(f"{h:<20}" for h in headers))
            output.append("-" * (22 * len(headers)))

            # Add data rows
            for row in results[:50]:  # Limit display to 50 rows
                values = [field['value'][:20] if field['value'] else '' for field in row]
                output.append(" | ".join(f"{v:<20}" for v in values))

            if len(results) > 50:
                output.append(f"... and {len(results) - 50} more rows")

        return "\n".join(output)

    def _format_csv(self, results: List[List[Dict]]) -> str:
        """Format results as CSV."""
        if not results:
            return ""

        output_lines = []

        # Headers
        headers = [field['field'] for field in results[0]]
        output_lines.append(','.join(headers))

        # Data
        for row in results:
            values = [field['value'] or '' for field in row]
            output_lines.append(','.join(f'"{v}"' for v in values))

        return '\n'.join(output_lines)

    def export_results(self, results: Dict[str, Any], filename: str, format_type: str = 'csv'):
        """Export results to file."""
        formatted_data = self.format_results(results, format_type)

        try:
            with open(filename, 'w') as f:
                f.write(formatted_data)
            print(f"✅ Results exported to {filename}")
        except Exception as e:
            print(f"❌ Failed to export results: {e}")

    def analyze_costs(self, query_name: str, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze estimated costs for running a query."""
        template = self.query_templates.get(query_name)
        if not template:
            return {}

        # Rough cost estimation (simplified)
        # CloudWatch Logs Insights charges per GB scanned
        base_cost_per_gb = 0.005  # USD per GB scanned

        estimated_log_size_gb = hours_back * 0.1  # Rough estimate: 100MB per hour
        estimated_cost = estimated_log_size_gb * base_cost_per_gb

        return {
            'query_name': query_name,
            'cost_optimized': template['cost_optimized'],
            'estimated_data_scanned_gb': estimated_log_size_gb,
            'estimated_cost_usd': estimated_cost,
            'hours_back': hours_back,
            'recommendations': [
                "Use specific time ranges to minimize data scanned",
                "Filter early in the query to reduce processing",
                "Consider using metric filters for frequent queries"
            ] if not template['cost_optimized'] else [
                "Query is already cost-optimized",
                "Consider saving frequently used queries"
            ]
        }


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='CloudWatch Logs Insights Query Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 log_insights_manager.py --list-templates
  python3 log_insights_manager.py --env prod --query TopErrorTypes
  python3 log_insights_manager.py --env staging --query ErrorFrequency --hours 12
  python3 log_insights_manager.py --env prod --query ServiceErrorBreakdown --export results.csv
  python3 log_insights_manager.py --query TopErrorTypes --analyze-cost
        """
    )

    parser.add_argument('--env', '--environment', choices=['staging', 'prod'],
                       default='prod', help='Environment (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--query', help='Query template to execute')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours back to query (default: 24)')
    parser.add_argument('--list-templates', action='store_true',
                       help='List available query templates')
    parser.add_argument('--list-saved', action='store_true',
                       help='List saved query definitions')
    parser.add_argument('--create-saved', action='store_true',
                       help='Create saved query definitions')
    parser.add_argument('--export', help='Export results to file (CSV format)')
    parser.add_argument('--format', choices=['table', 'csv', 'json'],
                       default='table', help='Output format (default: table)')
    parser.add_argument('--analyze-cost', action='store_true',
                       help='Analyze query costs')

    args = parser.parse_args()

    # List templates
    if args.list_templates:
        manager = LogInsightsManager()
        print("📚 Available Query Templates:")
        print("=" * 50)
        for name, template in manager.query_templates.items():
            cost_indicator = "💰" if not template['cost_optimized'] else "💚"
            print(f"{cost_indicator} {name}")
            print(f"   {template['description']}")
            print(f"   Cost optimized: {'Yes' if template['cost_optimized'] else 'No'}")
            print()
        return

    # Initialize manager
    manager = LogInsightsManager(environment=args.env, aws_profile=args.profile)

    if not manager.initialize_aws_client():
        sys.exit(1)

    # List saved queries
    if args.list_saved:
        saved_queries = manager.list_saved_queries()
        if saved_queries:
            print(f"📋 Saved Query Definitions ({len(saved_queries)}):")
            for query in saved_queries:
                print(f"   • {query['name']} (ID: {query['queryDefinitionId']})")
        else:
            print("No saved query definitions found.")
        return

    # Create saved queries
    if args.create_saved:
        log_group_name = f"/aws/lambda/lcopilot-{args.env}"
        print(f"🔧 Creating saved queries for log group: {log_group_name}")

        for query_name in manager.query_templates.keys():
            manager.create_saved_query(query_name, log_group_name)
        return

    # Analyze costs
    if args.analyze_cost and args.query:
        cost_analysis = manager.analyze_costs(args.query, args.hours)
        print(f"\n💰 Cost Analysis for {args.query}:")
        print(f"   Estimated data scanned: {cost_analysis['estimated_data_scanned_gb']:.2f} GB")
        print(f"   Estimated cost: ${cost_analysis['estimated_cost_usd']:.4f} USD")
        print(f"   Cost optimized: {'Yes' if cost_analysis['cost_optimized'] else 'No'}")
        print("   Recommendations:")
        for rec in cost_analysis['recommendations']:
            print(f"     • {rec}")
        return

    # Execute query
    if args.query:
        log_group_name = f"/aws/lambda/lcopilot-{args.env}"

        results = manager.execute_query(args.query, log_group_name, args.hours)
        if results:
            # Display results
            formatted_output = manager.format_results(results, args.format)
            print(formatted_output)

            # Export if requested
            if args.export:
                manager.export_results(results, args.export, 'csv')

            # Show statistics
            if results.get('statistics'):
                stats = results['statistics']
                print(f"\n📊 Query Statistics:")
                print(f"   Bytes scanned: {stats.get('bytesScanned', 'N/A')}")
                print(f"   Records matched: {stats.get('recordsMatched', 'N/A')}")
                print(f"   Records scanned: {stats.get('recordsScanned', 'N/A')}")
        return

    # Show help if no action specified
    parser.print_help()


if __name__ == "__main__":
    main()