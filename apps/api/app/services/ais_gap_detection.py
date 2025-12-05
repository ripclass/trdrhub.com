"""
AIS Gap Detection Service

Analyzes vessel AIS transmission history to detect suspicious gaps.
Gaps in AIS transmission can indicate:
- Dark shipping (intentional AIS switch-off)
- Sanctions evasion
- Ship-to-ship transfers
- Smuggling activities

This is a critical compliance feature for banks.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============== Models ==============

class AISPosition(BaseModel):
    """A single AIS position report."""
    timestamp: str
    latitude: float
    longitude: float
    speed: Optional[float] = None
    course: Optional[float] = None
    heading: Optional[float] = None
    nav_status: Optional[str] = None  # underway, anchored, moored, etc.
    source: str = "AIS"


class AISGap(BaseModel):
    """Detected gap in AIS transmission."""
    gap_id: str
    start_time: str
    end_time: str
    duration_hours: float
    last_known_position: Dict[str, float]  # lat, lon
    first_position_after: Dict[str, float]
    distance_nm: Optional[float] = None  # Nautical miles traveled during gap
    avg_speed_during_gap: Optional[float] = None  # Estimated speed
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_factors: List[str]
    possible_explanations: List[str]


class AISAnalysisResult(BaseModel):
    """Complete AIS analysis result."""
    vessel_name: str
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    analysis_period_days: int
    analyzed_at: str
    
    # Position data
    total_positions: int
    first_position: Optional[str] = None
    last_position: Optional[str] = None
    
    # Gap analysis
    total_gaps: int
    suspicious_gaps: int  # Gaps > 24 hours
    longest_gap_hours: float
    gaps: List[AISGap]
    
    # Risk assessment
    overall_risk_score: int  # 0-100
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_factors: List[str]
    recommendation: str
    
    # Geographic analysis
    high_risk_areas_visited: List[str]
    port_calls: int


# ============== Constants ==============

# Gap thresholds (in hours)
GAP_THRESHOLD_NORMAL = 6  # Gaps under 6h are normal
GAP_THRESHOLD_SUSPICIOUS = 24  # Gaps over 24h are suspicious
GAP_THRESHOLD_CRITICAL = 72  # Gaps over 72h are critical

# High-risk waters/areas
HIGH_RISK_AREAS = {
    "north_korea_waters": {
        "lat_range": (38.0, 43.0),
        "lon_range": (124.0, 132.0),
        "name": "North Korean Waters"
    },
    "iran_waters": {
        "lat_range": (24.0, 30.0),
        "lon_range": (48.0, 60.0),
        "name": "Iranian Waters"
    },
    "syria_coast": {
        "lat_range": (34.5, 36.5),
        "lon_range": (35.0, 37.0),
        "name": "Syrian Coast"
    },
    "somalia_coast": {
        "lat_range": (-2.0, 12.0),
        "lon_range": (42.0, 52.0),
        "name": "Somali Coast"
    },
    "venezuela_coast": {
        "lat_range": (8.0, 14.0),
        "lon_range": (-74.0, -60.0),
        "name": "Venezuelan Coast"
    },
    "dark_fleet_zones": {
        "lat_range": (35.0, 45.0),
        "lon_range": (-10.0, 30.0),
        "name": "Mediterranean Dark Fleet Zone"
    }
}


# ============== Service ==============

class AISGapDetectionService:
    """
    Service for analyzing vessel AIS history and detecting suspicious gaps.
    """
    
    def __init__(self):
        pass
    
    def _calculate_distance_nm(
        self, 
        lat1: float, lon1: float, 
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in nautical miles."""
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of Earth in nautical miles
        r = 3440.065
        return round(c * r, 1)
    
    def _is_in_high_risk_area(self, lat: float, lon: float) -> List[str]:
        """Check if position is in any high-risk area."""
        areas = []
        for area_id, area in HIGH_RISK_AREAS.items():
            lat_min, lat_max = area["lat_range"]
            lon_min, lon_max = area["lon_range"]
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                areas.append(area["name"])
        return areas
    
    def _assess_gap_risk(
        self, 
        duration_hours: float,
        last_pos: Dict[str, float],
        first_pos_after: Dict[str, float],
        distance_nm: float
    ) -> tuple[str, List[str], List[str]]:
        """
        Assess risk level of a specific gap.
        Returns: (risk_level, risk_factors, possible_explanations)
        """
        risk_factors = []
        explanations = []
        
        # Duration-based risk
        if duration_hours >= GAP_THRESHOLD_CRITICAL:
            risk_factors.append(f"Very long gap ({duration_hours:.1f} hours)")
            explanations.append("Extended maintenance or drydock")
            explanations.append("Intentional AIS shutdown")
        elif duration_hours >= GAP_THRESHOLD_SUSPICIOUS:
            risk_factors.append(f"Suspicious gap duration ({duration_hours:.1f} hours)")
            explanations.append("Poor satellite coverage")
            explanations.append("Equipment malfunction")
        
        # Distance analysis
        if duration_hours > 0:
            avg_speed = distance_nm / duration_hours
            if avg_speed > 25:  # Unusually high speed for gap duration
                risk_factors.append(f"High implied speed ({avg_speed:.1f} knots)")
                explanations.append("AIS turned off during transit")
            elif avg_speed < 2 and distance_nm > 50:
                risk_factors.append("Inconsistent movement pattern")
                explanations.append("Possible ship-to-ship transfer")
        
        # Location-based risk
        areas_before = self._is_in_high_risk_area(last_pos.get("lat", 0), last_pos.get("lon", 0))
        areas_after = self._is_in_high_risk_area(first_pos_after.get("lat", 0), first_pos_after.get("lon", 0))
        
        if areas_before:
            risk_factors.append(f"Gap started in: {', '.join(areas_before)}")
        if areas_after:
            risk_factors.append(f"Gap ended in: {', '.join(areas_after)}")
        
        # Determine overall risk level
        if len(risk_factors) >= 3 or duration_hours >= GAP_THRESHOLD_CRITICAL:
            risk_level = "CRITICAL"
        elif len(risk_factors) >= 2 or duration_hours >= GAP_THRESHOLD_SUSPICIOUS:
            risk_level = "HIGH"
        elif len(risk_factors) >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        if not explanations:
            explanations.append("Normal operational gap")
            explanations.append("Coastal coverage limitations")
        
        return risk_level, risk_factors, explanations
    
    def analyze_positions(
        self,
        positions: List[AISPosition],
        vessel_name: str,
        imo: Optional[str] = None,
        mmsi: Optional[str] = None
    ) -> AISAnalysisResult:
        """
        Analyze a list of AIS positions for gaps.
        
        Positions should be sorted by timestamp.
        """
        if not positions:
            return self._empty_result(vessel_name, imo, mmsi)
        
        # Sort by timestamp
        sorted_positions = sorted(
            positions, 
            key=lambda p: datetime.fromisoformat(p.timestamp.replace("Z", "+00:00"))
        )
        
        gaps: List[AISGap] = []
        high_risk_areas_visited = set()
        
        # Analyze gaps
        for i in range(1, len(sorted_positions)):
            prev = sorted_positions[i - 1]
            curr = sorted_positions[i]
            
            prev_time = datetime.fromisoformat(prev.timestamp.replace("Z", "+00:00"))
            curr_time = datetime.fromisoformat(curr.timestamp.replace("Z", "+00:00"))
            
            duration = curr_time - prev_time
            duration_hours = duration.total_seconds() / 3600
            
            # Check for high-risk areas
            areas = self._is_in_high_risk_area(curr.latitude, curr.longitude)
            high_risk_areas_visited.update(areas)
            
            # Only record gaps > threshold
            if duration_hours >= GAP_THRESHOLD_NORMAL:
                distance_nm = self._calculate_distance_nm(
                    prev.latitude, prev.longitude,
                    curr.latitude, curr.longitude
                )
                
                avg_speed = distance_nm / duration_hours if duration_hours > 0 else 0
                
                last_pos = {"lat": prev.latitude, "lon": prev.longitude}
                first_pos = {"lat": curr.latitude, "lon": curr.longitude}
                
                risk_level, risk_factors, explanations = self._assess_gap_risk(
                    duration_hours, last_pos, first_pos, distance_nm
                )
                
                gaps.append(AISGap(
                    gap_id=f"gap_{i}",
                    start_time=prev.timestamp,
                    end_time=curr.timestamp,
                    duration_hours=round(duration_hours, 1),
                    last_known_position=last_pos,
                    first_position_after=first_pos,
                    distance_nm=distance_nm,
                    avg_speed_during_gap=round(avg_speed, 1),
                    risk_level=risk_level,
                    risk_factors=risk_factors,
                    possible_explanations=explanations
                ))
        
        # Calculate overall risk
        suspicious_gaps = [g for g in gaps if g.duration_hours >= GAP_THRESHOLD_SUSPICIOUS]
        critical_gaps = [g for g in gaps if g.risk_level in ["CRITICAL", "HIGH"]]
        
        # Risk score calculation
        risk_score = 0
        risk_score += len(suspicious_gaps) * 20
        risk_score += len(critical_gaps) * 30
        risk_score += len(high_risk_areas_visited) * 15
        risk_score = min(risk_score, 100)
        
        # Overall risk level
        if risk_score >= 70 or len(critical_gaps) >= 2:
            overall_risk = "CRITICAL"
            recommendation = "DO NOT PROCEED - Multiple critical AIS gaps detected. Manual review required."
        elif risk_score >= 50 or len(critical_gaps) >= 1:
            overall_risk = "HIGH"
            recommendation = "CAUTION - Significant AIS gaps detected. Enhanced due diligence recommended."
        elif risk_score >= 30 or len(suspicious_gaps) >= 2:
            overall_risk = "MEDIUM"
            recommendation = "PROCEED WITH CAUTION - Some AIS gaps detected. Monitor vessel closely."
        else:
            overall_risk = "LOW"
            recommendation = "CLEAR - Normal AIS transmission pattern."
        
        # Build risk factors list
        all_risk_factors = []
        if len(suspicious_gaps) > 0:
            all_risk_factors.append(f"{len(suspicious_gaps)} suspicious gap(s) detected")
        if len(high_risk_areas_visited) > 0:
            all_risk_factors.append(f"Vessel visited: {', '.join(high_risk_areas_visited)}")
        if gaps:
            max_gap = max(g.duration_hours for g in gaps)
            if max_gap > 48:
                all_risk_factors.append(f"Longest gap: {max_gap:.1f} hours")
        
        longest_gap = max((g.duration_hours for g in gaps), default=0)
        
        return AISAnalysisResult(
            vessel_name=vessel_name,
            imo=imo,
            mmsi=mmsi,
            analysis_period_days=30,  # Default
            analyzed_at=datetime.utcnow().isoformat() + "Z",
            total_positions=len(sorted_positions),
            first_position=sorted_positions[0].timestamp if sorted_positions else None,
            last_position=sorted_positions[-1].timestamp if sorted_positions else None,
            total_gaps=len(gaps),
            suspicious_gaps=len(suspicious_gaps),
            longest_gap_hours=round(longest_gap, 1),
            gaps=gaps,
            overall_risk_score=risk_score,
            risk_level=overall_risk,
            risk_factors=all_risk_factors,
            recommendation=recommendation,
            high_risk_areas_visited=list(high_risk_areas_visited),
            port_calls=0  # Would need port data
        )
    
    def _empty_result(
        self, 
        vessel_name: str, 
        imo: Optional[str], 
        mmsi: Optional[str]
    ) -> AISAnalysisResult:
        """Return empty result when no positions available."""
        return AISAnalysisResult(
            vessel_name=vessel_name,
            imo=imo,
            mmsi=mmsi,
            analysis_period_days=0,
            analyzed_at=datetime.utcnow().isoformat() + "Z",
            total_positions=0,
            total_gaps=0,
            suspicious_gaps=0,
            longest_gap_hours=0,
            gaps=[],
            overall_risk_score=0,
            risk_level="UNKNOWN",
            risk_factors=["No AIS data available for analysis"],
            recommendation="Unable to analyze - no AIS position data available.",
            high_risk_areas_visited=[],
            port_calls=0
        )
    
    def generate_demo_analysis(
        self,
        vessel_name: str,
        imo: Optional[str] = None,
        mmsi: Optional[str] = None,
        risk_profile: str = "low"  # low, medium, high
    ) -> AISAnalysisResult:
        """
        Generate demo analysis for testing.
        """
        now = datetime.utcnow()
        
        if risk_profile == "high":
            # Simulate vessel with suspicious gaps
            gaps = [
                AISGap(
                    gap_id="gap_1",
                    start_time=(now - timedelta(days=15)).isoformat() + "Z",
                    end_time=(now - timedelta(days=14, hours=12)).isoformat() + "Z",
                    duration_hours=36.0,
                    last_known_position={"lat": 25.5, "lon": 55.2},
                    first_position_after={"lat": 26.8, "lon": 57.1},
                    distance_nm=145.2,
                    avg_speed_during_gap=4.0,
                    risk_level="HIGH",
                    risk_factors=[
                        "Suspicious gap duration (36.0 hours)",
                        "Gap ended in: Iranian Waters"
                    ],
                    possible_explanations=[
                        "Poor satellite coverage",
                        "Possible ship-to-ship transfer"
                    ]
                ),
                AISGap(
                    gap_id="gap_2",
                    start_time=(now - timedelta(days=5)).isoformat() + "Z",
                    end_time=(now - timedelta(days=4)).isoformat() + "Z",
                    duration_hours=24.5,
                    last_known_position={"lat": 28.1, "lon": 51.3},
                    first_position_after={"lat": 27.5, "lon": 49.8},
                    distance_nm=98.7,
                    avg_speed_during_gap=4.0,
                    risk_level="MEDIUM",
                    risk_factors=["Suspicious gap duration (24.5 hours)"],
                    possible_explanations=[
                        "Equipment malfunction",
                        "AIS turned off during transit"
                    ]
                )
            ]
            risk_score = 65
            risk_level = "HIGH"
            recommendation = "CAUTION - Multiple AIS gaps detected near high-risk areas. Enhanced due diligence recommended."
            risk_factors = [
                "2 suspicious gap(s) detected",
                "Vessel visited: Iranian Waters",
                "Longest gap: 36.0 hours"
            ]
            high_risk_areas = ["Iranian Waters"]
        elif risk_profile == "medium":
            gaps = [
                AISGap(
                    gap_id="gap_1",
                    start_time=(now - timedelta(days=10)).isoformat() + "Z",
                    end_time=(now - timedelta(days=9, hours=6)).isoformat() + "Z",
                    duration_hours=18.0,
                    last_known_position={"lat": 31.2, "lon": 121.5},
                    first_position_after={"lat": 30.8, "lon": 122.1},
                    distance_nm=52.3,
                    avg_speed_during_gap=2.9,
                    risk_level="MEDIUM",
                    risk_factors=["Inconsistent movement pattern"],
                    possible_explanations=[
                        "Coastal coverage limitations",
                        "Normal operational gap"
                    ]
                )
            ]
            risk_score = 35
            risk_level = "MEDIUM"
            recommendation = "PROCEED WITH CAUTION - Some AIS gaps detected. Monitor vessel closely."
            risk_factors = ["1 gap detected (18.0 hours)"]
            high_risk_areas = []
        else:
            # Low risk - clean vessel
            gaps = []
            risk_score = 5
            risk_level = "LOW"
            recommendation = "CLEAR - Normal AIS transmission pattern."
            risk_factors = []
            high_risk_areas = []
        
        return AISAnalysisResult(
            vessel_name=vessel_name,
            imo=imo,
            mmsi=mmsi,
            analysis_period_days=30,
            analyzed_at=now.isoformat() + "Z",
            total_positions=847,
            first_position=(now - timedelta(days=30)).isoformat() + "Z",
            last_position=(now - timedelta(hours=2)).isoformat() + "Z",
            total_gaps=len(gaps),
            suspicious_gaps=len([g for g in gaps if g.duration_hours >= 24]),
            longest_gap_hours=max((g.duration_hours for g in gaps), default=0),
            gaps=gaps,
            overall_risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendation=recommendation,
            high_risk_areas_visited=high_risk_areas,
            port_calls=5
        )


# Singleton instance
_ais_service: Optional[AISGapDetectionService] = None


def get_ais_service() -> AISGapDetectionService:
    """Get or create AIS gap detection service instance."""
    global _ais_service
    if _ais_service is None:
        _ais_service = AISGapDetectionService()
    return _ais_service

