import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from enum import Enum
import statistics

logger = logging.getLogger(__name__)

class FalsePositiveType(Enum):
    VERSION_MISMATCH = "version_mismatch"
    PRODUCT_MISMATCH = "product_mismatch"
    BANNER_INCONSISTENCY = "banner_inconsistency"
    LOW_CONFIDENCE = "low_confidence"
    MANUAL_REVIEW = "manual_review"
    CREDENTIAL_FALSE_POSITIVE = "credential_false_positive"

@dataclass
class FalsePositiveReport:
    id: str
    service_id: str
    vulnerability_id: Optional[str]
    credential_id: Optional[str]
    fp_type: FalsePositiveType
    confidence_score: float
    detection_method: str
    banner_snippet: str
    reason: str
    reported_by: str
    reported_at: datetime
    validated: bool = False

@dataclass
class FalsePositiveMetrics:
    total_detections: int
    false_positives: int
    false_positive_rate: float
    by_type: Dict[str, int]
    by_confidence_range: Dict[str, int]
    by_service_type: Dict[str, int]
    trend_7_days: float
    trend_30_days: float

class FalsePositiveTracker:
    """Service for tracking and analyzing false positive patterns."""

    def __init__(self):
        self.false_positive_reports = []
        self.validation_feedback = {}
        self.confidence_adjustments = {}
        self.pattern_blacklist = set()

    def report_false_positive(self,
                            service_id: str,
                            fp_type: FalsePositiveType,
                            confidence_score: float,
                            detection_method: str,
                            banner_snippet: str,
                            reason: str,
                            reported_by: str,
                            vulnerability_id: Optional[str] = None,
                            credential_id: Optional[str] = None) -> str:
        """
        Report a false positive detection.

        Args:
            service_id: ID of the service
            fp_type: Type of false positive
            confidence_score: Original confidence score
            detection_method: How the detection was made
            banner_snippet: Relevant banner information
            reason: Reason why it's a false positive
            reported_by: Who reported it (user ID or 'system')
            vulnerability_id: ID of vulnerability if applicable
            credential_id: ID of credential if applicable

        Returns:
            Report ID
        """
        report_id = f"fp_{len(self.false_positive_reports) + 1}_{int(datetime.now(UTC).timestamp())}"

        report = FalsePositiveReport(
            id=report_id,
            service_id=service_id,
            vulnerability_id=vulnerability_id,
            credential_id=credential_id,
            fp_type=fp_type,
            confidence_score=confidence_score,
            detection_method=detection_method,
            banner_snippet=banner_snippet,
            reason=reason,
            reported_by=reported_by,
            reported_at=datetime.now(UTC)
        )

        self.false_positive_reports.append(report)

        # Auto-learn from patterns
        self._learn_from_false_positive(report)

        logger.info(f"False positive reported: {report_id} - {fp_type.value}")
        return report_id

    def validate_false_positive(self, report_id: str, is_valid: bool, validator: str) -> bool:
        """
        Validate a false positive report.

        Args:
            report_id: ID of the report to validate
            is_valid: Whether the report is valid
            validator: Who validated it

        Returns:
            True if validation was successful
        """
        for report in self.false_positive_reports:
            if report.id == report_id:
                report.validated = True
                self.validation_feedback[report_id] = {
                    'is_valid': is_valid,
                    'validator': validator,
                    'validated_at': datetime.now(UTC)
                }

                if is_valid:
                    # Strengthen the pattern learning
                    self._reinforce_pattern_learning(report)
                else:
                    # This was actually a true positive, adjust accordingly
                    self._adjust_for_false_negative(report)

                return True

        return False

    def get_false_positive_metrics(self, days: int = 30) -> FalsePositiveMetrics:
        """
        Get false positive metrics for the specified time period.

        Args:
            days: Number of days to look back

        Returns:
            FalsePositiveMetrics object
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        recent_reports = [r for r in self.false_positive_reports if r.reported_at >= cutoff_date]

        # Calculate metrics
        total_fps = len(recent_reports)

        # Group by type
        by_type = {}
        for report in recent_reports:
            fp_type = report.fp_type.value
            by_type[fp_type] = by_type.get(fp_type, 0) + 1

        # Group by confidence range
        by_confidence = {
            '0.0-0.3': 0,
            '0.3-0.5': 0,
            '0.5-0.7': 0,
            '0.7-0.9': 0,
            '0.9-1.0': 0
        }

        for report in recent_reports:
            score = report.confidence_score
            if score < 0.3:
                by_confidence['0.0-0.3'] += 1
            elif score < 0.5:
                by_confidence['0.3-0.5'] += 1
            elif score < 0.7:
                by_confidence['0.5-0.7'] += 1
            elif score < 0.9:
                by_confidence['0.7-0.9'] += 1
            else:
                by_confidence['0.9-1.0'] += 1

        # Calculate trends
        trend_7_days = self._calculate_trend(7)
        trend_30_days = self._calculate_trend(30)

        # Estimate total detections (this would normally come from actual detection logs)
        estimated_total_detections = total_fps * 10  # Rough estimate

        fp_rate = (total_fps / estimated_total_detections * 100) if estimated_total_detections > 0 else 0

        return FalsePositiveMetrics(
            total_detections=estimated_total_detections,
            false_positives=total_fps,
            false_positive_rate=fp_rate,
            by_type=by_type,
            by_confidence_range=by_confidence,
            by_service_type={},  # Would need service type data
            trend_7_days=trend_7_days,
            trend_30_days=trend_30_days
        )

    def get_pattern_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get recommendations for reducing false positives based on observed patterns.

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []

        # Analyze patterns
        if len(self.false_positive_reports) < 5:
            return [{'type': 'info', 'message': 'Insufficient data for pattern analysis'}]

        # Check for high confidence false positives
        high_confidence_fps = [r for r in self.false_positive_reports if r.confidence_score > 0.8]
        if len(high_confidence_fps) > len(self.false_positive_reports) * 0.2:
            recommendations.append({
                'type': 'critical',
                'category': 'confidence_thresholds',
                'message': 'High number of false positives with high confidence scores',
                'suggestion': 'Review confidence calculation algorithms',
                'priority': 'high'
            })

        # Check for version mismatch patterns
        version_mismatches = [r for r in self.false_positive_reports if r.fp_type == FalsePositiveType.VERSION_MISMATCH]
        if len(version_mismatches) > 5:
            recommendations.append({
                'type': 'warning',
                'category': 'version_extraction',
                'message': f'{len(version_mismatches)} version mismatch false positives detected',
                'suggestion': 'Improve version extraction regex patterns',
                'priority': 'medium'
            })

        # Check for banner inconsistency patterns
        banner_issues = [r for r in self.false_positive_reports if r.fp_type == FalsePositiveType.BANNER_INCONSISTENCY]
        if len(banner_issues) > 3:
            recommendations.append({
                'type': 'warning',
                'category': 'banner_parsing',
                'message': f'{len(banner_issues)} banner inconsistency false positives detected',
                'suggestion': 'Review banner parsing logic and add validation',
                'priority': 'medium'
            })

        # Check for credential false positives
        cred_fps = [r for r in self.false_positive_reports if r.fp_type == FalsePositiveType.CREDENTIAL_FALSE_POSITIVE]
        if len(cred_fps) > 2:
            recommendations.append({
                'type': 'info',
                'category': 'credentials',
                'message': f'{len(cred_fps)} credential false positives detected',
                'suggestion': 'Review default credential detection patterns',
                'priority': 'low'
            })

        # Check for manual review patterns
        manual_reviews = [r for r in self.false_positive_reports if r.fp_type == FalsePositiveType.MANUAL_REVIEW]
        if len(manual_reviews) > 10:
            recommendations.append({
                'type': 'info',
                'category': 'automation',
                'message': 'High number of manual review false positives',
                'suggestion': 'Consider automating common false positive patterns',
                'priority': 'low'
            })

        return recommendations

    def get_confidence_adjustment_suggestions(self) -> Dict[str, float]:
        """
        Get suggestions for confidence threshold adjustments.

        Returns:
            Dictionary of threshold adjustments by category
        """
        if len(self.false_positive_reports) < 10:
            return {}

        adjustments = {}

        # Analyze confidence distribution of false positives
        confidence_scores = [r.confidence_score for r in self.false_positive_reports]

        # If many false positives have high confidence, suggest increasing thresholds
        high_conf_fps = [score for score in confidence_scores if score > 0.8]
        if len(high_conf_fps) > len(confidence_scores) * 0.3:
            adjustments['high_confidence_threshold'] = 0.9  # Increase to 0.9

        medium_conf_fps = [score for score in confidence_scores if 0.5 < score <= 0.8]
        if len(medium_conf_fps) > len(confidence_scores) * 0.4:
            adjustments['medium_confidence_threshold'] = 0.7  # Increase to 0.7

        # Suggest minimum confidence threshold
        if statistics.mean(confidence_scores) > 0.6:
            adjustments['minimum_threshold'] = 0.5

        return adjustments

    def create_pattern_blacklist(self) -> List[str]:
        """
        Create a blacklist of patterns that frequently cause false positives.

        Returns:
            List of pattern strings to blacklist
        """
        pattern_counts = {}

        for report in self.false_positive_reports:
            # Extract patterns from banner snippets
            banner = report.banner_snippet.lower()

            # Common false positive patterns
            patterns = [
                'test',
                'demo',
                'example',
                'localhost',
                'internal',
                'dev',
                'staging'
            ]

            for pattern in patterns:
                if pattern in banner:
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        # Return patterns that appear frequently
        blacklist = [pattern for pattern, count in pattern_counts.items() if count >= 3]
        self.pattern_blacklist.update(blacklist)

        return blacklist

    def _learn_from_false_positive(self, report: FalsePositiveReport):
        """Learn patterns from a false positive report."""
        # Track detection method issues
        method = report.detection_method
        if method not in self.confidence_adjustments:
            self.confidence_adjustments[method] = {'count': 0, 'total_confidence': 0}

        self.confidence_adjustments[method]['count'] += 1
        self.confidence_adjustments[method]['total_confidence'] += report.confidence_score

        # Add to pattern blacklist if appropriate
        if report.fp_type in [FalsePositiveType.BANNER_INCONSISTENCY, FalsePositiveType.PRODUCT_MISMATCH]:
            banner_words = report.banner_snippet.lower().split()
            for word in banner_words:
                if len(word) > 3 and word not in self.pattern_blacklist:
                    # Add words that appear suspicious
                    if any(suspect in word for suspect in ['test', 'demo', 'dev', 'local']):
                        self.pattern_blacklist.add(word)

    def _reinforce_pattern_learning(self, report: FalsePositiveReport):
        """Reinforce learning when a false positive is validated."""
        # Strengthen the confidence adjustment for this detection method
        method = report.detection_method
        if method in self.confidence_adjustments:
            # Reduce confidence for this method
            self.confidence_adjustments[method]['confidence_penalty'] = \
                self.confidence_adjustments[method].get('confidence_penalty', 0) + 0.1

    def _adjust_for_false_negative(self, report: FalsePositiveReport):
        """Adjust when a reported false positive was actually valid."""
        # This was incorrectly reported as false positive
        method = report.detection_method
        if method in self.confidence_adjustments:
            # Increase confidence for this method
            penalty = self.confidence_adjustments[method].get('confidence_penalty', 0)
            self.confidence_adjustments[method]['confidence_penalty'] = max(0, penalty - 0.05)

    def _calculate_trend(self, days: int) -> float:
        """Calculate false positive trend over specified days."""
        if len(self.false_positive_reports) < 2:
            return 0.0

        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        recent_reports = [r for r in self.false_positive_reports if r.reported_at >= cutoff_date]

        if len(recent_reports) < 2:
            return 0.0

        # Calculate daily average
        daily_counts = {}
        for report in recent_reports:
            day = report.reported_at.date()
            daily_counts[day] = daily_counts.get(day, 0) + 1

        if len(daily_counts) < 2:
            return 0.0

        # Simple trend calculation (slope)
        days_list = sorted(daily_counts.keys())
        counts = [daily_counts[day] for day in days_list]

        if len(counts) < 2:
            return 0.0

        # Linear trend approximation
        n = len(counts)
        sum_x = sum(range(n))
        sum_y = sum(counts)
        sum_xy = sum(i * counts[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0

        return slope

    def export_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Export comprehensive false positive report.

        Args:
            days: Number of days to include in report

        Returns:
            Comprehensive report dictionary
        """
        metrics = self.get_false_positive_metrics(days)
        recommendations = self.get_pattern_recommendations()
        adjustments = self.get_confidence_adjustment_suggestions()
        blacklist = list(self.pattern_blacklist)

        return {
            'report_generated': datetime.now(UTC).isoformat(),
            'period_days': days,
            'metrics': {
                'total_detections': metrics.total_detections,
                'false_positives': metrics.false_positives,
                'false_positive_rate': metrics.false_positive_rate,
                'by_type': metrics.by_type,
                'by_confidence_range': metrics.by_confidence_range,
                'trend_7_days': metrics.trend_7_days,
                'trend_30_days': metrics.trend_30_days
            },
            'recommendations': recommendations,
            'confidence_adjustments': adjustments,
            'pattern_blacklist': blacklist,
            'validation_stats': {
                'total_validated': len(self.validation_feedback),
                'validation_rate': len(self.validation_feedback) / len(self.false_positive_reports) * 100
                    if self.false_positive_reports else 0
            }
        }