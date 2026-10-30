import json
import logging
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

logger = logging.getLogger("fdrsetu.audit")

class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        action: str,
        entity_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        role: Optional[str] = None,
        entity_id: Optional[str] = None,
        previous_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> AuditLog:
        """
        Appends an immutable audit log entry into the audit_logs table.
        """
        try:
            prev_str = json.dumps(previous_value) if isinstance(previous_value, (dict, list)) else (str(previous_value) if previous_value is not None else None)
            new_str = json.dumps(new_value) if isinstance(new_value, (dict, list)) else (str(new_value) if new_value is not None else None)
            
            log_entry = AuditLog(
                user_id=user_id,
                username=username,
                role=role,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                previous_value=prev_str,
                new_value=new_str,
                details=details,
                ip_address=ip_address,
                correlation_id=correlation_id
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            logger.info(f"AuditLog recorded: action={action} entity={entity_type}:{entity_id} user={username}")
            return log_entry
        except Exception as e:
            logger.error(f"Failed to record audit log: {e}")
            db.rollback()
            return None
