from sqlalchemy import Column, String, Text, JSON, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid


class Rule(Base):
    __tablename__ = "rules_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, nullable=False)
    title = Column(String)
    description = Column(Text)
    condition = Column(JSON, nullable=False)
    expected_outcome = Column(JSON, nullable=False)
    domain = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=False, default="global")
    document_type = Column(String, nullable=False)
    version = Column(String, nullable=False, default="UCP600:2007")
    severity = Column(String, nullable=False, default="fail")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


