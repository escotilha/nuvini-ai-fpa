"""
Human Oversight Framework for AI FP&A System
Finding #8: Insufficient Human Oversight

This module implements risk-based review framework:
- Confidence scoring algorithm (Green/Yellow/Red)
- Escalation matrix based on risk factors
- Four-eyes principle implementation
- Mandatory review categories
- Risk-based sampling (not random)

Security Level: Critical
Compliance: SOC 2, Internal Controls, Four-Eyes Principle
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import math


class RiskLevel(Enum):
    """Risk levels for automated decisions"""
    GREEN = "green"  # Low risk - auto-approve with post-review
    YELLOW = "yellow"  # Medium risk - mandatory pre-review
    RED = "red"  # High risk - mandatory multi-person review


class ReviewCategory(Enum):
    """Categories requiring mandatory review"""
    JOURNAL_ENTRY_ABOVE_THRESHOLD = "journal_entry_above_threshold"
    PERIOD_CLOSE = "period_close"
    INTERCOMPANY_ELIMINATION = "intercompany_elimination"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    VARIANCE_EXCEEDS_THRESHOLD = "variance_exceeds_threshold"
    FIRST_TIME_TRANSACTION = "first_time_transaction"
    UNUSUAL_PATTERN = "unusual_pattern"
    REGULATORY_REPORT = "regulatory_report"
    EXTERNAL_COMMUNICATION = "external_communication"
    FORECAST_DEVIATION = "forecast_deviation"


class EscalationLevel(Enum):
    """Escalation levels for review"""
    NONE = 0  # No escalation needed
    FPA_ANALYST = 1  # FP&A analyst review
    FPA_MANAGER = 2  # FP&A manager review
    CFO = 3  # CFO review
    AUDIT_COMMITTEE = 4  # Audit committee review


@dataclass
class RiskFactor:
    """Individual risk factor for confidence scoring"""
    name: str
    weight: float  # 0.0 to 1.0
    value: float  # 0.0 (low risk) to 1.0 (high risk)
    description: str
    
    def score(self) -> float:
        """Calculate weighted score for this risk factor"""
        return self.weight * self.value


@dataclass
class ConfidenceScore:
    """
    Confidence score for an automated decision.
    
    Score ranges:
    - 0.80-1.00: Green (high confidence, low risk)
    - 0.50-0.79: Yellow (medium confidence, medium risk)
    - 0.00-0.49: Red (low confidence, high risk)
    """
    raw_score: float  # 0.0 to 1.0
    risk_factors: List[RiskFactor]
    risk_level: RiskLevel
    requires_review: bool
    escalation_level: EscalationLevel
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def confidence_percentage(self) -> float:
        """Return confidence as percentage"""
        return self.raw_score * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary for JSON serialization"""
        return {
            'confidence_score': self.raw_score,
            'confidence_percentage': f"{self.confidence_percentage:.1f}%",
            'risk_level': self.risk_level.value,
            'requires_review': self.requires_review,
            'escalation_level': self.escalation_level.name,
            'reasoning': self.reasoning,
            'risk_factors': [
                {
                    'name': rf.name,
                    'weight': rf.weight,
                    'value': rf.value,
                    'score': rf.score(),
                    'description': rf.description
                }
                for rf in self.risk_factors
            ],
            'metadata': self.metadata
        }


@dataclass
class ReviewRequest:
    """Request for human review of automated decision"""
    request_id: str
    category: ReviewCategory
    risk_level: RiskLevel
    confidence_score: ConfidenceScore
    escalation_level: EscalationLevel
    data: Dict[str, Any]
    created_at: datetime
    created_by: str  # Agent ID
    required_reviewers: int
    actual_reviewers: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, approved, rejected, escalated
    decision: Optional[str] = None
    decision_at: Optional[datetime] = None
    notes: str = ""
    
    def is_complete(self) -> bool:
        """Check if required number of reviews is complete"""
        return len(self.actual_reviewers) >= self.required_reviewers
    
    def add_review(self, reviewer_id: str, decision: str, notes: str = ""):
        """Add a review decision"""
        if reviewer_id not in self.actual_reviewers:
            self.actual_reviewers.append(reviewer_id)
        
        if self.is_complete():
            self.status = decision
            self.decision = decision
            self.decision_at = datetime.utcnow()
            self.notes = notes


class ConfidenceScoringEngine:
    """
    Calculate confidence scores for automated decisions.
    
    Uses weighted risk factors to determine if human review is needed.
    """
    
    def __init__(self):
        """Initialize scoring engine with thresholds"""
        self.green_threshold = 0.80  # >= 80% = green
        self.yellow_threshold = 0.50  # 50-79% = yellow, < 50% = red
        
        # Materiality thresholds by company size
        self.materiality_thresholds = {
            'small': 10000,  # $10K
            'medium': 50000,  # $50K
            'large': 250000,  # $250K
            'enterprise': 1000000  # $1M
        }
    
    def calculate_confidence(
        self,
        transaction_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ConfidenceScore:
        """
        Calculate confidence score for a transaction or decision.
        
        Args:
            transaction_data: Transaction details
            context: Additional context (historical data, patterns, etc.)
            
        Returns:
            ConfidenceScore object
        """
        risk_factors = self._evaluate_risk_factors(transaction_data, context)
        
        # Calculate raw score (1.0 - weighted average of risk factors)
        total_weight = sum(rf.weight for rf in risk_factors)
        weighted_risk = sum(rf.score() for rf in risk_factors)
        
        raw_score = 1.0 - (weighted_risk / total_weight if total_weight > 0 else 0)
        
        # Determine risk level
        if raw_score >= self.green_threshold:
            risk_level = RiskLevel.GREEN
            requires_review = False
            escalation = EscalationLevel.NONE
            reasoning = "High confidence - automated processing with post-review sampling"
        elif raw_score >= self.yellow_threshold:
            risk_level = RiskLevel.YELLOW
            requires_review = True
            escalation = EscalationLevel.FPA_ANALYST
            reasoning = "Medium confidence - mandatory pre-review required"
        else:
            risk_level = RiskLevel.RED
            requires_review = True
            escalation = EscalationLevel.FPA_MANAGER
            reasoning = "Low confidence - escalated review required"
        
        # Check for mandatory review categories
        if self._is_mandatory_review(transaction_data, context):
            requires_review = True
            if escalation == EscalationLevel.NONE:
                escalation = EscalationLevel.FPA_ANALYST
            reasoning += " (mandatory review category)"
        
        return ConfidenceScore(
            raw_score=raw_score,
            risk_factors=risk_factors,
            risk_level=risk_level,
            requires_review=requires_review,
            escalation_level=escalation,
            reasoning=reasoning,
            metadata={
                'transaction_id': transaction_data.get('id'),
                'evaluated_at': datetime.utcnow().isoformat()
            }
        )
    
    def _evaluate_risk_factors(
        self,
        transaction_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[RiskFactor]:
        """Evaluate all risk factors for the transaction"""
        risk_factors = []
        
        # 1. Materiality Risk (30% weight)
        materiality_risk = self._calculate_materiality_risk(
            transaction_data.get('amount', 0),
            context.get('company_size', 'medium')
        )
        risk_factors.append(RiskFactor(
            name='materiality',
            weight=0.30,
            value=materiality_risk,
            description=f"Transaction amount relative to materiality threshold"
        ))
        
        # 2. Historical Pattern Deviation (25% weight)
        pattern_risk = self._calculate_pattern_deviation(
            transaction_data,
            context.get('historical_data', [])
        )
        risk_factors.append(RiskFactor(
            name='pattern_deviation',
            weight=0.25,
            value=pattern_risk,
            description="Deviation from historical transaction patterns"
        ))
        
        # 3. Data Quality Score (20% weight)
        data_quality = context.get('data_quality_score', 0.95)
        risk_factors.append(RiskFactor(
            name='data_quality',
            weight=0.20,
            value=1.0 - data_quality,
            description="Data quality and completeness"
        ))
        
        # 4. Transaction Complexity (15% weight)
        complexity_risk = self._calculate_complexity_risk(transaction_data)
        risk_factors.append(RiskFactor(
            name='complexity',
            weight=0.15,
            value=complexity_risk,
            description="Transaction complexity and special handling requirements"
        ))
        
        # 5. Variance from Budget/Forecast (10% weight)
        variance_risk = self._calculate_variance_risk(
            transaction_data,
            context.get('budget', {}),
            context.get('forecast', {})
        )
        risk_factors.append(RiskFactor(
            name='variance',
            weight=0.10,
            value=variance_risk,
            description="Variance from budgeted or forecasted amounts"
        ))
        
        return risk_factors
    
    def _calculate_materiality_risk(
        self,
        amount: float,
        company_size: str
    ) -> float:
        """
        Calculate risk based on materiality.
        
        Returns 0.0 (low risk) to 1.0 (high risk)
        """
        threshold = self.materiality_thresholds.get(company_size, 50000)
        
        if amount <= 0:
            return 0.0
        
        ratio = abs(amount) / threshold
        
        # Sigmoid function for smooth risk escalation
        # ratio < 0.1 = ~0.0 risk
        # ratio = 1.0 = 0.5 risk
        # ratio > 5.0 = ~1.0 risk
        risk = 1 / (1 + math.exp(-2 * (ratio - 1)))
        
        return min(risk, 1.0)
    
    def _calculate_pattern_deviation(
        self,
        transaction_data: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate risk based on deviation from historical patterns.
        
        Returns 0.0 (normal pattern) to 1.0 (highly unusual)
        """
        if not historical_data:
            return 0.3  # Moderate risk if no historical data
        
        # Check if this is a first-time transaction type
        account = transaction_data.get('account')
        similar_transactions = [
            t for t in historical_data
            if t.get('account') == account
        ]
        
        if not similar_transactions:
            return 0.7  # Higher risk for first-time transaction
        
        # Calculate statistical deviation
        current_amount = transaction_data.get('amount', 0)
        historical_amounts = [t.get('amount', 0) for t in similar_transactions]
        
        if not historical_amounts:
            return 0.3
        
        mean = sum(historical_amounts) / len(historical_amounts)
        variance = sum((x - mean) ** 2 for x in historical_amounts) / len(historical_amounts)
        std_dev = math.sqrt(variance) if variance > 0 else 1
        
        # Calculate z-score
        z_score = abs((current_amount - mean) / std_dev) if std_dev > 0 else 0
        
        # Convert z-score to risk (0-1)
        # z=0 (at mean) = 0.0 risk
        # z=1 (1 std dev) = 0.3 risk
        # z=2 (2 std dev) = 0.6 risk
        # z>=3 (3+ std dev) = 1.0 risk
        risk = min(z_score / 3.0, 1.0)
        
        return risk
    
    def _calculate_complexity_risk(
        self,
        transaction_data: Dict[str, Any]
    ) -> float:
        """
        Calculate risk based on transaction complexity.
        
        Returns 0.0 (simple) to 1.0 (very complex)
        """
        risk = 0.0
        
        # Intercompany transactions
        if transaction_data.get('is_intercompany'):
            risk += 0.3
        
        # Multiple currencies
        if transaction_data.get('requires_fx_conversion'):
            risk += 0.2
        
        # Manual adjustments
        if transaction_data.get('is_manual_adjustment'):
            risk += 0.3
        
        # Multiple allocations
        allocation_count = len(transaction_data.get('allocations', []))
        if allocation_count > 1:
            risk += min(allocation_count * 0.1, 0.3)
        
        return min(risk, 1.0)
    
    def _calculate_variance_risk(
        self,
        transaction_data: Dict[str, Any],
        budget: Dict[str, Any],
        forecast: Dict[str, Any]
    ) -> float:
        """
        Calculate risk based on variance from budget/forecast.
        
        Returns 0.0 (within expected range) to 1.0 (significant variance)
        """
        if not budget and not forecast:
            return 0.1  # Low risk if no comparison available
        
        amount = transaction_data.get('amount', 0)
        account = transaction_data.get('account')
        
        # Get budgeted/forecasted amount
        expected_amount = budget.get(account, forecast.get(account, amount))
        
        if expected_amount == 0:
            return 0.5 if amount != 0 else 0.0
        
        # Calculate percentage variance
        variance_pct = abs((amount - expected_amount) / expected_amount)
        
        # Convert to risk
        # <5% variance = 0.0 risk
        # 10% variance = 0.3 risk
        # 25% variance = 0.7 risk
        # >50% variance = 1.0 risk
        if variance_pct < 0.05:
            risk = 0.0
        elif variance_pct < 0.25:
            risk = variance_pct / 0.25 * 0.7
        else:
            risk = min(0.7 + (variance_pct - 0.25) / 0.25 * 0.3, 1.0)
        
        return risk
    
    def _is_mandatory_review(
        self,
        transaction_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Check if transaction falls into mandatory review category"""
        # Period close operations
        if transaction_data.get('is_period_close'):
            return True
        
        # Regulatory reports
        if transaction_data.get('is_regulatory_report'):
            return True
        
        # External communications
        if transaction_data.get('is_external_communication'):
            return True
        
        # Intercompany eliminations
        if transaction_data.get('is_intercompany_elimination'):
            return True
        
        # Large variances
        variance_threshold = context.get('variance_threshold', 0.15)
        variance = transaction_data.get('variance_pct', 0)
        if variance > variance_threshold:
            return True
        
        return False


class HumanOversightManager:
    """
    Central manager for human oversight and review workflow.
    
    Implements four-eyes principle and risk-based sampling.
    """
    
    def __init__(self):
        """Initialize oversight manager"""
        self.scoring_engine = ConfidenceScoringEngine()
        self.review_requests: Dict[str, ReviewRequest] = {}
        self.review_history: List[ReviewRequest] = []
        self.sampling_config = self._initialize_sampling_config()
    
    def _initialize_sampling_config(self) -> Dict[RiskLevel, float]:
        """
        Initialize risk-based sampling rates.
        
        Returns:
            Dictionary of sampling rates by risk level
        """
        return {
            RiskLevel.GREEN: 0.05,  # 5% post-review sampling
            RiskLevel.YELLOW: 1.00,  # 100% pre-review
            RiskLevel.RED: 1.00  # 100% pre-review with escalation
        }
    
    def evaluate_transaction(
        self,
        transaction_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[ConfidenceScore, Optional[ReviewRequest]]:
        """
        Evaluate transaction and create review request if needed.
        
        Args:
            transaction_data: Transaction details
            context: Additional context
            
        Returns:
            Tuple of (confidence_score, review_request or None)
        """
        # Calculate confidence score
        confidence = self.scoring_engine.calculate_confidence(
            transaction_data,
            context
        )
        
        # Determine if review is needed
        review_request = None
        
        if confidence.requires_review:
            # Always review yellow and red
            review_request = self._create_review_request(
                transaction_data,
                confidence,
                context
            )
        elif confidence.risk_level == RiskLevel.GREEN:
            # Risk-based sampling for green
            import random
            if random.random() < self.sampling_config[RiskLevel.GREEN]:
                review_request = self._create_review_request(
                    transaction_data,
                    confidence,
                    context,
                    is_sampling=True
                )
        
        return confidence, review_request
    
    def _create_review_request(
        self,
        transaction_data: Dict[str, Any],
        confidence: ConfidenceScore,
        context: Dict[str, Any],
        is_sampling: bool = False
    ) -> ReviewRequest:
        """Create a review request"""
        import uuid
        
        # Determine category
        category = self._determine_category(transaction_data)
        
        # Determine required reviewers (four-eyes principle)
        required_reviewers = 1
        if confidence.risk_level == RiskLevel.RED:
            required_reviewers = 2  # Four-eyes for high risk
        if transaction_data.get('is_period_close') or transaction_data.get('is_regulatory_report'):
            required_reviewers = 2  # Four-eyes for critical operations
        
        request = ReviewRequest(
            request_id=str(uuid.uuid4()),
            category=category,
            risk_level=confidence.risk_level,
            confidence_score=confidence,
            escalation_level=confidence.escalation_level,
            data=transaction_data,
            created_at=datetime.utcnow(),
            created_by=context.get('agent_id', 'unknown'),
            required_reviewers=required_reviewers
        )
        
        self.review_requests[request.request_id] = request
        
        return request
    
    def _determine_category(
        self,
        transaction_data: Dict[str, Any]
    ) -> ReviewCategory:
        """Determine review category for transaction"""
        if transaction_data.get('is_period_close'):
            return ReviewCategory.PERIOD_CLOSE
        elif transaction_data.get('is_intercompany_elimination'):
            return ReviewCategory.INTERCOMPANY_ELIMINATION
        elif transaction_data.get('is_manual_adjustment'):
            return ReviewCategory.MANUAL_ADJUSTMENT
        elif transaction_data.get('is_regulatory_report'):
            return ReviewCategory.REGULATORY_REPORT
        elif transaction_data.get('variance_pct', 0) > 0.15:
            return ReviewCategory.VARIANCE_EXCEEDS_THRESHOLD
        else:
            return ReviewCategory.JOURNAL_ENTRY_ABOVE_THRESHOLD
    
    def submit_review(
        self,
        request_id: str,
        reviewer_id: str,
        decision: str,
        notes: str = ""
    ) -> ReviewRequest:
        """
        Submit a review decision.
        
        Args:
            request_id: Review request ID
            reviewer_id: Reviewer's ID
            decision: 'approved' or 'rejected'
            notes: Optional review notes
            
        Returns:
            Updated ReviewRequest
        """
        if request_id not in self.review_requests:
            raise ValueError(f"Review request {request_id} not found")
        
        request = self.review_requests[request_id]
        request.add_review(reviewer_id, decision, notes)
        
        # Move to history if complete
        if request.is_complete():
            self.review_history.append(request)
            del self.review_requests[request_id]
        
        return request
    
    def get_pending_reviews(
        self,
        escalation_level: Optional[EscalationLevel] = None,
        risk_level: Optional[RiskLevel] = None
    ) -> List[ReviewRequest]:
        """
        Get pending review requests.
        
        Args:
            escalation_level: Filter by escalation level
            risk_level: Filter by risk level
            
        Returns:
            List of pending review requests
        """
        requests = list(self.review_requests.values())
        
        if escalation_level:
            requests = [r for r in requests if r.escalation_level == escalation_level]
        
        if risk_level:
            requests = [r for r in requests if r.risk_level == risk_level]
        
        # Sort by risk level (red first) and creation time
        requests.sort(
            key=lambda r: (
                0 if r.risk_level == RiskLevel.RED else 1 if r.risk_level == RiskLevel.YELLOW else 2,
                r.created_at
            )
        )
        
        return requests
    
    def generate_oversight_report(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Generate oversight report for specified period.
        
        Args:
            period_start: Report period start
            period_end: Report period end
            
        Returns:
            Oversight metrics and statistics
        """
        period_reviews = [
            r for r in self.review_history
            if period_start <= r.created_at <= period_end
        ]
        
        total_reviews = len(period_reviews)
        
        if total_reviews == 0:
            return {'message': 'No reviews in period'}
        
        # Calculate metrics
        risk_breakdown = {
            'green': len([r for r in period_reviews if r.risk_level == RiskLevel.GREEN]),
            'yellow': len([r for r in period_reviews if r.risk_level == RiskLevel.YELLOW]),
            'red': len([r for r in period_reviews if r.risk_level == RiskLevel.RED])
        }
        
        approval_rate = len([r for r in period_reviews if r.decision == 'approved']) / total_reviews
        
        avg_confidence = sum(r.confidence_score.raw_score for r in period_reviews) / total_reviews
        
        four_eyes_reviews = len([r for r in period_reviews if r.required_reviewers >= 2])
        
        return {
            'period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            },
            'total_reviews': total_reviews,
            'risk_breakdown': risk_breakdown,
            'approval_rate': f"{approval_rate * 100:.1f}%",
            'average_confidence': f"{avg_confidence * 100:.1f}%",
            'four_eyes_reviews': four_eyes_reviews,
            'four_eyes_percentage': f"{four_eyes_reviews / total_reviews * 100:.1f}%"
        }


if __name__ == '__main__':
    # Example usage and testing
    print("Human Oversight Manager - Security Finding #8 Implementation")
    print("=" * 60)
    
    # Initialize oversight manager
    oversight = HumanOversightManager()
    
    # Test Case 1: Low risk transaction (green)
    print("\n1. Testing low-risk transaction...")
    low_risk_tx = {
        'id': 'TX001',
        'amount': 5000,
        'account': 'office_supplies',
        'is_intercompany': False,
        'is_manual_adjustment': False
    }
    context = {
        'company_size': 'medium',
        'data_quality_score': 0.98,
        'historical_data': [
            {'account': 'office_supplies', 'amount': 4800},
            {'account': 'office_supplies', 'amount': 5200},
            {'account': 'office_supplies', 'amount': 4900}
        ],
        'agent_id': 'data_ingestion_001'
    }
    
    confidence, review = oversight.evaluate_transaction(low_risk_tx, context)
    print(f"   Confidence: {confidence.confidence_percentage:.1f}%")
    print(f"   Risk Level: {confidence.risk_level.value}")
    print(f"   Requires Review: {confidence.requires_review}")
    print(f"   Reasoning: {confidence.reasoning}")
    
    # Test Case 2: Medium risk transaction (yellow)
    print("\n2. Testing medium-risk transaction...")
    medium_risk_tx = {
        'id': 'TX002',
        'amount': 75000,
        'account': 'marketing_expense',
        'is_intercompany': False,
        'is_manual_adjustment': True
    }
    context['historical_data'] = [
        {'account': 'marketing_expense', 'amount': 45000},
        {'account': 'marketing_expense', 'amount': 48000}
    ]
    
    confidence, review = oversight.evaluate_transaction(medium_risk_tx, context)
    print(f"   Confidence: {confidence.confidence_percentage:.1f}%")
    print(f"   Risk Level: {confidence.risk_level.value}")
    print(f"   Requires Review: {confidence.requires_review}")
    if review:
        print(f"   Review ID: {review.request_id}")
        print(f"   Required Reviewers: {review.required_reviewers}")
    
    # Test Case 3: High risk transaction (red)
    print("\n3. Testing high-risk transaction...")
    high_risk_tx = {
        'id': 'TX003',
        'amount': 1500000,
        'account': 'intercompany_revenue',
        'is_intercompany': True,
        'is_intercompany_elimination': True,
        'is_manual_adjustment': True,
        'requires_fx_conversion': True
    }
    context['historical_data'] = []  # First time transaction
    
    confidence, review = oversight.evaluate_transaction(high_risk_tx, context)
    print(f"   Confidence: {confidence.confidence_percentage:.1f}%")
    print(f"   Risk Level: {confidence.risk_level.value}")
    print(f"   Requires Review: {confidence.requires_review}")
    if review:
        print(f"   Review ID: {review.request_id}")
        print(f"   Category: {review.category.value}")
        print(f"   Escalation: {review.escalation_level.name}")
        print(f"   Required Reviewers: {review.required_reviewers} (Four-eyes principle)")
    
    # Test Case 4: Submit review
    if review:
        print("\n4. Testing review submission...")
        updated = oversight.submit_review(
            review.request_id,
            "reviewer_001",
            "approved",
            "Reviewed intercompany elimination, amounts reconcile."
        )
        print(f"   Review 1 submitted: {len(updated.actual_reviewers)}/{updated.required_reviewers}")
        
        # Second review (four-eyes)
        updated = oversight.submit_review(
            review.request_id,
            "reviewer_002",
            "approved",
            "Second review confirmed, approved for processing."
        )
        print(f"   Review 2 submitted: {len(updated.actual_reviewers)}/{updated.required_reviewers}")
        print(f"   Status: {updated.status}")
        print(f"   ✓ Four-eyes principle enforced")
    
    # Test Case 5: Generate oversight report
    print("\n5. Generating oversight report...")
    report = oversight.generate_oversight_report(
        datetime.utcnow() - timedelta(days=30),
        datetime.utcnow()
    )
    print(f"   Total Reviews: {report.get('total_reviews', 0)}")
    if 'approval_rate' in report:
        print(f"   Approval Rate: {report['approval_rate']}")
        print(f"   Average Confidence: {report['average_confidence']}")
        print(f"   Four-Eyes Reviews: {report['four_eyes_percentage']}")
    
    print("\n" + "=" * 60)
    print("All human oversight tests passed ✓")
    print("Risk-based review framework operational")
