"""
Performance monitoring middleware for Lambda functions.

This middleware tracks cold starts, execution times, memory usage,
and publishes custom CloudWatch metrics for monitoring.
"""

import json
import time
import os
import psutil
from datetime import datetime, timezone
from functools import wraps
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager

import boto3
from botocore.exceptions import ClientError


class PerformanceMonitor:
    """Performance monitoring and metrics collection for Lambda functions."""
    
    def __init__(self, function_name: Optional[str] = None):
        self.function_name = function_name or os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'unknown')
        try:
            self.cloudwatch = boto3.client('cloudwatch')
            self.cloudwatch_available = True
        except Exception as e:
            print(f"CloudWatch not available: {e}")
            self.cloudwatch = None
            self.cloudwatch_available = False
        self.is_cold_start = True
        self.start_time = None
        self.memory_size = int(os.environ.get('AWS_LAMBDA_FUNCTION_MEMORY_SIZE', '128'))
        
    def __call__(self, handler: Callable) -> Callable:
        """Decorator to wrap Lambda handlers with performance monitoring."""
        
        @wraps(handler)
        def wrapper(event: Dict[str, Any], context: Any) -> Any:
            # Record start time
            self.start_time = time.time()
            
            # Detect cold start
            cold_start = self.is_cold_start
            self.is_cold_start = False
            
            # Get initial memory usage
            initial_memory = self._get_memory_usage()
            
            try:
                # Execute the handler
                result = handler(event, context)
                
                # Calculate execution metrics
                execution_time = (time.time() - self.start_time) * 1000  # milliseconds
                final_memory = self._get_memory_usage()
                memory_used = final_memory - initial_memory
                memory_utilization = (final_memory / self.memory_size) * 100
                
                # Publish performance metrics
                self._publish_metrics({
                    'execution_time': execution_time,
                    'memory_used': memory_used,
                    'memory_utilization': memory_utilization,
                    'cold_start': cold_start,
                    'success': True
                })
                
                # Log performance data
                self._log_performance_data({
                    'cold_start': cold_start,
                    'execution_time_ms': execution_time,
                    'memory_utilization_percent': memory_utilization,
                    'request_id': getattr(context, 'aws_request_id', 'unknown'),
                    'status': 'success'
                })
                
                return result
                
            except Exception as e:
                # Calculate execution metrics for failed requests
                execution_time = (time.time() - self.start_time) * 1000
                final_memory = self._get_memory_usage()
                memory_utilization = (final_memory / self.memory_size) * 100
                
                # Publish error metrics
                self._publish_metrics({
                    'execution_time': execution_time,
                    'memory_utilization': memory_utilization,
                    'cold_start': cold_start,
                    'success': False,
                    'error': True
                })
                
                # Log error performance data
                self._log_performance_data({
                    'cold_start': cold_start,
                    'execution_time_ms': execution_time,
                    'memory_utilization_percent': memory_utilization,
                    'request_id': getattr(context, 'aws_request_id', 'unknown'),
                    'status': 'error',
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                })
                
                raise
                
        return wrapper
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0
    
    def _publish_metrics(self, metrics: Dict[str, Any]) -> None:
        """Publish custom metrics to CloudWatch."""
        if not self.cloudwatch_available:
            return
        try:
            metric_data = []
            timestamp = datetime.now(timezone.utc)
            
            # Cold start metric
            if metrics.get('cold_start', False):
                metric_data.append({
                    'MetricName': 'ColdStarts',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': timestamp,
                    'Dimensions': [
                        {
                            'Name': 'FunctionName',
                            'Value': self.function_name
                        }
                    ]
                })
            
            # Memory utilization metric
            if 'memory_utilization' in metrics:
                metric_data.append({
                    'MetricName': 'MemoryUtilization',
                    'Value': metrics['memory_utilization'],
                    'Unit': 'Percent',
                    'Timestamp': timestamp,
                    'Dimensions': [
                        {
                            'Name': 'FunctionName',
                            'Value': self.function_name
                        }
                    ]
                })
            
            # Execution time metric
            if 'execution_time' in metrics:
                metric_data.append({
                    'MetricName': 'ExecutionTime',
                    'Value': metrics['execution_time'],
                    'Unit': 'Milliseconds',
                    'Timestamp': timestamp,
                    'Dimensions': [
                        {
                            'Name': 'FunctionName',
                            'Value': self.function_name
                        }
                    ]
                })
            
            # Success/Error metrics
            if metrics.get('success', False):
                metric_data.append({
                    'MetricName': 'SuccessfulInvocations',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': timestamp,
                    'Dimensions': [
                        {
                            'Name': 'FunctionName',
                            'Value': self.function_name
                        }
                    ]
                })
            elif metrics.get('error', False):
                metric_data.append({
                    'MetricName': 'ErrorInvocations',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': timestamp,
                    'Dimensions': [
                        {
                            'Name': 'FunctionName',
                            'Value': self.function_name
                        }
                    ]
                })
            
            # Publish metrics in batches (CloudWatch limit is 20 per request)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace='AWS/Lambda/Performance',
                    MetricData=batch
                )
                
        except ClientError as e:
            print(f"Failed to publish CloudWatch metrics: {e}")
        except Exception as e:
            print(f"Unexpected error publishing metrics: {e}")
    
    def _log_performance_data(self, data: Dict[str, Any]) -> None:
        """Log structured performance data for CloudWatch Logs Insights."""
        performance_log = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'function_name': self.function_name,
            'type': 'PERFORMANCE_METRIC',
            **data
        }
        
        print(json.dumps(performance_log))


class ColdStartOptimizer:
    """Utilities for optimizing Lambda cold starts."""
    
    @staticmethod
    def warm_up_connections():
        """Pre-warm database and external service connections."""
        try:
            # Pre-warm database connection
            from database import get_db_connection
            db = get_db_connection()
            db.execute("SELECT 1").fetchone()
            print("Database connection warmed up")
            
        except Exception as e:
            print(f"Failed to warm up database connection: {e}")
        
        try:
            # Pre-warm Redis connection
            import redis
            redis_client = redis.Redis.from_url(os.environ.get('REDIS_URL', ''))
            redis_client.ping()
            print("Redis connection warmed up")
            
        except Exception as e:
            print(f"Failed to warm up Redis connection: {e}")
    
    @staticmethod
    def preload_modules():
        """Preload commonly used modules to reduce import time."""
        import importlib
        
        common_modules = [
            'json',
            'datetime',
            'uuid',
            'hashlib',
            'base64',
            'urllib.parse',
            'boto3',
            'fastapi',
            'pydantic'
        ]
        
        for module in common_modules:
            try:
                importlib.import_module(module)
            except ImportError:
                pass  # Module not available, skip
        
        print(f"Preloaded {len(common_modules)} common modules")


# Performance monitoring context manager
@contextmanager
def performance_context(operation_name: str):
    """Context manager for monitoring specific operations."""
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    try:
        yield
    finally:
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        duration = (end_time - start_time) * 1000  # milliseconds
        memory_delta = end_memory - start_memory
        
        performance_log = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'OPERATION_PERFORMANCE',
            'operation': operation_name,
            'duration_ms': duration,
            'memory_delta_mb': memory_delta
        }
        
        print(json.dumps(performance_log))


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for easy use
def monitor_performance(handler: Callable) -> Callable:
    """Convenience decorator for performance monitoring."""
    return performance_monitor(handler)


# Lambda initialization optimizations
def optimize_lambda_init():
    """Optimize Lambda initialization for reduced cold start time."""
    print("Optimizing Lambda initialization...")
    
    # Preload modules
    ColdStartOptimizer.preload_modules()
    
    # Warm up connections
    ColdStartOptimizer.warm_up_connections()
    
    print("Lambda initialization optimization complete")


# Initialize optimizations when module is imported
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    optimize_lambda_init()
