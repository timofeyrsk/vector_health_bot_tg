"""
User state management for multi-step dialogs
"""
import logging
from typing import Dict, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class UserStateManager:
    """Simple in-memory state manager for user dialogs"""
    
    def __init__(self):
        self.user_states = {}  # user_id -> state_data
    
    def set_state(self, user_id: int, state: str, data: Dict = None) -> None:
        """Set user state with optional data"""
        self.user_states[user_id] = {
            'state': state,
            'data': data or {},
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"State set for user {user_id}: {state}, data: {data}")
    
    def get_state(self, user_id: int) -> Optional[Dict]:
        """Get current user state"""
        return self.user_states.get(user_id)
    
    def get_state_name(self, user_id: int) -> Optional[str]:
        """Get current state name for user"""
        state_data = self.get_state(user_id)
        return state_data.get('state') if state_data else None
    
    def get_state_data(self, user_id: int) -> Dict:
        """Get state data for user"""
        state_data = self.get_state(user_id)
        result = state_data.get('data', {}) if state_data else {}
        logger.info(f"State data retrieved for user {user_id}: {result}")
        return result
    
    def clear_state(self, user_id: int) -> None:
        """Clear user state"""
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def update_state_data(self, user_id: int, updates: Dict) -> None:
        """Update state data for user"""
        if user_id in self.user_states:
            self.user_states[user_id]['data'].update(updates)
            self.user_states[user_id]['timestamp'] = datetime.now().isoformat()

# Global state manager instance
state_manager = UserStateManager()

# State constants
class States:
    # Goal change dialog
    GOAL_CHANGE_CURRENT_WEIGHT = "goal_change_current_weight"
    GOAL_CHANGE_TARGET_WEIGHT = "goal_change_target_weight"
    
    # Report time dialog
    REPORT_TIME_INPUT = "report_time_input"
    
    # Food edit dialog
    FOOD_EDIT_SELECT = "food_edit_select"
    FOOD_EDIT_ACTION = "food_edit_action"
    FOOD_EDIT_CALORIES = "food_edit_calories"
    FOOD_EDIT_PROTEIN = "food_edit_protein"
    FOOD_EDIT_FAT = "food_edit_fat"
    FOOD_EDIT_CARBS = "food_edit_carbs"
    FOOD_EDIT_WEIGHT = "food_edit_weight" 