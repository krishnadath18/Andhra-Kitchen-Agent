"""
Integration test demonstrating confidence filtering workflow

This test shows how the confidence filtering works end-to-end:
1. VisionAnalyzer detects ingredients with confidence scores
2. filter_by_confidence() separates them into high/medium/low
3. get_confidence_summary() provides actionable information
"""

import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision_analyzer import VisionAnalyzer


class TestConfidenceFilteringIntegration(unittest.TestCase):
    """Integration test for confidence filtering workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        with patch('boto3.client'):
            self.analyzer = VisionAnalyzer()
    
    def test_complete_confidence_filtering_workflow(self):
        """
        Test complete workflow: detection -> filtering -> summary
        
        Simulates a realistic scenario where VisionAnalyzer detects
        various ingredients with different confidence levels.
        """
        # Simulated inventory from vision analysis
        inventory = {
            "total_items": 10,
            "detection_timestamp": "2024-01-15T10:30:00Z",
            "session_id": "test_session_123",
            "ingredients": [
                # High confidence - automatically included (Requirements 21.1)
                {
                    "ingredient_name": "brinjal",
                    "ingredient_name_telugu": "వంకాయ",
                    "quantity": 3,
                    "unit": "pieces",
                    "confidence_score": 0.95,
                    "category": "vegetable"
                },
                {
                    "ingredient_name": "rice",
                    "ingredient_name_telugu": "బియ్యం",
                    "quantity": 2,
                    "unit": "kg",
                    "confidence_score": 0.88,
                    "category": "grain"
                },
                {
                    "ingredient_name": "curry_leaves",
                    "ingredient_name_telugu": "కరివేపాకు",
                    "quantity": 1,
                    "unit": "bunches",
                    "confidence_score": 0.72,
                    "category": "spice"
                },
                # Medium confidence - needs user confirmation (Requirements 21.2)
                {
                    "ingredient_name": "tamarind",
                    "ingredient_name_telugu": "చింతపండు",
                    "quantity": 100,
                    "unit": "grams",
                    "confidence_score": 0.65,
                    "category": "spice"
                },
                {
                    "ingredient_name": "gongura",
                    "ingredient_name_telugu": "గోంగూర",
                    "quantity": 1,
                    "unit": "bunches",
                    "confidence_score": 0.58,
                    "category": "vegetable"
                },
                {
                    "ingredient_name": "drumstick",
                    "ingredient_name_telugu": "మునగకాయ",
                    "quantity": 5,
                    "unit": "pieces",
                    "confidence_score": 0.52,
                    "category": "vegetable"
                },
                # Low confidence - excluded (Requirements 21.3)
                {
                    "ingredient_name": "unknown_vegetable_1",
                    "quantity": 2,
                    "unit": "pieces",
                    "confidence_score": 0.45,
                    "category": "vegetable"
                },
                {
                    "ingredient_name": "unknown_spice_1",
                    "quantity": 50,
                    "unit": "grams",
                    "confidence_score": 0.32,
                    "category": "spice"
                },
                {
                    "ingredient_name": "unknown_item_1",
                    "quantity": 1,
                    "unit": "pieces",
                    "confidence_score": 0.18,
                    "category": "other"
                },
                {
                    "ingredient_name": "unknown_item_2",
                    "quantity": 1,
                    "unit": "pieces",
                    "confidence_score": 0.08,
                    "category": "other"
                }
            ]
        }
        
        # Step 1: Filter by confidence
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        # Verify filtering results
        self.assertEqual(len(high), 3, "Should have 3 high confidence ingredients")
        self.assertEqual(len(medium), 3, "Should have 3 medium confidence ingredients")
        self.assertEqual(len(low), 4, "Should have 4 low confidence ingredients")
        
        # Step 2: Get confidence summary
        summary = self.analyzer.get_confidence_summary(inventory)
        
        # Verify summary structure
        self.assertEqual(summary["total_detected"], 10)
        self.assertEqual(summary["high_confidence"]["count"], 3)
        self.assertEqual(summary["medium_confidence"]["count"], 3)
        self.assertEqual(summary["low_confidence"]["count"], 4)
        
        # Step 3: Verify actions for each category
        self.assertEqual(
            summary["high_confidence"]["action"],
            "automatically_included",
            "High confidence ingredients should be automatically included"
        )
        self.assertEqual(
            summary["medium_confidence"]["action"],
            "user_confirmation_needed",
            "Medium confidence ingredients should need user confirmation"
        )
        self.assertEqual(
            summary["low_confidence"]["action"],
            "excluded",
            "Low confidence ingredients should be excluded"
        )
        
        # Step 4: Verify specific ingredients in each category
        high_names = [ing["ingredient_name"] for ing in high]
        self.assertIn("brinjal", high_names)
        self.assertIn("rice", high_names)
        self.assertIn("curry_leaves", high_names)
        
        medium_names = [ing["ingredient_name"] for ing in medium]
        self.assertIn("tamarind", medium_names)
        self.assertIn("gongura", medium_names)
        self.assertIn("drumstick", medium_names)
        
        low_names = [ing["ingredient_name"] for ing in low]
        self.assertIn("unknown_vegetable_1", low_names)
        self.assertIn("unknown_spice_1", low_names)
        self.assertIn("unknown_item_1", low_names)
        self.assertIn("unknown_item_2", low_names)
        
        # Print summary for demonstration
        print("\n" + "="*60)
        print("CONFIDENCE FILTERING WORKFLOW DEMONSTRATION")
        print("="*60)
        print(f"\nTotal ingredients detected: {summary['total_detected']}")
        print(f"\nHigh Confidence (>= 0.7) - Automatically Included:")
        print(f"  Count: {summary['high_confidence']['count']}")
        for ing in high:
            print(f"  - {ing['ingredient_name']}: {ing['confidence_score']}")
        
        print(f"\nMedium Confidence (0.5-0.7) - User Confirmation Needed:")
        print(f"  Count: {summary['medium_confidence']['count']}")
        for ing in medium:
            print(f"  - {ing['ingredient_name']}: {ing['confidence_score']}")
        
        print(f"\nLow Confidence (< 0.5) - Excluded:")
        print(f"  Count: {summary['low_confidence']['count']}")
        for ing in low:
            print(f"  - {ing['ingredient_name']}: {ing['confidence_score']}")
        print("="*60 + "\n")
    
    def test_recipe_generation_use_case(self):
        """
        Test use case: Preparing inventory for recipe generation
        
        Only high confidence ingredients should be used for automatic
        recipe generation. Medium confidence ingredients should be
        presented to user for confirmation first.
        """
        inventory = {
            "total_items": 5,
            "ingredients": [
                {"ingredient_name": "brinjal", "confidence_score": 0.92},
                {"ingredient_name": "rice", "confidence_score": 0.85},
                {"ingredient_name": "curry_leaves", "confidence_score": 0.78},
                {"ingredient_name": "tamarind", "confidence_score": 0.62},  # medium
                {"ingredient_name": "unknown", "confidence_score": 0.35}    # low
            ]
        }
        
        high, medium, low = self.analyzer.filter_by_confidence(inventory)
        
        # For recipe generation, use only high confidence ingredients
        recipe_ingredients = high
        self.assertEqual(len(recipe_ingredients), 3)
        
        # Medium confidence ingredients should be presented for confirmation
        confirmation_needed = medium
        self.assertEqual(len(confirmation_needed), 1)
        self.assertEqual(confirmation_needed[0]["ingredient_name"], "tamarind")
        
        # Low confidence ingredients should be excluded
        excluded = low
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0]["ingredient_name"], "unknown")
        
        print("\nRecipe Generation Use Case:")
        print(f"  Ingredients for recipe: {[ing['ingredient_name'] for ing in recipe_ingredients]}")
        print(f"  Need confirmation: {[ing['ingredient_name'] for ing in confirmation_needed]}")
        print(f"  Excluded: {[ing['ingredient_name'] for ing in excluded]}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
