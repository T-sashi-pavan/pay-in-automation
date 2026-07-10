from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from backend.app.database.session import Base


class RuleAuditLog(Base):
    __tablename__ = "rule_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    commission_rule_id = Column(Integer, ForeignKey("commission_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    field = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    edited_by = Column(String(100), nullable=False, default="User")
    edited_at = Column(DateTime, nullable=False, server_default=func.now())
