from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    aicte_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    institution_type = Column(String(100), default="Engineering & Technology")
    address = Column(Text, nullable=False)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False)
    pin_code = Column(String(10), nullable=True)
    contact_person = Column(String(150), nullable=False)
    official_email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False)
    account_status = Column(String(50), default="ACTIVE", nullable=False)  # PENDING, ACTIVE, SUSPENDED
    registration_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="institution")
