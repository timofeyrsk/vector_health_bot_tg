from .user_profile import UserProfile
from .food_log import FoodLog
from .activity_log import ActivityLog

# Add relationships to UserProfile
from sqlalchemy.orm import relationship

# Add relationships to UserProfile after all models are imported
UserProfile.food_logs = relationship("FoodLog", back_populates="user")
UserProfile.activity_logs = relationship("ActivityLog", back_populates="user")

__all__ = ['UserProfile', 'FoodLog', 'ActivityLog']

