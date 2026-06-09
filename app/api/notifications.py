"""Notification rules API endpoints."""

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_connection

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationRuleCreate(BaseModel):
    name: str
    rule_type: str  # price_drop_percent, price_below, portfolio_drop_percent
    symbol: str = ""
    condition: str = ""
    threshold: float = 0
    email_subject: str = "股票价格提醒"
    email_template: str = ""
    recipients: str = ""
    active: bool = True


class NotificationRuleUpdate(BaseModel):
    name: str | None = None
    rule_type: str | None = None
    symbol: str | None = None
    condition: str | None = None
    threshold: float | None = None
    email_subject: str | None = None
    email_template: str | None = None
    recipients: str | None = None
    active: bool | None = None


@router.get("/rules")
def list_notification_rules():
    """List all notification rules."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM notification_rules ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


@router.post("/rules")
def create_notification_rule(data: NotificationRuleCreate):
    """Create a new notification rule."""
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO notification_rules 
               (name, rule_type, symbol, condition, threshold, 
                email_subject, email_template, recipients, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.name,
                data.rule_type,
                data.symbol,
                data.condition,
                data.threshold,
                data.email_subject,
                data.email_template,
                data.recipients,
                data.active
            )
        )
        conn.commit()
        rule_id = cursor.lastrowid
    
    return {"id": rule_id, "success": True}


@router.get("/rules/{rule_id}")
def get_notification_rule(rule_id: int):
    """Get a notification rule by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM notification_rules WHERE id = ?",
            (rule_id,)
        ).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return dict(row)


@router.put("/rules/{rule_id}")
def update_notification_rule(rule_id: int, data: NotificationRuleUpdate):
    """Update a notification rule."""
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        return {"success": True}
    
    set_clauses = []
    values = []
    for key, value in update_data.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)
    
    values.append(rule_id)
    
    with get_connection() as conn:
        conn.execute(
            f"UPDATE notification_rules SET {', '.join(set_clauses)} WHERE id = ?",
            values
        )
        conn.commit()
    
    return {"success": True}


@router.delete("/rules/{rule_id}")
def delete_notification_rule(rule_id: int):
    """Delete a notification rule."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM notification_rules WHERE id = ?",
            (rule_id,)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"success": True}


@router.post("/rules/{rule_id}/toggle")
def toggle_notification_rule(rule_id: int):
    """Toggle notification rule active status."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT active FROM notification_rules WHERE id = ?",
            (rule_id,)
        ).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        new_active = not row["active"]
        conn.execute(
            "UPDATE notification_rules SET active = ? WHERE id = ?",
            (new_active, rule_id)
        )
        conn.commit()
    
    return {"active": new_active}
