import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface LambdaWarmerStackProps extends cdk.StackProps {
  targetLambdaFunction: lambda.Function;
  warmingSchedule?: string; // Cron expression
  concurrentWarmingRequests?: number;
  environment: string;
}

export class LambdaWarmerStack extends cdk.Stack {
  public readonly warmerFunction: lambda.Function;
  public readonly warmerRule: events.Rule;

  constructor(scope: Construct, id: string, props: LambdaWarmerStackProps) {
    super(scope, id, props);

    const { 
      targetLambdaFunction, 
      warmingSchedule = 'rate(5 minutes)', // Default: every 5 minutes
      concurrentWarmingRequests = 3, // Default: 3 concurrent instances
      environment 
    } = props;

    // Create the warmer Lambda function
    this.warmerFunction = new lambda.Function(this, 'LambdaWarmer', {
      functionName: `lambda-warmer-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_warmer.handler',
      code: lambda.Code.fromInline(this.getWarmerCode()),
      timeout: cdk.Duration.seconds(30),
      memorySize: 128,
      environment: {
        TARGET_FUNCTION_NAME: targetLambdaFunction.functionName,
        CONCURRENT_REQUESTS: concurrentWarmingRequests.toString(),
        ENVIRONMENT: environment,
      },
      description: `Lambda warmer for ${targetLambdaFunction.functionName}`,
    });

    // Grant permissions to invoke the target Lambda function
    targetLambdaFunction.grantInvoke(this.warmerFunction);

    // Add CloudWatch Logs permissions
    this.warmerFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['arn:aws:logs:*:*:*'],
    }));

    // Create EventBridge rule for scheduled warming
    this.warmerRule = new events.Rule(this, 'WarmerScheduleRule', {
      ruleName: `lambda-warmer-schedule-${environment}`,
      description: `Scheduled warming for ${targetLambdaFunction.functionName}`,
      schedule: events.Schedule.expression(warmingSchedule),
    });

    // Add the warmer function as target
    this.warmerRule.addTarget(new targets.LambdaFunction(this.warmerFunction, {
      event: events.RuleTargetInput.fromObject({
        source: 'lambda-warmer',
        action: 'warm',
        target_function: targetLambdaFunction.functionName,
        concurrent_requests: concurrentWarmingRequests,
      }),
    }));

    // Create additional warming rules for different scenarios
    this.createConditionalWarmingRules(targetLambdaFunction, environment);

    // Add tags for cost tracking and management
    cdk.Tags.of(this).add('Service', 'LambdaWarmer');
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('CostCenter', 'Performance');
  }

  private createConditionalWarmingRules(targetFunction: lambda.Function, environment: string) {
    // Peak hours warming (more frequent during business hours)
    const peakHoursRule = new events.Rule(this, 'PeakHoursWarmerRule', {
      ruleName: `lambda-warmer-peak-hours-${environment}`,
      description: 'More frequent warming during peak hours',
      schedule: events.Schedule.expression('rate(2 minutes)'), // Every 2 minutes during peak
    });

    // Add condition to only run during business hours (9 AM to 6 PM UTC)
    peakHoursRule.addTarget(new targets.LambdaFunction(this.warmerFunction, {
      event: events.RuleTargetInput.fromObject({
        source: 'lambda-warmer-peak',
        action: 'conditional-warm',
        target_function: targetFunction.functionName,
        concurrent_requests: 5, // More concurrent requests during peak
        time_condition: 'business-hours',
      }),
    }));

    // Pre-deployment warming
    const preDeploymentRule = new events.Rule(this, 'PreDeploymentWarmerRule', {
      ruleName: `lambda-warmer-pre-deployment-${environment}`,
      description: 'Intensive warming before deployments',
      enabled: false, // Enabled manually before deployments
    });

    preDeploymentRule.addTarget(new targets.LambdaFunction(this.warmerFunction, {
      event: events.RuleTargetInput.fromObject({
        source: 'lambda-warmer-deployment',
        action: 'intensive-warm',
        target_function: targetFunction.functionName,
        concurrent_requests: 10,
        duration_minutes: 10,
      }),
    }));
  }

  private getWarmerCode(): string {
    return `
import json
import boto3
import asyncio
import aiohttp
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

lambda_client = boto3.client('lambda')

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda warmer function to prevent cold starts."""
    
    print(f"Lambda warmer invoked: {json.dumps(event)}")
    
    target_function = event.get('target_function') or os.environ['TARGET_FUNCTION_NAME']
    concurrent_requests = int(event.get('concurrent_requests', os.environ.get('CONCURRENT_REQUESTS', 3)))
    action = event.get('action', 'warm')
    
    try:
        if action == 'warm':
            result = warm_function(target_function, concurrent_requests)
        elif action == 'conditional-warm':
            result = conditional_warm(event, target_function, concurrent_requests)
        elif action == 'intensive-warm':
            result = intensive_warm(event, target_function, concurrent_requests)
        else:
            result = {'status': 'error', 'message': f'Unknown action: {action}'}
        
        print(f"Warming result: {json.dumps(result)}")
        return result
        
    except Exception as e:
        error_result = {
            'status': 'error',
            'message': str(e),
            'target_function': target_function,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        print(f"Warming error: {json.dumps(error_result)}")
        return error_result

def warm_function(function_name: str, concurrent_requests: int) -> Dict[str, Any]:
    """Warm the target function with concurrent requests."""
    
    warming_payload = {
        'source': 'lambda-warmer',
        'warming': True,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    successful_invocations = 0
    failed_invocations = 0
    
    # Use ThreadPoolExecutor for concurrent invocations
    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = []
        
        for i in range(concurrent_requests):
            future = executor.submit(invoke_function, function_name, warming_payload, i)
            futures.append(future)
        
        # Collect results
        for future in futures:
            try:
                result = future.result(timeout=25)  # 25 second timeout
                if result.get('success', False):
                    successful_invocations += 1
                else:
                    failed_invocations += 1
            except Exception as e:
                print(f"Invocation failed: {str(e)}")
                failed_invocations += 1
    
    return {
        'status': 'completed',
        'target_function': function_name,
        'successful_invocations': successful_invocations,
        'failed_invocations': failed_invocations,
        'total_requests': concurrent_requests,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

def conditional_warm(event: Dict[str, Any], function_name: str, concurrent_requests: int) -> Dict[str, Any]:
    """Conditionally warm based on time or other conditions."""
    
    time_condition = event.get('time_condition')
    current_hour = datetime.now(timezone.utc).hour
    
    # Business hours condition (9 AM to 6 PM UTC)
    if time_condition == 'business-hours':
        if not (9 <= current_hour <= 18):
            return {
                'status': 'skipped',
                'reason': 'Outside business hours',
                'current_hour': current_hour,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    # Proceed with warming
    return warm_function(function_name, concurrent_requests)

def intensive_warm(event: Dict[str, Any], function_name: str, concurrent_requests: int) -> Dict[str, Any]:
    """Intensive warming for pre-deployment scenarios."""
    
    duration_minutes = event.get('duration_minutes', 5)
    interval_seconds = 30  # Warm every 30 seconds
    
    results = []
    start_time = datetime.now(timezone.utc)
    
    while (datetime.now(timezone.utc) - start_time).seconds < (duration_minutes * 60):
        result = warm_function(function_name, concurrent_requests)
        results.append(result)
        
        # Wait before next warming cycle
        import time
        time.sleep(interval_seconds)
    
    # Aggregate results
    total_successful = sum(r.get('successful_invocations', 0) for r in results)
    total_failed = sum(r.get('failed_invocations', 0) for r in results)
    
    return {
        'status': 'completed',
        'mode': 'intensive',
        'target_function': function_name,
        'duration_minutes': duration_minutes,
        'warming_cycles': len(results),
        'total_successful_invocations': total_successful,
        'total_failed_invocations': total_failed,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

def invoke_function(function_name: str, payload: Dict[str, Any], request_id: int) -> Dict[str, Any]:
    """Invoke the target Lambda function."""
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        status_code = response['StatusCode']
        
        if status_code == 200:
            # Check if it was a cold start by examining logs
            log_result = response.get('LogResult', '')
            if log_result:
                import base64
                logs = base64.b64decode(log_result).decode('utf-8')
                cold_start = 'INIT_START' in logs
            else:
                cold_start = None
            
            return {
                'success': True,
                'status_code': status_code,
                'request_id': request_id,
                'cold_start': cold_start,
                'execution_duration': response.get('ExecutedVersion', 'unknown')
            }
        else:
            return {
                'success': False,
                'status_code': status_code,
                'request_id': request_id,
                'error': 'Non-200 status code'
            }
            
    except Exception as e:
        return {
            'success': False,
            'request_id': request_id,
            'error': str(e)
        }
`;
  }
}`;
  }
}
