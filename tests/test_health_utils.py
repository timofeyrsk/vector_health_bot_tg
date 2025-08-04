import unittest
from unittest.mock import Mock, patch
from tests.test_config import BaseTestCase
from utils.health_utils import HealthCalculator, MealPlanner

class TestHealthCalculator(BaseTestCase):
    """Test cases for HealthCalculator utility"""
    
    def test_calculate_bmr_male(self):
        """Test BMR calculation for male"""
        bmr = HealthCalculator.calculate_bmr(70, 175, 30, 'male')
        expected = 10 * 70 + 6.25 * 175 - 5 * 30 + 5
        self.assertEqual(bmr, round(expected, 2))
    
    def test_calculate_bmr_female(self):
        """Test BMR calculation for female"""
        bmr = HealthCalculator.calculate_bmr(60, 165, 25, 'female')
        expected = 10 * 60 + 6.25 * 165 - 5 * 25 - 161
        self.assertEqual(bmr, round(expected, 2))
    
    def test_calculate_tdee(self):
        """Test TDEE calculation"""
        bmr = 1500
        tdee_sedentary = HealthCalculator.calculate_tdee(bmr, 'sedentary')
        tdee_moderate = HealthCalculator.calculate_tdee(bmr, 'moderate')
        tdee_active = HealthCalculator.calculate_tdee(bmr, 'active')
        
        self.assertEqual(tdee_sedentary, 1800.0)  # 1500 * 1.2
        self.assertEqual(tdee_moderate, 2325.0)   # 1500 * 1.55
        self.assertEqual(tdee_active, 2587.5)     # 1500 * 1.725
    
    def test_calculate_daily_calorie_target(self):
        """Test daily calorie target calculation"""
        tdee = 2000
        
        lose_target = HealthCalculator.calculate_daily_calorie_target(tdee, 'lose_weight')
        maintain_target = HealthCalculator.calculate_daily_calorie_target(tdee, 'maintain_weight')
        gain_target = HealthCalculator.calculate_daily_calorie_target(tdee, 'gain_weight')
        
        self.assertEqual(lose_target, 1500)    # 2000 - 500
        self.assertEqual(maintain_target, 2000) # 2000
        self.assertEqual(gain_target, 2500)    # 2000 + 500
    
    def test_calculate_macronutrient_targets(self):
        """Test macronutrient target calculation"""
        daily_calories = 2000
        weight_kg = 70
        
        macros = HealthCalculator.calculate_macronutrient_targets(daily_calories, weight_kg)
        
        # Protein: 70 * 1.8 = 126g
        self.assertEqual(macros['protein_g'], 126.0)
        
        # Fat: 2000 * 0.25 / 9 = 55.56g
        self.assertAlmostEqual(macros['fat_g'], 55.56, places=2)
        
        # Carbs should be calculated from remaining calories
        self.assertGreater(macros['carbs_g'], 0)
    
    def test_calculate_bmi(self):
        """Test BMI calculation"""
        bmi, category = HealthCalculator.calculate_bmi(70, 175)
        expected_bmi = 70 / (1.75 ** 2)
        
        self.assertAlmostEqual(bmi, round(expected_bmi, 1))
        self.assertEqual(category, "Normal weight")
    
    def test_calculate_ideal_weight_range(self):
        """Test ideal weight range calculation"""
        min_weight, max_weight = HealthCalculator.calculate_ideal_weight_range(175)
        height_m = 1.75
        
        expected_min = 18.5 * (height_m ** 2)
        expected_max = 24.9 * (height_m ** 2)
        
        self.assertAlmostEqual(min_weight, round(expected_min, 1))
        self.assertAlmostEqual(max_weight, round(expected_max, 1))

class TestMealPlanner(BaseTestCase):
    """Test cases for MealPlanner utility"""
    
    def test_suggest_meal_distribution(self):
        """Test meal distribution suggestion"""
        daily_calories = 2000
        distribution = MealPlanner.suggest_meal_distribution(daily_calories)
        
        self.assertEqual(distribution['breakfast'], 500)  # 25%
        self.assertEqual(distribution['lunch'], 700)      # 35%
        self.assertEqual(distribution['dinner'], 600)     # 30%
        self.assertEqual(distribution['snacks'], 200)     # 10%
        
        # Total should equal daily calories
        total = sum(distribution.values())
        self.assertEqual(total, daily_calories)
    
    def test_calculate_remaining_calories(self):
        """Test remaining calories calculation"""
        daily_target = 2000
        consumed = 1500
        
        result = MealPlanner.calculate_remaining_calories(daily_target, consumed)
        
        self.assertEqual(result['remaining_calories'], 500)
        self.assertEqual(result['percentage_consumed'], 75.0)
        self.assertFalse(result['over_target'])
        self.assertEqual(result['calories_over'], 0)
    
    def test_calculate_remaining_calories_over_target(self):
        """Test remaining calories when over target"""
        daily_target = 2000
        consumed = 2200
        
        result = MealPlanner.calculate_remaining_calories(daily_target, consumed)
        
        self.assertEqual(result['remaining_calories'], 0)
        self.assertEqual(result['percentage_consumed'], 110.0)
        self.assertTrue(result['over_target'])
        self.assertEqual(result['calories_over'], 200)
    
    def test_suggest_macro_adjustments(self):
        """Test macro adjustment suggestions"""
        current_macros = {'protein_g': 80, 'fat_g': 50, 'carbs_g': 200}
        target_macros = {'protein_g': 120, 'fat_g': 60, 'carbs_g': 250}
        
        suggestions = MealPlanner.suggest_macro_adjustments(current_macros, target_macros)
        
        # Should suggest adding protein (40g difference)
        protein_suggestion = next((s for s in suggestions if 'protein' in s.lower()), None)
        self.assertIsNotNone(protein_suggestion)
        
        # Should suggest adding carbs (50g difference)
        carb_suggestion = next((s for s in suggestions if 'carb' in s.lower()), None)
        self.assertIsNotNone(carb_suggestion)

if __name__ == '__main__':
    unittest.main()

