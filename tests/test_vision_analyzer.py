"""
Unit tests for VisionAnalyzer confidence filtering functionality

Tests Requirements 21.1, 21.2, 21.3:
- 21.1: Include ingredients with confidence >= 0.7 automatically
- 21.2: Flag ingredients with confidence 0.5-0.7 for user confirmation
- 21.3: Exclude ingredients with confidence < 0.5
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision_analyzer import VisionAnalyzer
from config.env import Config


class TestVisionAnalyzerConfidenceFiltering(unittest.TestCase):
    """Test confidence threshold filtering in VisionAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock boto3 client to avoid AWS calls
        with patch('boto3.client'):
            self.analyzer = VisionAnalyzer()
    
    def test_confidence_thresholds_from_config(self):
        """Test that confidence thresholds are loaded from config"""
        self.assertEqual(self.analyzer.confidence_high, Config.VISION_CONFIDENCE_HIGH)
        self.assertEqual(self.analyzer.confidence_medium, Config.VISION_CONFIDENCE_MEDIUM)
        self.assertEqual(self.analyzer.confidence_high, 0.7)
        self.assertEqual(self.analyzer.confidence_medium, 0.5)
    
    def test_filter_high_confidence_ingredients(self):
        """Test Requirement 21.1: Include ingredients with confidence >= 0.7"""
        inventory = {
            "total_items": 3,
            "ingredients": [
                {"ingredient_name": "brinjal", "confidence_score": 0.95},
                {"ingredient_name": "rice", "confidence_score": 0.7},
                {"ingredient_name": "curry_leaves", "confidence_score": 0.85}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        # All ingredients should be in high confidence
        self.assertEqual(len(high), 3)
        self.assertEqual(len(medium), 0)
        self.assertEqual(len(low), 0)
        
        # Verify all high confidence ingredients
        high_names = [ing["ingredient_name"] for ing in high]
        self.assertIn("brinjal", high_names)
        self.assertIn("rice", high_names)
        self.assertIn("curry_leaves", high_names)
    
    def test_filter_medium_confidence_ingredients(self):
        """Test Requirement 21.2: Flag ingredients with confidence 0.5-0.7 for confirmation"""
        inventory = {
            "total_items": 3,
            "ingredients": [
                {"ingredient_name": "tamarind", "confidence_score": 0.65},
                {"ingredient_name": "gongura", "confidence_score": 0.5},
                {"ingredient_name": "turmeric", "confidence_score": 0.69}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        # All ingredients should be in medium confidence
        self.assertEqual(len(high), 0)
        self.assertEqual(len(medium), 3)
        self.assertEqual(len(low), 0)
        
        # Verify all medium confidence ingredients
        medium_names = [ing["ingredient_name"] for ing in medium]
        self.assertIn("tamarind", medium_names)
        self.assertIn("gongura", medium_names)
        self.assertIn("turmeric", medium_names)
    
    def test_filter_low_confidence_ingredients(self):
        """Test Requirement 21.3: Exclude ingredients with confidence < 0.5"""
        inventory = {
            "total_items": 3,
            "ingredients": [
                {"ingredient_name": "unknown1", "confidence_score": 0.49},
                {"ingredient_name": "unknown2", "confidence_score": 0.2},
                {"ingredient_name": "unknown3", "confidence_score": 0.0}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        # All ingredients should be in low confidence
        self.assertEqual(len(high), 0)
        self.assertEqual(len(medium), 0)
        self.assertEqual(len(low), 3)
        
        # Verify all low confidence ingredients
        low_names = [ing["ingredient_name"] for ing in low]
        self.assertIn("unknown1", low_names)
        self.assertIn("unknown2", low_names)
        self.assertIn("unknown3", low_names)
    
    def test_filter_mixed_confidence_levels(self):
        """Test filtering with mixed confidence levels"""
        inventory = {
            "total_items": 6,
            "ingredients": [
                {"ingredient_name": "brinjal", "confidence_score": 0.95},  # high
                {"ingredient_name": "rice", "confidence_score": 0.7},      # high (boundary)
                {"ingredient_name": "tamarind", "confidence_score": 0.65}, # medium
                {"ingredient_name": "gongura", "confidence_score": 0.5},   # medium (boundary)
                {"ingredient_name": "unknown1", "confidence_score": 0.49}, # low (boundary)
                {"ingredient_name": "unknown2", "confidence_score": 0.1}   # low
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        # Verify counts
        self.assertEqual(len(high), 2)
        self.assertEqual(len(medium), 2)
        self.assertEqual(len(low), 2)
        
        # Verify high confidence ingredients
        high_names = [ing["ingredient_name"] for ing in high]
        self.assertIn("brinjal", high_names)
        self.assertIn("rice", high_names)
        
        # Verify medium confidence ingredients
        medium_names = [ing["ingredient_name"] for ing in medium]
        self.assertIn("tamarind", medium_names)
        self.assertIn("gongura", medium_names)
        
        # Verify low confidence ingredients
        low_names = [ing["ingredient_name"] for ing in low]
        self.assertIn("unknown1", low_names)
        self.assertIn("unknown2", low_names)
    
    def test_filter_empty_inventory(self):
        """Test filtering with empty inventory"""
        inventory = {
            "total_items": 0,
            "ingredients": []
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        self.assertEqual(len(high), 0)
        self.assertEqual(len(medium), 0)
        self.assertEqual(len(low), 0)
    
    def test_filter_missing_confidence_score(self):
        """Test filtering when confidence_score is missing (defaults to 0)"""
        inventory = {
            "total_items": 1,
            "ingredients": [
                {"ingredient_name": "unknown"}  # No confidence_score
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        # Should be in low confidence (default 0)
        self.assertEqual(len(high), 0)
        self.assertEqual(len(medium), 0)
        self.assertEqual(len(low), 1)
    
    def test_confidence_summary_structure(self):
        """Test get_confidence_summary returns correct structure"""
        inventory = {
            "total_items": 6,
            "ingredients": [
                {"ingredient_name": "brinjal", "confidence_score": 0.95},
                {"ingredient_name": "rice", "confidence_score": 0.85},
                {"ingredient_name": "tamarind", "confidence_score": 0.65},
                {"ingredient_name": "gongura", "confidence_score": 0.55},
                {"ingredient_name": "unknown1", "confidence_score": 0.3},
                {"ingredient_name": "unknown2", "confidence_score": 0.1}
            ]
        }
        
        summary = self.analyzer.get_confidence_summary(inventory)
        
        # Verify structure
        self.assertIn("total_detected", summary)
        self.assertIn("high_confidence", summary)
        self.assertIn("medium_confidence", summary)
        self.assertIn("low_confidence", summary)
        
        # Verify total
        self.assertEqual(summary["total_detected"], 6)
        
        # Verify high confidence
        self.assertEqual(summary["high_confidence"]["count"], 2)
        self.assertEqual(summary["high_confidence"]["action"], "automatically_included")
        self.assertIn("0.7", summary["high_confidence"]["threshold"])
        
        # Verify medium confidence
        self.assertEqual(summary["medium_confidence"]["count"], 2)
        self.assertEqual(summary["medium_confidence"]["action"], "user_confirmation_needed")
        self.assertIn("0.5", summary["medium_confidence"]["threshold"])
        self.assertIn("0.7", summary["medium_confidence"]["threshold"])
        
        # Verify low confidence
        self.assertEqual(summary["low_confidence"]["count"], 2)
        self.assertEqual(summary["low_confidence"]["action"], "excluded")
        self.assertIn("0.5", summary["low_confidence"]["threshold"])
    
    def test_boundary_value_0_7(self):
        """Test boundary value: confidence exactly 0.7 should be high"""
        inventory = {
            "total_items": 1,
            "ingredients": [
                {"ingredient_name": "rice", "confidence_score": 0.7}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        self.assertEqual(len(high), 1)
        self.assertEqual(len(medium), 0)
        self.assertEqual(len(low), 0)
    
    def test_boundary_value_0_5(self):
        """Test boundary value: confidence exactly 0.5 should be medium"""
        inventory = {
            "total_items": 1,
            "ingredients": [
                {"ingredient_name": "gongura", "confidence_score": 0.5}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        self.assertEqual(len(high), 0)
        self.assertEqual(len(medium), 1)
        self.assertEqual(len(low), 0)
    
    def test_boundary_value_just_below_0_7(self):
        """Test boundary value: confidence 0.6999 should be medium"""
        inventory = {
            "total_items": 1,
            "ingredients": [
                {"ingredient_name": "tamarind", "confidence_score": 0.6999}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        self.assertEqual(len(high), 0)
        self.assertEqual(len(medium), 1)
        self.assertEqual(len(low), 0)
    
    def test_boundary_value_just_below_0_5(self):
        """Test boundary value: confidence 0.4999 should be low"""
        inventory = {
            "total_items": 1,
            "ingredients": [
                {"ingredient_name": "unknown", "confidence_score": 0.4999}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        self.assertEqual(len(high), 0)
        self.assertEqual(len(medium), 0)
        self.assertEqual(len(low), 1)
    
    def test_confidence_score_1_0(self):
        """Test maximum confidence score 1.0"""
        inventory = {
            "total_items": 1,
            "ingredients": [
                {"ingredient_name": "rice", "confidence_score": 1.0}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        self.assertEqual(len(high), 1)
        self.assertEqual(len(medium), 0)
        self.assertEqual(len(low), 0)
    
    def test_confidence_score_0_0(self):
        """Test minimum confidence score 0.0"""
        inventory = {
            "total_items": 1,
            "ingredients": [
                {"ingredient_name": "unknown", "confidence_score": 0.0}
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        self.assertEqual(len(high), 0)
        self.assertEqual(len(medium), 0)
        self.assertEqual(len(low), 1)


if __name__ == '__main__':
    unittest.main()
