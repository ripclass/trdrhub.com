"""
LCopilot Predictive Reliability Manager

Enterprise-only feature for ML-powered reliability forecasting and anomaly detection.
Provides predictive insights for system reliability, capacity planning, and proactive issue detection.

Features:
- Time series forecasting for service reliability
- Anomaly detection for early warning systems
- Capacity planning and resource optimization
- Predictive maintenance scheduling
- Risk assessment and mitigation recommendations
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import joblib
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class ForecastType(Enum):
    AVAILABILITY = "availability"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    CAPACITY = "capacity"
    COST = "cost"

class AnomalyType(Enum):
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    CAPACITY = "capacity"
    SECURITY = "security"

@dataclass
class PredictiveModel:
    model_id: str
    model_type: str
    target_metric: str
    accuracy_score: float
    last_trained: datetime
    training_data_size: int
    feature_importance: Dict[str, float]
    model_path: str

@dataclass
class ForecastPoint:
    timestamp: datetime
    metric_name: str
    predicted_value: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    confidence_level: float
    factors: List[str]

@dataclass
class Anomaly:
    timestamp: datetime
    anomaly_type: AnomalyType
    severity: str
    confidence: float
    description: str
    affected_services: List[str]
    predicted_impact: Dict[str, Any]
    recommended_actions: List[str]

@dataclass
class ReliabilityForecast:
    forecast_id: str
    customer_id: str
    forecast_type: ForecastType
    predictions: List[ForecastPoint]
    model_used: str
    generated_at: datetime
    forecast_horizon_hours: int
    accuracy_metrics: Dict[str, float]
    risk_factors: List[str]

@dataclass
class CapacityRecommendation:
    resource_type: str
    current_utilization: float
    predicted_utilization: float
    recommended_action: str
    confidence: float
    cost_impact: float
    timeline: str
    justification: str

class PredictiveReliabilityManager:
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.s3 = boto3.client('s3')
        self.cloudwatch = boto3.client('cloudwatch')
        self.sagemaker = boto3.client('sagemaker-runtime')

        self.config_path = Path(__file__).parent.parent / "config" / "reliability_config.yaml"
        self.reliability_config = self._load_reliability_config()

        self.models_bucket = f"lcopilot-ml-models-{environment}"
        self.predictions_bucket = f"lcopilot-predictions-{environment}"

        # Initialize ML models
        self.models = {}
        self.scalers = {}
        self.anomaly_detectors = {}

    def _load_reliability_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Reliability config not found at {self.config_path}")
            return {}

    def is_enterprise_customer(self, customer_id: str) -> bool:
        customer_config = self.reliability_config.get('customers', {}).get(customer_id, {})
        return customer_config.get('tier') == 'enterprise'

    def prepare_training_data(self, customer_id: str, metric_type: ForecastType,
                             days_back: int = 30) -> pd.DataFrame:
        if not self.is_enterprise_customer(customer_id):
            raise ValueError("Predictive reliability is only available for Enterprise tier")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)

        # Collect historical data
        data_points = []

        try:
            # Get CloudWatch metrics
            metrics = self._collect_cloudwatch_data(customer_id, metric_type, start_time, end_time)

            # Get system events and deployments
            events = self._collect_system_events(customer_id, start_time, end_time)

            # Get external factors (holidays, business events, etc.)
            external_factors = self._collect_external_factors(start_time, end_time)

            # Combine all data sources
            df = self._merge_data_sources(metrics, events, external_factors)

            logger.info(f"Prepared {len(df)} training samples for {metric_type.value}")
            return df

        except Exception as e:
            logger.error(f"Failed to prepare training data: {str(e)}")
            return pd.DataFrame()

    def _collect_cloudwatch_data(self, customer_id: str, metric_type: ForecastType,
                                start_time: datetime, end_time: datetime) -> pd.DataFrame:
        metric_mapping = {
            ForecastType.AVAILABILITY: {
                'namespace': 'AWS/ApiGateway',
                'metric_name': 'Count',
                'stat': 'Sum'
            },
            ForecastType.RESPONSE_TIME: {
                'namespace': 'AWS/ApiGateway',
                'metric_name': 'Latency',
                'stat': 'Average'
            },
            ForecastType.ERROR_RATE: {
                'namespace': 'AWS/ApiGateway',
                'metric_name': '4XXError',
                'stat': 'Sum'
            },
            ForecastType.CAPACITY: {
                'namespace': 'AWS/Lambda',
                'metric_name': 'ConcurrentExecutions',
                'stat': 'Maximum'
            }
        }

        config = metric_mapping.get(metric_type, metric_mapping[ForecastType.AVAILABILITY])

        response = self.cloudwatch.get_metric_statistics(
            Namespace=config['namespace'],
            MetricName=config['metric_name'],
            Dimensions=[
                {'Name': 'ApiName', 'Value': f'lcopilot-api-enterprise-{self.environment}'}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,  # 5 minutes
            Statistics=[config['stat']]
        )

        data = []
        for point in response['Datapoints']:
            data.append({
                'timestamp': point['Timestamp'],
                'target_value': point[config['stat']],
                'metric_type': metric_type.value
            })

        return pd.DataFrame(data)

    def _collect_system_events(self, customer_id: str, start_time: datetime,
                              end_time: datetime) -> pd.DataFrame:
        # Collect deployment events, configuration changes, scaling events
        events = []

        # Simulated system events - in production, this would query actual event sources
        sample_events = [
            {'timestamp': start_time + timedelta(hours=6), 'event_type': 'deployment', 'impact_score': 0.3},
            {'timestamp': start_time + timedelta(hours=18), 'event_type': 'scaling', 'impact_score': 0.2},
            {'timestamp': start_time + timedelta(days=3), 'event_type': 'config_change', 'impact_score': 0.1},
        ]

        return pd.DataFrame(sample_events)

    def _collect_external_factors(self, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        # Collect external factors that might impact system reliability
        factors = []

        current = start_time
        while current < end_time:
            # Business hours factor
            is_business_hours = 9 <= current.hour <= 17 and current.weekday() < 5
            is_weekend = current.weekday() >= 5

            factors.append({
                'timestamp': current,
                'business_hours': 1 if is_business_hours else 0,
                'weekend': 1 if is_weekend else 0,
                'hour_of_day': current.hour,
                'day_of_week': current.weekday()
            })

            current += timedelta(minutes=5)

        return pd.DataFrame(factors)

    def _merge_data_sources(self, metrics: pd.DataFrame, events: pd.DataFrame,
                           factors: pd.DataFrame) -> pd.DataFrame:
        if metrics.empty:
            return pd.DataFrame()

        # Ensure timestamp columns are datetime
        for df in [metrics, events, factors]:
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Merge on timestamp (rounded to nearest 5 minutes)
        metrics['time_bucket'] = metrics['timestamp'].dt.floor('5min')
        factors['time_bucket'] = factors['timestamp'].dt.floor('5min')

        # Merge metrics with factors
        merged = pd.merge(metrics, factors, on='time_bucket', how='left', suffixes=('', '_factor'))

        # Add event indicators
        if not events.empty:
            events['time_bucket'] = events['timestamp'].dt.floor('5min')
            events_agg = events.groupby('time_bucket').agg({
                'impact_score': 'sum',
                'event_type': lambda x: ','.join(x)
            }).reset_index()

            merged = pd.merge(merged, events_agg, on='time_bucket', how='left')
            merged['impact_score'] = merged['impact_score'].fillna(0)
            merged['has_event'] = merged['impact_score'] > 0

        # Feature engineering
        merged['hour_sin'] = np.sin(2 * np.pi * merged['hour_of_day'] / 24)
        merged['hour_cos'] = np.cos(2 * np.pi * merged['hour_of_day'] / 24)
        merged['day_sin'] = np.sin(2 * np.pi * merged['day_of_week'] / 7)
        merged['day_cos'] = np.cos(2 * np.pi * merged['day_of_week'] / 7)

        # Lag features
        merged['target_lag_1'] = merged['target_value'].shift(1)
        merged['target_lag_2'] = merged['target_value'].shift(2)
        merged['target_ma_5'] = merged['target_value'].rolling(window=5).mean()

        # Remove rows with NaN values
        merged = merged.dropna()

        return merged

    def train_predictive_model(self, customer_id: str, metric_type: ForecastType,
                              training_data: pd.DataFrame) -> PredictiveModel:
        if not self.is_enterprise_customer(customer_id):
            raise ValueError("Predictive reliability is only available for Enterprise tier")

        if training_data.empty or len(training_data) < 50:
            raise ValueError("Insufficient training data for model training")

        model_id = f"{customer_id}_{metric_type.value}_{self.environment}"

        try:
            # Prepare features and target
            feature_cols = [
                'business_hours', 'weekend', 'hour_sin', 'hour_cos',
                'day_sin', 'day_cos', 'target_lag_1', 'target_lag_2',
                'target_ma_5', 'impact_score'
            ]

            X = training_data[feature_cols].fillna(0)
            y = training_data['target_value']

            # Split data
            split_idx = int(0.8 * len(X))
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )

            model.fit(X_train_scaled, y_train)

            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            accuracy = max(0, 1 - mae / y_test.mean()) if y_test.mean() > 0 else 0

            # Feature importance
            feature_importance = dict(zip(feature_cols, model.feature_importances_))

            # Save model and scaler
            model_path = f"models/{model_id}"
            self._save_model_to_s3(model, scaler, model_path)

            # Store in memory for immediate use
            self.models[model_id] = model
            self.scalers[model_id] = scaler

            predictive_model = PredictiveModel(
                model_id=model_id,
                model_type="RandomForestRegressor",
                target_metric=metric_type.value,
                accuracy_score=accuracy,
                last_trained=datetime.utcnow(),
                training_data_size=len(training_data),
                feature_importance=feature_importance,
                model_path=model_path
            )

            logger.info(f"Model trained successfully: {model_id} (Accuracy: {accuracy:.3f})")
            return predictive_model

        except Exception as e:
            logger.error(f"Failed to train predictive model: {str(e)}")
            raise

    def _save_model_to_s3(self, model: Any, scaler: Any, model_path: str):
        # Save model
        model_key = f"{model_path}/model.joblib"
        model_bytes = joblib.dumps(model)
        self.s3.put_object(
            Bucket=self.models_bucket,
            Key=model_key,
            Body=model_bytes
        )

        # Save scaler
        scaler_key = f"{model_path}/scaler.joblib"
        scaler_bytes = joblib.dumps(scaler)
        self.s3.put_object(
            Bucket=self.models_bucket,
            Key=scaler_key,
            Body=scaler_bytes
        )

    def _load_model_from_s3(self, model_path: str) -> Tuple[Any, Any]:
        # Load model
        model_key = f"{model_path}/model.joblib"
        model_obj = self.s3.get_object(Bucket=self.models_bucket, Key=model_key)
        model = joblib.loads(model_obj['Body'].read())

        # Load scaler
        scaler_key = f"{model_path}/scaler.joblib"
        scaler_obj = self.s3.get_object(Bucket=self.models_bucket, Key=scaler_key)
        scaler = joblib.loads(scaler_obj['Body'].read())

        return model, scaler

    def generate_reliability_forecast(self, customer_id: str, metric_type: ForecastType,
                                    forecast_hours: int = 24) -> ReliabilityForecast:
        if not self.is_enterprise_customer(customer_id):
            raise ValueError("Predictive reliability is only available for Enterprise tier")

        model_id = f"{customer_id}_{metric_type.value}_{self.environment}"

        # Check if model exists in memory or load from S3
        if model_id not in self.models:
            try:
                model_path = f"models/{model_id}"
                model, scaler = self._load_model_from_s3(model_path)
                self.models[model_id] = model
                self.scalers[model_id] = scaler
            except:
                # Train new model if not exists
                logger.info(f"Training new model for {model_id}")
                training_data = self.prepare_training_data(customer_id, metric_type)
                predictive_model = self.train_predictive_model(customer_id, metric_type, training_data)

        model = self.models[model_id]
        scaler = self.scalers[model_id]

        predictions = []
        current_time = datetime.utcnow()

        try:
            # Get recent data for initial conditions
            recent_data = self.prepare_training_data(customer_id, metric_type, days_back=1)

            if recent_data.empty:
                raise ValueError("No recent data available for forecasting")

            last_values = recent_data.tail(5)

            # Generate predictions for each hour
            for hour in range(forecast_hours):
                forecast_time = current_time + timedelta(hours=hour)

                # Prepare features for prediction
                features = self._prepare_forecast_features(forecast_time, last_values)

                if features is not None:
                    features_scaled = scaler.transform([features])
                    predicted_value = model.predict(features_scaled)[0]

                    # Calculate confidence intervals (simplified approach)
                    confidence_interval = predicted_value * 0.1  # ±10%

                    prediction = ForecastPoint(
                        timestamp=forecast_time,
                        metric_name=metric_type.value,
                        predicted_value=max(0, predicted_value),  # Ensure non-negative
                        confidence_interval_lower=max(0, predicted_value - confidence_interval),
                        confidence_interval_upper=predicted_value + confidence_interval,
                        confidence_level=0.8,
                        factors=self._identify_prediction_factors(features)
                    )

                    predictions.append(prediction)

            # Analyze risk factors
            risk_factors = self._identify_risk_factors(predictions, customer_id)

            forecast = ReliabilityForecast(
                forecast_id=f"forecast_{customer_id}_{metric_type.value}_{int(current_time.timestamp())}",
                customer_id=customer_id,
                forecast_type=metric_type,
                predictions=predictions,
                model_used=model_id,
                generated_at=current_time,
                forecast_horizon_hours=forecast_hours,
                accuracy_metrics={"estimated_accuracy": 0.85},  # Would be calculated from historical accuracy
                risk_factors=risk_factors
            )

            # Save forecast
            self._save_forecast(forecast)

            logger.info(f"Generated forecast with {len(predictions)} predictions for {customer_id}")
            return forecast

        except Exception as e:
            logger.error(f"Failed to generate forecast: {str(e)}")
            raise

    def _prepare_forecast_features(self, forecast_time: datetime,
                                  recent_data: pd.DataFrame) -> Optional[List[float]]:
        try:
            # Business hours and temporal features
            is_business_hours = 9 <= forecast_time.hour <= 17 and forecast_time.weekday() < 5
            is_weekend = forecast_time.weekday() >= 5

            # Cyclical features
            hour_sin = np.sin(2 * np.pi * forecast_time.hour / 24)
            hour_cos = np.cos(2 * np.pi * forecast_time.hour / 24)
            day_sin = np.sin(2 * np.pi * forecast_time.weekday() / 7)
            day_cos = np.cos(2 * np.pi * forecast_time.weekday() / 7)

            # Lag features from recent data
            if len(recent_data) >= 2:
                target_lag_1 = recent_data['target_value'].iloc[-1]
                target_lag_2 = recent_data['target_value'].iloc[-2]
                target_ma_5 = recent_data['target_value'].tail(5).mean()
            else:
                return None

            # Impact score (assume no planned events for forecast)
            impact_score = 0.0

            features = [
                1 if is_business_hours else 0,
                1 if is_weekend else 0,
                hour_sin,
                hour_cos,
                day_sin,
                day_cos,
                target_lag_1,
                target_lag_2,
                target_ma_5,
                impact_score
            ]

            return features

        except Exception as e:
            logger.error(f"Failed to prepare forecast features: {str(e)}")
            return None

    def _identify_prediction_factors(self, features: List[float]) -> List[str]:
        factors = []

        # Map features to human-readable factors
        feature_names = [
            'business_hours', 'weekend', 'hour_sin', 'hour_cos',
            'day_sin', 'day_cos', 'target_lag_1', 'target_lag_2',
            'target_ma_5', 'impact_score'
        ]

        if features[0] == 1:  # business_hours
            factors.append("business_hours")
        if features[1] == 1:  # weekend
            factors.append("weekend")
        if features[9] > 0:  # impact_score
            factors.append("system_events")

        return factors

    def _identify_risk_factors(self, predictions: List[ForecastPoint], customer_id: str) -> List[str]:
        risk_factors = []

        if not predictions:
            return risk_factors

        # Analyze prediction trends
        values = [p.predicted_value for p in predictions]

        # Check for increasing trend
        if len(values) > 5:
            slope = np.polyfit(range(len(values)), values, 1)[0]
            if slope > 0.1:
                risk_factors.append("increasing_trend_detected")

        # Check for high variability
        if np.std(values) > np.mean(values) * 0.3:
            risk_factors.append("high_variability")

        # Check for values outside normal range
        mean_val = np.mean(values)
        if any(v > mean_val * 2 for v in values):
            risk_factors.append("potential_outliers")

        return risk_factors

    def detect_anomalies(self, customer_id: str, hours_back: int = 24) -> List[Anomaly]:
        if not self.is_enterprise_customer(customer_id):
            raise ValueError("Anomaly detection is only available for Enterprise tier")

        anomalies = []

        try:
            # Prepare data for anomaly detection
            training_data = self.prepare_training_data(customer_id, ForecastType.AVAILABILITY, days_back=7)

            if training_data.empty or len(training_data) < 100:
                logger.warning("Insufficient data for anomaly detection")
                return anomalies

            # Train anomaly detection model
            detector_id = f"anomaly_{customer_id}_{self.environment}"

            if detector_id not in self.anomaly_detectors:
                detector = IsolationForest(
                    contamination=0.1,
                    random_state=42,
                    n_jobs=-1
                )

                feature_cols = ['target_value', 'business_hours', 'weekend', 'impact_score']
                X = training_data[feature_cols].fillna(0)
                detector.fit(X)

                self.anomaly_detectors[detector_id] = detector

            detector = self.anomaly_detectors[detector_id]

            # Get recent data for anomaly detection
            recent_data = self.prepare_training_data(customer_id, ForecastType.AVAILABILITY, days_back=1)

            if not recent_data.empty:
                feature_cols = ['target_value', 'business_hours', 'weekend', 'impact_score']
                X_recent = recent_data[feature_cols].fillna(0)

                # Detect anomalies
                anomaly_scores = detector.decision_function(X_recent)
                anomaly_labels = detector.predict(X_recent)

                for idx, (score, label) in enumerate(zip(anomaly_scores, anomaly_labels)):
                    if label == -1:  # Anomaly detected
                        row = recent_data.iloc[idx]
                        confidence = abs(score)

                        # Determine anomaly type and severity
                        anomaly_type = self._classify_anomaly_type(row)
                        severity = "HIGH" if confidence > 0.5 else "MEDIUM"

                        anomaly = Anomaly(
                            timestamp=row['timestamp'],
                            anomaly_type=anomaly_type,
                            severity=severity,
                            confidence=confidence,
                            description=f"Unusual pattern detected in {anomaly_type.value}",
                            affected_services=[f"lcopilot-api-enterprise-{self.environment}"],
                            predicted_impact={
                                "availability_impact": "5-15%",
                                "user_impact": "moderate",
                                "duration_estimate": "1-2 hours"
                            },
                            recommended_actions=[
                                "Investigate recent changes",
                                "Check resource utilization",
                                "Review error logs",
                                "Monitor system metrics closely"
                            ]
                        )

                        anomalies.append(anomaly)

        except Exception as e:
            logger.error(f"Failed to detect anomalies: {str(e)}")

        return anomalies

    def _classify_anomaly_type(self, data_row: pd.Series) -> AnomalyType:
        # Simple classification based on available data
        if data_row.get('impact_score', 0) > 0:
            return AnomalyType.RELIABILITY
        elif data_row.get('target_value', 0) > data_row.get('target_ma_5', 0) * 2:
            return AnomalyType.PERFORMANCE
        else:
            return AnomalyType.CAPACITY

    def generate_capacity_recommendations(self, customer_id: str) -> List[CapacityRecommendation]:
        if not self.is_enterprise_customer(customer_id):
            raise ValueError("Capacity recommendations are only available for Enterprise tier")

        recommendations = []

        try:
            # Generate forecast for capacity planning
            capacity_forecast = self.generate_reliability_forecast(
                customer_id, ForecastType.CAPACITY, forecast_hours=168  # 1 week
            )

            # Analyze current vs predicted utilization
            current_utilization = 0.75  # Would be calculated from actual metrics
            predicted_max = max(p.predicted_value for p in capacity_forecast.predictions)
            predicted_utilization = predicted_max / 100  # Normalize

            # Generate recommendations based on predictions
            if predicted_utilization > 0.8:
                recommendations.append(CapacityRecommendation(
                    resource_type="Lambda Concurrent Executions",
                    current_utilization=current_utilization,
                    predicted_utilization=predicted_utilization,
                    recommended_action="Scale up reserved concurrency",
                    confidence=0.85,
                    cost_impact=150.0,
                    timeline="Next 48 hours",
                    justification="Predicted peak utilization exceeds 80% threshold"
                ))

            if predicted_utilization > 0.9:
                recommendations.append(CapacityRecommendation(
                    resource_type="API Gateway Throttling",
                    current_utilization=current_utilization,
                    predicted_utilization=predicted_utilization,
                    recommended_action="Increase throttling limits",
                    confidence=0.9,
                    cost_impact=75.0,
                    timeline="Immediate",
                    justification="Critical utilization threshold predicted"
                ))

        except Exception as e:
            logger.error(f"Failed to generate capacity recommendations: {str(e)}")

        return recommendations

    def _save_forecast(self, forecast: ReliabilityForecast):
        try:
            forecast_key = f"forecasts/{forecast.customer_id}/{forecast.forecast_id}.json"
            forecast_data = asdict(forecast)

            # Convert datetime objects to strings
            forecast_json = json.dumps(forecast_data, default=str, indent=2)

            self.s3.put_object(
                Bucket=self.predictions_bucket,
                Key=forecast_key,
                Body=forecast_json,
                ContentType='application/json'
            )

            logger.info(f"Forecast saved: {forecast_key}")

        except Exception as e:
            logger.error(f"Failed to save forecast: {str(e)}")

def main():
    """Demo predictive reliability functionality"""
    manager = PredictiveReliabilityManager()

    customer_id = "customer-enterprise-001"

    if not manager.is_enterprise_customer(customer_id):
        print("Predictive reliability is only available for Enterprise tier customers")
        return

    print("=== LCopilot Predictive Reliability Demo ===")

    # Generate availability forecast
    print("\n1. Generating availability forecast...")
    try:
        forecast = manager.generate_reliability_forecast(
            customer_id, ForecastType.AVAILABILITY, forecast_hours=24
        )

        print(f"Generated forecast with {len(forecast.predictions)} predictions")
        print(f"Risk factors: {forecast.risk_factors}")

        # Show first few predictions
        for i, pred in enumerate(forecast.predictions[:5]):
            print(f"  {pred.timestamp.strftime('%H:%M')}: {pred.predicted_value:.2f} "
                  f"(CI: {pred.confidence_interval_lower:.2f}-{pred.confidence_interval_upper:.2f})")

    except Exception as e:
        print(f"Forecast generation failed: {str(e)}")

    # Detect anomalies
    print("\n2. Detecting anomalies...")
    try:
        anomalies = manager.detect_anomalies(customer_id, hours_back=24)
        print(f"Detected {len(anomalies)} anomalies")

        for anomaly in anomalies:
            print(f"  {anomaly.timestamp.strftime('%H:%M')}: {anomaly.description} "
                  f"(Severity: {anomaly.severity}, Confidence: {anomaly.confidence:.2f})")

    except Exception as e:
        print(f"Anomaly detection failed: {str(e)}")

    # Generate capacity recommendations
    print("\n3. Generating capacity recommendations...")
    try:
        recommendations = manager.generate_capacity_recommendations(customer_id)
        print(f"Generated {len(recommendations)} recommendations")

        for rec in recommendations:
            print(f"  {rec.resource_type}: {rec.recommended_action} "
                  f"(Cost impact: ${rec.cost_impact}, Timeline: {rec.timeline})")

    except Exception as e:
        print(f"Capacity recommendations failed: {str(e)}")

if __name__ == "__main__":
    main()