#!/usr/bin/env python3
"""
Enterprise Escalation Router Lambda Function

Routes CloudWatch alarms to appropriate escalation channels based on environment:
- Staging: Slack + Email
- Production: PagerDuty + Slack + Email

Supports:
- Slack webhook notifications
- PagerDuty Events API v2
- Email via SNS
- Custom webhook endpoints
- Message formatting and severity mapping

Environment Variables Required:
- ENVIRONMENT (staging|prod)
- SLACK_WEBHOOK_URL
- PAGERDUTY_INTEGRATION_KEY (prod only)
- EMAIL_SNS_TOPIC_ARN

Usage:
Deploy as Lambda function and connect to SNS topics
"""

import json
import os
import urllib3
from datetime import datetime
from typing import Dict, Any, List, Optional


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for escalation routing."""

    print(f"Received event: {json.dumps(event, indent=2)}")

    try:
        # Parse SNS message
        records = event.get('Records', [])
        if not records:
            print("No records found in event")
            return {'statusCode': 200, 'body': 'No records to process'}

        results = []
        for record in records:
            if record.get('EventSource') == 'aws:sns':
                sns_message = json.loads(record['Sns']['Message'])
                result = process_alarm(sns_message)
                results.append(result)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(results),
                'results': results
            })
        }

    except Exception as e:
        print(f"Error processing escalation: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }


def process_alarm(alarm_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process CloudWatch alarm and route to appropriate channels."""

    # Extract alarm information
    alarm_name = alarm_data.get('AlarmName', 'Unknown')
    new_state = alarm_data.get('NewStateValue', 'UNKNOWN')
    old_state = alarm_data.get('OldStateValue', 'UNKNOWN')
    reason = alarm_data.get('NewStateReason', 'No reason provided')
    timestamp = alarm_data.get('StateChangeTime', datetime.utcnow().isoformat())

    # Determine environment from alarm name
    environment = 'prod'
    if '-staging' in alarm_name:
        environment = 'staging'
    elif '-prod' in alarm_name:
        environment = 'prod'

    print(f"Processing alarm: {alarm_name} ({environment}) - {old_state} -> {new_state}")

    # Create formatted message
    message = format_alarm_message(alarm_data, environment)

    # Route based on environment and state
    routing_results = []

    # Always send to Slack
    slack_result = send_to_slack(message, new_state, environment)
    routing_results.append(slack_result)

    # Production-specific routing
    if environment == 'prod':
        if new_state == 'ALARM':
            # Critical production alarm - send to PagerDuty
            pagerduty_result = send_to_pagerduty(alarm_data, message)
            routing_results.append(pagerduty_result)

    # Send to additional channels based on severity
    if new_state in ['ALARM', 'INSUFFICIENT_DATA']:
        email_result = send_email_notification(message, environment)
        routing_results.append(email_result)

    return {
        'alarm_name': alarm_name,
        'environment': environment,
        'state_change': f"{old_state} -> {new_state}",
        'routing_results': routing_results
    }


def format_alarm_message(alarm_data: Dict[str, Any], environment: str) -> Dict[str, str]:
    """Format alarm data into structured message."""

    alarm_name = alarm_data.get('AlarmName', 'Unknown')
    new_state = alarm_data.get('NewStateValue', 'UNKNOWN')
    old_state = alarm_data.get('OldStateValue', 'UNKNOWN')
    reason = alarm_data.get('NewStateReason', 'No reason provided')
    timestamp = alarm_data.get('StateChangeTime', datetime.utcnow().isoformat())

    # Determine severity and emoji
    severity_info = get_severity_info(new_state, environment)

    # Create different message formats
    return {
        'title': f"{severity_info['emoji']} {environment.upper()} Alert: {alarm_name}",
        'summary': f"CloudWatch alarm {alarm_name} changed from {old_state} to {new_state}",
        'details': {
            'environment': environment.upper(),
            'alarm_name': alarm_name,
            'state_change': f"{old_state} → {new_state}",
            'reason': reason,
            'timestamp': timestamp,
            'severity': severity_info['level'],
            'aws_region': alarm_data.get('Region', 'unknown'),
            'account_id': alarm_data.get('AWSAccountId', 'unknown')
        },
        'slack_text': create_slack_message(alarm_name, new_state, old_state, reason, environment, severity_info),
        'pagerduty_summary': f"{environment.upper()}: {alarm_name} is {new_state}",
        'email_subject': f"[{environment.upper()}] CloudWatch Alert: {alarm_name} - {new_state}"
    }


def get_severity_info(state: str, environment: str) -> Dict[str, str]:
    """Get severity information based on state and environment."""

    severity_map = {
        'ALARM': {
            'level': 'critical' if environment == 'prod' else 'warning',
            'emoji': '🚨' if environment == 'prod' else '⚠️',
            'color': '#ff0000' if environment == 'prod' else '#ff9900'
        },
        'OK': {
            'level': 'info',
            'emoji': '✅',
            'color': '#00ff00'
        },
        'INSUFFICIENT_DATA': {
            'level': 'warning',
            'emoji': '📊',
            'color': '#ffcc00'
        }
    }

    return severity_map.get(state, {
        'level': 'unknown',
        'emoji': '❓',
        'color': '#808080'
    })


def create_slack_message(alarm_name: str, new_state: str, old_state: str, reason: str,
                        environment: str, severity_info: Dict[str, str]) -> str:
    """Create formatted Slack message."""

    return f"""
{severity_info['emoji']} *{environment.upper()} CloudWatch Alert*

*Alarm:* `{alarm_name}`
*State Change:* {old_state} → *{new_state}*
*Environment:* {environment.upper()}
*Severity:* {severity_info['level'].upper()}
*Reason:* {reason}
*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

*Next Steps:*
• Check CloudWatch dashboard for details
• Review application logs for root cause
• Update team if resolution expected time > 15min
    """.strip()


def send_to_slack(message: Dict[str, str], state: str, environment: str) -> Dict[str, Any]:
    """Send notification to Slack webhook."""

    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not webhook_url:
        return {'channel': 'slack', 'status': 'skipped', 'reason': 'No webhook URL configured'}

    try:
        http = urllib3.PoolManager()

        # Get severity info for color
        severity_info = get_severity_info(state, environment)

        slack_payload = {
            'text': message['title'],
            'attachments': [
                {
                    'color': severity_info['color'],
                    'title': f"Environment: {environment.upper()}",
                    'text': message['slack_text'],
                    'footer': 'LCopilot Monitoring',
                    'ts': int(datetime.utcnow().timestamp())
                }
            ]
        }

        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(slack_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        if response.status == 200:
            return {'channel': 'slack', 'status': 'success', 'response_code': response.status}
        else:
            return {'channel': 'slack', 'status': 'failed', 'response_code': response.status}

    except Exception as e:
        print(f"Failed to send Slack notification: {str(e)}")
        return {'channel': 'slack', 'status': 'error', 'error': str(e)}


def send_to_pagerduty(alarm_data: Dict[str, Any], message: Dict[str, str]) -> Dict[str, Any]:
    """Send critical alert to PagerDuty."""

    integration_key = os.environ.get('PAGERDUTY_INTEGRATION_KEY')
    if not integration_key:
        return {'channel': 'pagerduty', 'status': 'skipped', 'reason': 'No integration key configured'}

    try:
        http = urllib3.PoolManager()

        # Create PagerDuty event
        event_action = 'trigger' if alarm_data.get('NewStateValue') == 'ALARM' else 'resolve'

        pagerduty_payload = {
            'routing_key': integration_key,
            'event_action': event_action,
            'dedup_key': f"lcopilot-{alarm_data.get('AlarmName', 'unknown')}",
            'payload': {
                'summary': message['pagerduty_summary'],
                'source': f"CloudWatch-{alarm_data.get('Region', 'unknown')}",
                'severity': 'critical',
                'component': 'LCopilot API',
                'group': 'Production Monitoring',
                'class': 'CloudWatch Alarm',
                'custom_details': {
                    'alarm_name': alarm_data.get('AlarmName'),
                    'reason': alarm_data.get('NewStateReason'),
                    'aws_account': alarm_data.get('AWSAccountId'),
                    'region': alarm_data.get('Region'),
                    'timestamp': alarm_data.get('StateChangeTime')
                }
            }
        }

        response = http.request(
            'POST',
            'https://events.pagerduty.com/v2/enqueue',
            body=json.dumps(pagerduty_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        if response.status == 202:  # PagerDuty accepts with 202
            return {'channel': 'pagerduty', 'status': 'success', 'response_code': response.status}
        else:
            return {'channel': 'pagerduty', 'status': 'failed', 'response_code': response.status}

    except Exception as e:
        print(f"Failed to send PagerDuty notification: {str(e)}")
        return {'channel': 'pagerduty', 'status': 'error', 'error': str(e)}


def send_email_notification(message: Dict[str, str], environment: str) -> Dict[str, Any]:
    """Send email notification via SNS."""

    email_topic_arn = os.environ.get('EMAIL_SNS_TOPIC_ARN')
    if not email_topic_arn:
        return {'channel': 'email', 'status': 'skipped', 'reason': 'No email topic ARN configured'}

    try:
        import boto3
        sns = boto3.client('sns')

        # Create email body
        email_body = f"""
LCopilot CloudWatch Alert Notification

{message['summary']}

Environment: {environment.upper()}
Alarm: {message['details']['alarm_name']}
State Change: {message['details']['state_change']}
Severity: {message['details']['severity'].upper()}
Reason: {message['details']['reason']}
Timestamp: {message['details']['timestamp']}
AWS Region: {message['details']['aws_region']}
Account ID: {message['details']['account_id']}

Next Steps:
1. Check the CloudWatch dashboard for detailed metrics
2. Review application logs for the root cause
3. Update the team if resolution is expected to take longer than 15 minutes

---
This is an automated notification from LCopilot Monitoring System.
        """.strip()

        response = sns.publish(
            TopicArn=email_topic_arn,
            Subject=message['email_subject'],
            Message=email_body
        )

        return {'channel': 'email', 'status': 'success', 'message_id': response.get('MessageId')}

    except Exception as e:
        print(f"Failed to send email notification: {str(e)}")
        return {'channel': 'email', 'status': 'error', 'error': str(e)}


# For local testing
if __name__ == "__main__":
    # Example test event
    test_event = {
        'Records': [
            {
                'EventSource': 'aws:sns',
                'Sns': {
                    'Message': json.dumps({
                        'AlarmName': 'lcopilot-error-spike-prod',
                        'NewStateValue': 'ALARM',
                        'OldStateValue': 'OK',
                        'NewStateReason': 'Threshold Crossed: 6 datapoints [6.0 (13/01/24 14:30:00)] were greater than the threshold (5.0).',
                        'StateChangeTime': '2024-01-13T14:30:15.123Z',
                        'Region': 'eu-north-1',
                        'AWSAccountId': '222222222222'
                    })
                }
            }
        ]
    }

    # Mock environment variables
    os.environ['SLACK_WEBHOOK_URL'] = 'https://hooks.slack.com/services/T00000000/B00000000/test'
    os.environ['PAGERDUTY_INTEGRATION_KEY'] = 'test-key'
    os.environ['EMAIL_SNS_TOPIC_ARN'] = 'arn:aws:sns:eu-north-1:222222222222:lcopilot-email-alerts'

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))