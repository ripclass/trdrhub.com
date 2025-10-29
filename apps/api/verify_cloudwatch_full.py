#!/usr/bin/env python3
"""
CloudWatch Verification Script for LCopilot API.

Verifies that:
1. Recent log events are reaching CloudWatch (lcopilot-backend log group)
2. Metric filter LCopilotErrorCount is incrementing properly

Usage:
    python3 verify_cloudwatch_full.py
"""

import boto3
import time
from datetime import datetime, timedelta, timezone

REGION = "eu-north-1"
LOG_GROUP = "lcopilot-backend"
NAMESPACE = "LCopilot"
METRIC_NAME = "LCopilotErrorCount"

def verify_logs(minutes=5):
    """Verify recent log events are reaching CloudWatch."""
    client = boto3.client("logs", region_name=REGION)
    start = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp() * 1000)

    streams = client.describe_log_streams(
        logGroupName=LOG_GROUP,
        orderBy="LastEventTime",
        descending=True,
        limit=1
    )
    if not streams["logStreams"]:
        return False, "❌ No log streams found"

    stream = streams["logStreams"][0]["logStreamName"]
    events = client.get_log_events(
        logGroupName=LOG_GROUP,
        logStreamName=stream,
        startTime=start,
        limit=20,
        startFromHead=False
    )
    if not events["events"]:
        return False, f"❌ No logs found in last {minutes} min"
    return True, f"✅ Found {len(events['events'])} log events"

def verify_metric(minutes=5):
    """Verify metric filter LCopilotErrorCount is incrementing."""
    client = boto3.client("cloudwatch", region_name=REGION)
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)

    resp = client.get_metric_statistics(
        Namespace=NAMESPACE,
        MetricName=METRIC_NAME,
        Dimensions=[],
        StartTime=start,
        EndTime=end,
        Period=60,
        Statistics=["Sum"]
    )
    datapoints = resp.get("Datapoints", [])
    if not datapoints:
        return False, f"❌ No datapoints for {METRIC_NAME}"
    latest = max(datapoints, key=lambda x: x["Timestamp"])
    return True, f"✅ {METRIC_NAME} incremented by {latest['Sum']} at {latest['Timestamp']}"

if __name__ == "__main__":
    ok_logs, msg_logs = verify_logs()
    print(msg_logs)
    ok_metric, msg_metric = verify_metric()
    print(msg_metric)

    if ok_logs and ok_metric:
        print("🎉 CloudWatch pipeline fully verified!")
    else:
        print("⚠️ Partial verification failed — check setup.")