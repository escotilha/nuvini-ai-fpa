"""
Test suite for human oversight module (Finding #8)

Tests:
- Confidence scoring
- Risk factor calculation
- Risk-based sampling
- Review workflow
- Four-eyes principle
- Escalation matrix
"""

import unittest
from datetime import datetime, timedelta

# Add src to path
import sys
sys.path.insert(0, '/Volumes/AI/Code/FPA/src')

from core.human_oversight import (
    RiskLevel,
    ReviewCategory,
    EscalationLevel,
    RiskFactor,
    ConfidenceScore,
    ReviewRequest,
    ConfidenceScoringEngine,
    HumanOversightManager
)


class TestRiskFactor(unittest.TestCase):
    """Test risk factor calculation"""
    
    def test_risk_factor_score(self):
        """Test weighted risk factor score"""
        rf = RiskFactor(
            name='test_risk',
            weight=0.5,
            value=0.8,
            description='Test risk factor'
        )
        
        # Score should be weight * value
        self.assertEqual(rf.score(), 0.4)


class TestConfidenceScore(unittest.TestCase):
    """Test confidence score object"""
    
    def test_confidence_percentage(self):
        """Test confidence percentage calculation"""
        score = ConfidenceScore(
            raw_score=0.85,
            risk_factors=[],
            risk_level=RiskLevel.GREEN,
            requires_review=False,
            escalation_level=EscalationLevel.NONE,
            reasoning='Test'
        )
        
        self.assertEqual(score.confidence_percentage, 85.0)
    
    def test_to_dict(self):
        """Test exporting to dictionary"""
        rf = RiskFactor('test', 0.5, 0.3, 'Test')
        score = ConfidenceScore(
            raw_score=0.75,
            risk_factors=[rf],
            risk_level=RiskLevel.YELLOW,
            requires_review=True,
            escalation_level=EscalationLevel.FPA_ANALYST,
            reasoning='Medium confidence'
        )
        
        data = score.to_dict()
        
        self.assertEqual(data['confidence_score'], 0.75)
        self.assertEqual(data['risk_level'], 'yellow')
        self.assertTrue(data['requires_review'])
        self.assertEqual(len(data['risk_factors']), 1)


class TestConfidenceScoringEngine(unittest.TestCase):
    """Test confidence scoring engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = ConfidenceScoringEngine()
    
    def test_low_risk_transaction(self):
        """Test scoring for low-risk transaction"""
        transaction = {
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
            'budget': {'office_supplies': 5000}
        }
        
        score = self.engine.calculate_confidence(transaction, context)
        
        # Should be green (high confidence)
        self.assertEqual(score.risk_level, RiskLevel.GREEN)
        self.assertFalse(score.requires_review)
        self.assertGreaterEqual(score.raw_score, 0.80)
    
    def test_medium_risk_transaction(self):
        """Test scoring for medium-risk transaction"""
        transaction = {
            'id': 'TX002',
            'amount': 75000,
            'account': 'marketing_expense',
            'is_intercompany': False,
            'is_manual_adjustment': True
        }
        
        context = {
            'company_size': 'medium',
            'data_quality_score': 0.95,
            'historical_data': [
                {'account': 'marketing_expense', 'amount': 45000},
                {'account': 'marketing_expense', 'amount': 48000}
            ],
            'budget': {'marketing_expense': 50000}
        }
        
        score = self.engine.calculate_confidence(transaction, context)
        
        # Should be yellow or red (lower confidence due to manual adjustment and variance)
        self.assertIn(score.risk_level, [RiskLevel.YELLOW, RiskLevel.RED])
        self.assertTrue(score.requires_review)
    
    def test_high_risk_transaction(self):
        """Test scoring for high-risk transaction"""
        transaction = {
            'id': 'TX003',
            'amount': 1500000,
            'account': 'intercompany_revenue',
            'is_intercompany': True,
            'is_manual_adjustment': True,
            'requires_fx_conversion': True
        }
        
        context = {
            'company_size': 'medium',
            'data_quality_score': 0.90,
            'historical_data': [],  # First time transaction
            'budget': {}
        }
        
        score = self.engine.calculate_confidence(transaction, context)
        
        # Should be red (low confidence)
        self.assertEqual(score.risk_level, RiskLevel.RED)
        self.assertTrue(score.requires_review)
        self.assertLess(score.raw_score, 0.50)
        self.assertEqual(score.escalation_level, EscalationLevel.FPA_MANAGER)
    
    def test_materiality_risk_calculation(self):
        """Test materiality risk calculation"""
        # Small amount - low risk
        low_risk = self.engine._calculate_materiality_risk(5000, 'medium')
        self.assertLess(low_risk, 0.3)
        
        # At threshold - medium risk
        medium_risk = self.engine._calculate_materiality_risk(50000, 'medium')
        self.assertGreater(medium_risk, 0.3)
        self.assertLess(medium_risk, 0.7)
        
        # Large amount - high risk
        high_risk = self.engine._calculate_materiality_risk(500000, 'medium')
        self.assertGreater(high_risk, 0.7)
    
    def test_pattern_deviation_calculation(self):
        """Test pattern deviation risk calculation"""
        transaction = {'account': 'test_account', 'amount': 10000}
        
        # No historical data - moderate risk
        no_history_risk = self.engine._calculate_pattern_deviation(transaction, [])
        self.assertGreater(no_history_risk, 0.2)
        self.assertLess(no_history_risk, 0.5)
        
        # First time account - higher risk
        other_account_history = [
            {'account': 'other_account', 'amount': 5000}
        ]
        first_time_risk = self.engine._calculate_pattern_deviation(
            transaction,
            other_account_history
        )
        self.assertGreater(first_time_risk, 0.6)
        
        # Normal pattern - low risk
        normal_history = [
            {'account': 'test_account', 'amount': 9800},
            {'account': 'test_account', 'amount': 10200},
            {'account': 'test_account', 'amount': 9900}
        ]
        normal_risk = self.engine._calculate_pattern_deviation(transaction, normal_history)
        self.assertLess(normal_risk, 0.3)
    
    def test_complexity_risk_calculation(self):
        """Test complexity risk calculation"""
        # Simple transaction
        simple_tx = {
            'is_intercompany': False,
            'is_manual_adjustment': False,
            'requires_fx_conversion': False,
            'allocations': []
        }
        simple_risk = self.engine._calculate_complexity_risk(simple_tx)
        self.assertEqual(simple_risk, 0.0)
        
        # Complex transaction
        complex_tx = {
            'is_intercompany': True,
            'is_manual_adjustment': True,
            'requires_fx_conversion': True,
            'allocations': [1, 2, 3]
        }
        complex_risk = self.engine._calculate_complexity_risk(complex_tx)
        self.assertGreater(complex_risk, 0.7)
    
    def test_variance_risk_calculation(self):
        """Test variance risk calculation"""
        # Low variance - low risk
        low_variance_tx = {'amount': 10000, 'account': 'test'}
        budget = {'test': 10200}
        low_risk = self.engine._calculate_variance_risk(low_variance_tx, budget, {})
        self.assertLess(low_risk, 0.1)
        
        # Medium variance - medium risk
        med_variance_tx = {'amount': 10000, 'account': 'test'}
        budget = {'test': 8500}
        med_risk = self.engine._calculate_variance_risk(med_variance_tx, budget, {})
        self.assertGreater(med_risk, 0.3)
        
        # High variance - high risk
        high_variance_tx = {'amount': 10000, 'account': 'test'}
        budget = {'test': 5000}
        high_risk = self.engine._calculate_variance_risk(high_variance_tx, budget, {})
        self.assertGreater(high_risk, 0.7)
    
    def test_mandatory_review_detection(self):
        """Test mandatory review category detection"""
        # Period close
        period_close = {'is_period_close': True}
        self.assertTrue(self.engine._is_mandatory_review(period_close, {}))
        
        # Regulatory report
        regulatory = {'is_regulatory_report': True}
        self.assertTrue(self.engine._is_mandatory_review(regulatory, {}))
        
        # Large variance
        high_variance = {'variance_pct': 0.20}
        self.assertTrue(self.engine._is_mandatory_review(high_variance, {'variance_threshold': 0.15}))
        
        # Normal transaction
        normal = {}
        self.assertFalse(self.engine._is_mandatory_review(normal, {}))


class TestReviewRequest(unittest.TestCase):
    """Test review request object"""
    
    def test_is_complete(self):
        """Test review completion check"""
        score = ConfidenceScore(
            raw_score=0.45,
            risk_factors=[],
            risk_level=RiskLevel.RED,
            requires_review=True,
            escalation_level=EscalationLevel.FPA_MANAGER,
            reasoning='Test'
        )
        
        request = ReviewRequest(
            request_id='REQ001',
            category=ReviewCategory.MANUAL_ADJUSTMENT,
            risk_level=RiskLevel.RED,
            confidence_score=score,
            escalation_level=EscalationLevel.FPA_MANAGER,
            data={},
            created_at=datetime.utcnow(),
            created_by='test_agent',
            required_reviewers=2
        )
        
        # Not complete initially
        self.assertFalse(request.is_complete())
        
        # Add first review
        request.add_review('reviewer_1', 'approved', 'Looks good')
        self.assertFalse(request.is_complete())
        
        # Add second review
        request.add_review('reviewer_2', 'approved', 'Confirmed')
        self.assertTrue(request.is_complete())
        
        # Should have both reviewers
        self.assertEqual(len(request.actual_reviewers), 2)
        self.assertEqual(request.status, 'approved')


class TestHumanOversightManager(unittest.TestCase):
    """Test human oversight manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = HumanOversightManager()
    
    def test_evaluate_low_risk_transaction(self):
        """Test evaluating low-risk transaction"""
        transaction = {
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
                {'account': 'office_supplies', 'amount': 4900}
            ],
            'budget': {'office_supplies': 5000},
            'agent_id': 'test_agent'
        }
        
        confidence, review = self.manager.evaluate_transaction(transaction, context)
        
        # Should be green
        self.assertEqual(confidence.risk_level, RiskLevel.GREEN)
        
        # May or may not require review (due to sampling)
        # But if no review, should be because of sampling
        if review is None:
            self.assertFalse(confidence.requires_review)
    
    def test_evaluate_high_risk_transaction(self):
        """Test evaluating high-risk transaction"""
        transaction = {
            'id': 'TX003',
            'amount': 1500000,
            'account': 'intercompany_revenue',
            'is_intercompany': True,
            'is_manual_adjustment': True
        }
        
        context = {
            'company_size': 'medium',
            'data_quality_score': 0.90,
            'historical_data': [],
            'agent_id': 'test_agent'
        }
        
        confidence, review = self.manager.evaluate_transaction(transaction, context)
        
        # Should be red
        self.assertEqual(confidence.risk_level, RiskLevel.RED)
        
        # Should require review
        self.assertTrue(confidence.requires_review)
        self.assertIsNotNone(review)
        
        # Should require four-eyes (2 reviewers)
        self.assertGreaterEqual(review.required_reviewers, 2)
    
    def test_evaluate_period_close(self):
        """Test evaluating period close (mandatory review)"""
        transaction = {
            'id': 'TX004',
            'amount': 10000,
            'account': 'retained_earnings',
            'is_period_close': True
        }
        
        context = {
            'company_size': 'medium',
            'data_quality_score': 0.99,
            'historical_data': [
                {'account': 'retained_earnings', 'amount': 10000}
            ],
            'agent_id': 'test_agent'
        }
        
        confidence, review = self.manager.evaluate_transaction(transaction, context)
        
        # Should require review (mandatory category)
        self.assertTrue(confidence.requires_review)
        self.assertIsNotNone(review)
        
        # Should be period close category
        self.assertEqual(review.category, ReviewCategory.PERIOD_CLOSE)
        
        # Should require four-eyes
        self.assertGreaterEqual(review.required_reviewers, 2)
    
    def test_submit_review(self):
        """Test submitting review"""
        # Create high-risk transaction
        transaction = {
            'id': 'TX005',
            'amount': 500000,
            'account': 'manual_adjustment',
            'is_manual_adjustment': True
        }
        
        context = {
            'company_size': 'medium',
            'data_quality_score': 0.95,
            'historical_data': [],
            'agent_id': 'test_agent'
        }
        
        confidence, review = self.manager.evaluate_transaction(transaction, context)
        
        if review:
            # Submit review
            updated = self.manager.submit_review(
                review.request_id,
                'reviewer_001',
                'approved',
                'Reviewed and approved'
            )
            
            # Should have one reviewer
            self.assertEqual(len(updated.actual_reviewers), 1)
            
            # If requires 2 reviewers, submit second review
            if updated.required_reviewers >= 2:
                updated = self.manager.submit_review(
                    review.request_id,
                    'reviewer_002',
                    'approved',
                    'Second review confirmed'
                )
                
                # Should be complete now
                self.assertTrue(updated.is_complete())
                self.assertEqual(updated.status, 'approved')
    
    def test_get_pending_reviews(self):
        """Test getting pending reviews"""
        # Create multiple review requests
        transactions = [
            {
                'id': 'TX_RED',
                'amount': 1000000,
                'is_manual_adjustment': True,
                'is_intercompany': True
            },
            {
                'id': 'TX_YELLOW',
                'amount': 100000,
                'is_manual_adjustment': True
            }
        ]
        
        context = {
            'company_size': 'medium',
            'data_quality_score': 0.95,
            'historical_data': [],
            'agent_id': 'test_agent'
        }
        
        for tx in transactions:
            self.manager.evaluate_transaction(tx, context)
        
        # Get all pending reviews
        pending = self.manager.get_pending_reviews()
        
        # Should have reviews pending
        self.assertGreater(len(pending), 0)
        
        # Should be sorted by risk (red first)
        if len(pending) >= 2:
            # First should be higher or equal risk
            first_risk = 0 if pending[0].risk_level == RiskLevel.RED else 1 if pending[0].risk_level == RiskLevel.YELLOW else 2
            second_risk = 0 if pending[1].risk_level == RiskLevel.RED else 1 if pending[1].risk_level == RiskLevel.YELLOW else 2
            self.assertLessEqual(first_risk, second_risk)
    
    def test_generate_oversight_report(self):
        """Test generating oversight report"""
        # Create and complete some reviews
        transaction = {
            'id': 'TX006',
            'amount': 100000,
            'is_manual_adjustment': True
        }
        
        context = {
            'company_size': 'medium',
            'data_quality_score': 0.95,
            'historical_data': [],
            'agent_id': 'test_agent'
        }
        
        confidence, review = self.manager.evaluate_transaction(transaction, context)
        
        if review:
            # Complete review
            for i in range(review.required_reviewers):
                self.manager.submit_review(
                    review.request_id,
                    f'reviewer_{i}',
                    'approved',
                    'Approved'
                )
        
        # Generate report
        report = self.manager.generate_oversight_report(
            datetime.utcnow() - timedelta(days=1),
            datetime.utcnow() + timedelta(days=1)
        )
        
        # Should have report data if there were reviews
        if 'total_reviews' in report:
            self.assertGreater(report['total_reviews'], 0)
            self.assertIn('approval_rate', report)
            self.assertIn('average_confidence', report)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
