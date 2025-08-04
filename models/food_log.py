from sqlalchemy import Column, BigInteger, Text, Integer, Numeric, DateTime, ForeignKey, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from database.connection import Base

class FoodLog(Base):
    __tablename__ = 'food_logs'
    
    log_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(BigInteger, ForeignKey('user_profiles.user_id', ondelete='CASCADE'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text, nullable=False)
    dish_name = Column(Text)
    estimated_ingredients = Column(Text)
    estimated_weight_g = Column(Numeric(7, 2))
    calories = Column(Integer)
    protein_g = Column(Numeric(6, 2))
    fat_g = Column(Numeric(6, 2))
    carbs_g = Column(Numeric(6, 2))
    food_embedding_vector = Column(Text)  # Will store vector as text for now
    log_type = Column(Text, default='manual')  # 'photo', 'text', 'manual'
    photo_url = Column(Text)
    
    # Relationship to user profile
    user = relationship("UserProfile", back_populates="food_logs")
    
    def __repr__(self):
        return f"<FoodLog(log_id={self.log_id}, dish_name='{self.dish_name}', calories={self.calories})>"

