import math
from typing import Dict, List, Tuple
from datetime import date, datetime, timedelta

class HealthCalculator:
    """Utility class for health-related calculations"""
    
    @staticmethod
    def calculate_bmr(weight_kg: float, height_cm: int, age: int, gender: str) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation
        
        Args:
            weight_kg: Weight in kilograms
            height_cm: Height in centimeters
            age: Age in years
            gender: 'male' or 'female'
            
        Returns:
            BMR in calories per day
        """
        if gender.lower() == 'male':
            bmr = (10 * weight_kg + 6.25 * height_cm - 5 * age + 5)
        else:  # female
            bmr = (10 * weight_kg + 6.25 * height_cm - 5 * age - 161)
        
        return round(bmr, 2)
    
    @staticmethod
    def calculate_tdee(bmr: float, activity_level: str) -> float:
        """
        Calculate Total Daily Energy Expenditure
        
        Args:
            bmr: Basal Metabolic Rate
            activity_level: 'sedentary', 'moderate', or 'active'
            
        Returns:
            TDEE in calories per day
        """
        activity_multipliers = {
            'sedentary': 1.2,    # Little to no exercise
            'moderate': 1.55,    # Light exercise 1-3 days/week
            'active': 1.725      # Moderate exercise 3-5 days/week
        }
        
        multiplier = activity_multipliers.get(activity_level.lower(), 1.2)
        return round(bmr * multiplier, 2)
    
    @staticmethod
    def calculate_daily_calorie_target(tdee: float, goal: str) -> int:
        """
        Calculate daily calorie target based on goal
        
        Args:
            tdee: Total Daily Energy Expenditure
            goal: 'lose_weight', 'maintain_weight', or 'gain_weight'
            
        Returns:
            Daily calorie target
        """
        if goal == 'lose_weight':
            return int(tdee - 500)  # 500 calorie deficit for ~1 lb/week loss
        elif goal == 'gain_weight':
            return int(tdee + 500)  # 500 calorie surplus for ~1 lb/week gain
        else:  # maintain_weight
            return int(tdee)
    
    @staticmethod
    def calculate_macronutrient_targets(daily_calories: int, weight_kg: float) -> Dict[str, float]:
        """
        Calculate macronutrient targets
        
        Args:
            daily_calories: Daily calorie target
            weight_kg: Body weight in kg
            
        Returns:
            Dictionary with protein, fat, and carb targets in grams
        """
        # Protein: 1.6-2.2g per kg body weight (use 1.8g)
        protein_g = round(weight_kg * 1.8, 2)
        
        # Fat: 20-35% of calories (use 25%)
        fat_calories = daily_calories * 0.25
        fat_g = round(fat_calories / 9, 2)  # 9 calories per gram of fat
        
        # Carbs: remaining calories
        protein_calories = protein_g * 4  # 4 calories per gram of protein
        carb_calories = daily_calories - protein_calories - fat_calories
        carb_g = round(carb_calories / 4, 2)  # 4 calories per gram of carbs
        
        return {
            'protein_g': protein_g,
            'fat_g': fat_g,
            'carbs_g': carb_g
        }
    
    @staticmethod
    def calculate_bmi(weight_kg: float, height_cm: int) -> Tuple[float, str]:
        """
        Calculate Body Mass Index and category
        
        Args:
            weight_kg: Weight in kilograms
            height_cm: Height in centimeters
            
        Returns:
            Tuple of (BMI value, BMI category)
        """
        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)
        bmi = round(bmi, 1)
        
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal weight"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"
        
        return bmi, category
    
    @staticmethod
    def calculate_ideal_weight_range(height_cm: int) -> Tuple[float, float]:
        """
        Calculate ideal weight range based on BMI 18.5-24.9
        
        Args:
            height_cm: Height in centimeters
            
        Returns:
            Tuple of (min_weight, max_weight) in kg
        """
        height_m = height_cm / 100
        min_weight = round(18.5 * (height_m ** 2), 1)
        max_weight = round(24.9 * (height_m ** 2), 1)
        
        return min_weight, max_weight
    
    @staticmethod
    def calculate_weight_loss_timeline(current_weight: float, target_weight: float, 
                                     weekly_loss_rate: float = 0.5) -> Dict:
        """
        Calculate weight loss timeline
        
        Args:
            current_weight: Current weight in kg
            target_weight: Target weight in kg
            weekly_loss_rate: Expected weight loss per week in kg
            
        Returns:
            Dictionary with timeline information
        """
        weight_to_lose = current_weight - target_weight
        
        if weight_to_lose <= 0:
            return {
                'weeks_needed': 0,
                'months_needed': 0,
                'target_date': date.today(),
                'weekly_rate': 0
            }
        
        weeks_needed = math.ceil(weight_to_lose / weekly_loss_rate)
        months_needed = round(weeks_needed / 4.33, 1)  # Average weeks per month
        target_date = date.today() + timedelta(weeks=weeks_needed)
        
        return {
            'weeks_needed': weeks_needed,
            'months_needed': months_needed,
            'target_date': target_date,
            'weekly_rate': weekly_loss_rate,
            'total_weight_to_lose': weight_to_lose
        }
    
    @staticmethod
    def calculate_calorie_deficit_needed(weight_to_lose_kg: float, weeks: int) -> int:
        """
        Calculate daily calorie deficit needed to lose weight in given time
        
        Args:
            weight_to_lose_kg: Weight to lose in kg
            weeks: Number of weeks to achieve the loss
            
        Returns:
            Daily calorie deficit needed
        """
        # 1 kg of fat ≈ 7700 calories
        total_calories_to_lose = weight_to_lose_kg * 7700
        daily_deficit = total_calories_to_lose / (weeks * 7)
        
        return int(daily_deficit)
    
    @staticmethod
    def analyze_nutrition_balance(consumed: Dict, targets: Dict) -> Dict:
        """
        Analyze nutrition balance vs targets
        
        Args:
            consumed: Dictionary with consumed nutrients
            targets: Dictionary with target nutrients
            
        Returns:
            Analysis with percentages and recommendations
        """
        analysis = {}
        
        for nutrient in ['calories', 'protein_g', 'fat_g', 'carbs_g']:
            consumed_amount = consumed.get(nutrient, 0)
            target_amount = targets.get(nutrient, 0)
            
            if target_amount > 0:
                percentage = (consumed_amount / target_amount) * 100
                remaining = target_amount - consumed_amount
                
                analysis[nutrient] = {
                    'consumed': consumed_amount,
                    'target': target_amount,
                    'percentage': round(percentage, 1),
                    'remaining': max(0, remaining),
                    'status': 'over' if percentage > 110 else 'under' if percentage < 90 else 'good'
                }
            else:
                analysis[nutrient] = {
                    'consumed': consumed_amount,
                    'target': target_amount,
                    'percentage': 0,
                    'remaining': 0,
                    'status': 'no_target'
                }
        
        return analysis

class MealPlanner:
    """Utility class for meal planning and recommendations"""
    
    @staticmethod
    def suggest_meal_distribution(daily_calories: int) -> Dict[str, int]:
        """
        Suggest calorie distribution across meals
        
        Args:
            daily_calories: Total daily calorie target
            
        Returns:
            Dictionary with suggested calories per meal
        """
        return {
            'breakfast': int(daily_calories * 0.25),  # 25%
            'lunch': int(daily_calories * 0.35),     # 35%
            'dinner': int(daily_calories * 0.30),    # 30%
            'snacks': int(daily_calories * 0.10)     # 10%
        }
    
    @staticmethod
    def calculate_remaining_calories(daily_target: int, consumed_today: int) -> Dict:
        """
        Calculate remaining calories for the day
        
        Args:
            daily_target: Daily calorie target
            consumed_today: Calories consumed so far today
            
        Returns:
            Dictionary with remaining calorie information
        """
        remaining = daily_target - consumed_today
        percentage_consumed = (consumed_today / daily_target) * 100 if daily_target > 0 else 0
        
        return {
            'remaining_calories': max(0, remaining),
            'percentage_consumed': round(percentage_consumed, 1),
            'over_target': remaining < 0,
            'calories_over': abs(remaining) if remaining < 0 else 0
        }
    
    @staticmethod
    def suggest_macro_adjustments(current_macros: Dict, target_macros: Dict) -> List[str]:
        """
        Suggest adjustments to meet macro targets
        
        Args:
            current_macros: Current macro consumption
            target_macros: Target macro values
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        # Protein suggestions
        protein_diff = target_macros.get('protein_g', 0) - current_macros.get('protein_g', 0)
        if protein_diff > 10:
            suggestions.append(f"Add {int(protein_diff)}g more protein (try lean meats, eggs, or protein powder)")
        elif protein_diff < -10:
            suggestions.append("You're over your protein target - consider reducing portion sizes")
        
        # Fat suggestions
        fat_diff = target_macros.get('fat_g', 0) - current_macros.get('fat_g', 0)
        if fat_diff > 5:
            suggestions.append(f"Add {int(fat_diff)}g more healthy fats (nuts, avocado, olive oil)")
        elif fat_diff < -5:
            suggestions.append("Reduce fat intake - choose leaner proteins and cooking methods")
        
        # Carb suggestions
        carb_diff = target_macros.get('carbs_g', 0) - current_macros.get('carbs_g', 0)
        if carb_diff > 20:
            suggestions.append(f"Add {int(carb_diff)}g more carbs (fruits, vegetables, whole grains)")
        elif carb_diff < -20:
            suggestions.append("Reduce carb intake - focus on vegetables over grains")
        
        return suggestions

