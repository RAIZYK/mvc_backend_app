from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.data.base import Base


class EmailOtp(Base):
    __tablename__ = "email_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    code = Column(String(6), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EmailOtp email={self.email} used={self.is_used}>"
