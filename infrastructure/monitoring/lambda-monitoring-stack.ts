import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface LambdaMonitoringStackProps extends cdk.StackProps {
  lambdaFunction: lambda.Function;
  alertEmail: string;
  environment: string;
}

export class LambdaMonitoringStack extends cdk.Stack {
  public readonly dashboard: cloudwatch.Dashboard;
  public readonly alarmTopic: sns.Topic;

  constructor(scope: Construct, id: string, props: LambdaMonitoringStackProps) {
    super(scope, id, props);

    const { lambdaFunction, alertEmail, environment } = props;

    // Create SNS topic for alerts
    this.alarmTopic = new sns.Topic(this, 'LambdaAlarmTopic', {
      displayName: `Lambda Performance Alerts - ${environment}`,
      topicName: `lambda-performance-alerts-${environment}`,
    });

    // Subscribe email to SNS topic
    this.alarmTopic.addSubscription(
      new snsSubscriptions.EmailSubscription(alertEmail)
    );

    // Create custom metrics for cold starts
    const coldStartMetric = this.createColdStartMetric(lambdaFunction);
    const initDurationMetric = this.createInitDurationMetric(lambdaFunction);
    const memoryUtilizationMetric = this.createMemoryUtilizationMetric(lambdaFunction);

    // Create CloudWatch alarms
    this.createPerformanceAlarms(
      lambdaFunction,
      coldStartMetric,
      initDurationMetric,
      memoryUtilizationMetric
    );

    // Create CloudWatch dashboard
    this.dashboard = this.createPerformanceDashboard(
      lambdaFunction,
      coldStartMetric,
      initDurationMetric,
      memoryUtilizationMetric,
      environment
    );

    // Create log insights queries for performance analysis
    this.createLogInsightsQueries(lambdaFunction);

    // Add X-Ray tracing for detailed performance analysis
    this.enableXRayTracing(lambdaFunction);
  }

  private createColdStartMetric(lambdaFunction: lambda.Function): cloudwatch.Metric {
    // Custom metric for cold start detection
    return new cloudwatch.Metric({
      namespace: 'AWS/Lambda/Performance',
      metricName: 'ColdStarts',
      dimensionsMap: {
        FunctionName: lambdaFunction.functionName,
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });
  }

  private createInitDurationMetric(lambdaFunction: lambda.Function): cloudwatch.Metric {
    // AWS Lambda built-in init duration metric
    return new cloudwatch.Metric({
      namespace: 'AWS/Lambda',
      metricName: 'InitDuration',
      dimensionsMap: {
        FunctionName: lambdaFunction.functionName,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(5),
    });
  }

  private createMemoryUtilizationMetric(lambdaFunction: lambda.Function): cloudwatch.Metric {
    // Custom metric for memory utilization percentage
    return new cloudwatch.Metric({
      namespace: 'AWS/Lambda/Performance',
      metricName: 'MemoryUtilization',
      dimensionsMap: {
        FunctionName: lambdaFunction.functionName,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(5),
    });
  }

  private createPerformanceAlarms(
    lambdaFunction: lambda.Function,
    coldStartMetric: cloudwatch.Metric,
    initDurationMetric: cloudwatch.Metric,
    memoryUtilizationMetric: cloudwatch.Metric
  ) {
    // Cold start frequency alarm
    new cloudwatch.Alarm(this, 'HighColdStartRate', {
      alarmName: `${lambdaFunction.functionName}-high-cold-start-rate`,
      alarmDescription: 'High cold start rate detected',
      metric: coldStartMetric,
      threshold: 10, // More than 10 cold starts in 5 minutes
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    }).addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(this.alarmTopic));

    // Init duration alarm
    new cloudwatch.Alarm(this, 'HighInitDuration', {
      alarmName: `${lambdaFunction.functionName}-high-init-duration`,
      alarmDescription: 'High Lambda initialization duration',
      metric: initDurationMetric,
      threshold: 2000, // 2 seconds
      evaluationPeriods: 3,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    }).addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(this.alarmTopic));

    // Memory utilization alarm
    new cloudwatch.Alarm(this, 'HighMemoryUtilization', {
      alarmName: `${lambdaFunction.functionName}-high-memory-utilization`,
      alarmDescription: 'High memory utilization detected',
      metric: memoryUtilizationMetric,
      threshold: 85, // 85% memory utilization
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    }).addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(this.alarmTopic));

    // Duration alarm (response time)
    const durationAlarm = lambdaFunction.metricDuration({
      statistic: 'Average',
      period: cdk.Duration.minutes(5),
    }).createAlarm(this, 'HighDuration', {
      alarmName: `${lambdaFunction.functionName}-high-duration`,
      alarmDescription: 'High Lambda execution duration',
      threshold: 5000, // 5 seconds
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
    });
    durationAlarm.addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(this.alarmTopic));

    // Error rate alarm
    const errorRateAlarm = lambdaFunction.metricErrors({
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    }).createAlarm(this, 'HighErrorRate', {
      alarmName: `${lambdaFunction.functionName}-high-error-rate`,
      alarmDescription: 'High Lambda error rate',
      threshold: 5, // More than 5 errors in 5 minutes
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
    });
    errorRateAlarm.addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(this.alarmTopic));
  }

  private createPerformanceDashboard(
    lambdaFunction: lambda.Function,
    coldStartMetric: cloudwatch.Metric,
    initDurationMetric: cloudwatch.Metric,
    memoryUtilizationMetric: cloudwatch.Metric,
    environment: string
  ): cloudwatch.Dashboard {
    const dashboard = new cloudwatch.Dashboard(this, 'LambdaPerformanceDashboard', {
      dashboardName: `lambda-performance-${environment}`,
    });

    // Row 1: Overview metrics
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Invocations and Errors',
        left: [
          lambdaFunction.metricInvocations({
            statistic: 'Sum',
            period: cdk.Duration.minutes(5),
          }),
        ],
        right: [
          lambdaFunction.metricErrors({
            statistic: 'Sum',
            period: cdk.Duration.minutes(5),
          }),
        ],
        width: 12,
        height: 6,
      }),
      new cloudwatch.SingleValueWidget({
        title: 'Success Rate',
        metrics: [
          new cloudwatch.MathExpression({
            expression: '(invocations - errors) / invocations * 100',
            usingMetrics: {
              invocations: lambdaFunction.metricInvocations({
                statistic: 'Sum',
                period: cdk.Duration.minutes(5),
              }),
              errors: lambdaFunction.metricErrors({
                statistic: 'Sum',
                period: cdk.Duration.minutes(5),
              }),
            },
          }),
        ],
        width: 6,
        height: 6,
      }),
      new cloudwatch.SingleValueWidget({
        title: 'Average Duration (ms)',
        metrics: [
          lambdaFunction.metricDuration({
            statistic: 'Average',
            period: cdk.Duration.minutes(5),
          }),
        ],
        width: 6,
        height: 6,
      })
    );

    // Row 2: Cold start metrics
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Cold Starts',
        left: [coldStartMetric],
        width: 12,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Init Duration',
        left: [initDurationMetric],
        width: 12,
        height: 6,
      })
    );

    // Row 3: Resource utilization
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Memory Utilization',
        left: [memoryUtilizationMetric],
        width: 12,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Duration Percentiles',
        left: [
          lambdaFunction.metricDuration({
            statistic: 'p50',
            period: cdk.Duration.minutes(5),
          }),
          lambdaFunction.metricDuration({
            statistic: 'p90',
            period: cdk.Duration.minutes(5),
          }),
          lambdaFunction.metricDuration({
            statistic: 'p99',
            period: cdk.Duration.minutes(5),
          }),
        ],
        width: 12,
        height: 6,
      })
    );

    // Row 4: Concurrent executions and throttles
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Concurrent Executions',
        left: [
          lambdaFunction.metricConcurrentExecutions({
            statistic: 'Maximum',
            period: cdk.Duration.minutes(5),
          }),
        ],
        width: 12,
        height: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Throttles',
        left: [
          lambdaFunction.metricThrottles({
            statistic: 'Sum',
            period: cdk.Duration.minutes(5),
          }),
        ],
        width: 12,
        height: 6,
      })
    );

    return dashboard;
  }

  private createLogInsightsQueries(lambdaFunction: lambda.Function) {
    // Create CloudWatch Logs Insights queries for performance analysis
    const logGroup = lambdaFunction.logGroup;

    // Cold start analysis query
    new logs.QueryDefinition(this, 'ColdStartAnalysis', {
      queryDefinitionName: `${lambdaFunction.functionName}-cold-start-analysis`,
      queryString: `
        fields @timestamp, @requestId, @duration, @initDuration, @memorySize, @maxMemoryUsed
        | filter @type = "REPORT"
        | filter ispresent(@initDuration)
        | stats count() as coldStarts, avg(@initDuration) as avgInitDuration, max(@initDuration) as maxInitDuration
        | sort @timestamp desc
      `,
      logGroups: [logGroup],
    });

    // Performance bottleneck query
    new logs.QueryDefinition(this, 'PerformanceBottlenecks', {
      queryDefinitionName: `${lambdaFunction.functionName}-performance-bottlenecks`,
      queryString: `
        fields @timestamp, @requestId, @duration, @maxMemoryUsed, @message
        | filter @type = "REPORT"
        | filter @duration > 2000
        | sort @duration desc
        | limit 100
      `,
      logGroups: [logGroup],
    });

    // Memory usage analysis query
    new logs.QueryDefinition(this, 'MemoryUsageAnalysis', {
      queryDefinitionName: `${lambdaFunction.functionName}-memory-usage`,
      queryString: `
        fields @timestamp, @requestId, @memorySize, @maxMemoryUsed
        | filter @type = "REPORT"
        | stats avg(@maxMemoryUsed) as avgMemoryUsed, max(@maxMemoryUsed) as maxMemoryUsed, 
                avg(@maxMemoryUsed/@memorySize*100) as avgMemoryUtilization
        | sort @timestamp desc
      `,
      logGroups: [logGroup],
    });
  }

  private enableXRayTracing(lambdaFunction: lambda.Function) {
    // Enable X-Ray tracing for detailed performance analysis
    lambdaFunction.addEnvironment('_X_AMZN_TRACE_ID', 'Root=1-00000000-000000000000000000000000');
    
    // Add X-Ray permissions
    lambdaFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'xray:PutTraceSegments',
        'xray:PutTelemetryRecords',
      ],
      resources: ['*'],
    }));
  }
}
