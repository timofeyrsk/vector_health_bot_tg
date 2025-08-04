from sqlalchemy import Column, BigInteger, Text, SmallInteger, Numeric, Integer, DateTime, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.connection import Base

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    
    user_id = Column(BigInteger, primary_key=True)  # Telegram User ID
    chat_id = Column(BigInteger)  # Telegram Chat ID for sending messages
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    gender = Column(Text)
    age = Column(SmallInteger)
    height_cm = Column(SmallInteger)
    current_weight_kg = Column(Numeric(5, 2))
    target_weight_kg = Column(Numeric(5, 2))
    goal = Column(Text)  # 'lose_weight', 'maintain_weight', 'gain_weight'
    activity_level = Column(Text)  # 'sedentary', 'moderate', 'active'
    bmr = Column(Numeric(7, 2))  # Basal Metabolic Rate
    tdee = Column(Numeric(7, 2))  # Total Daily Energy Expenditure
    daily_calorie_target = Column(Integer)
    daily_protein_target_g = Column(Numeric(6, 2))
    daily_fat_target_g = Column(Numeric(6, 2))
    daily_carbs_target_g = Column(Numeric(6, 2))
    daily_report_time = Column(Time)  # Time for daily reports in MSK timezone
    terra_user_id = Column(Text)  # Terra API user ID
    
    # Relationships
    food_logs = relationship("FoodLog", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, goal='{self.goal}')>"

