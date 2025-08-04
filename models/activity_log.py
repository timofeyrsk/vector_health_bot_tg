from sqlalchemy import Column, BigInteger, Integer, Date, DateTime, ForeignKey, UniqueConstraint, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from database.connection import Base

class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    
    log_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(BigInteger, ForeignKey('user_profiles.user_id', ondelete='CASCADE'))
    date = Column(Date, nullable=False)
    active_calories = Column(Integer)
    steps = Column(Integer)
    sleep_duration_min = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to user profile
    user = relationship("UserProfile", back_populates="activity_logs")
    
    # Unique constraint for one record per user per day
    __table_args__ = (UniqueConstraint('user_id', 'date', name='unique_user_date'),)
    
    def __repr__(self):
        return f"<ActivityLog(user_id={self.user_id}, date={self.date}, steps={self.steps})>"

