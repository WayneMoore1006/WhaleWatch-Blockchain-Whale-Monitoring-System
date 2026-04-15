"""
Updated Alert Repository
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.models import Alert
from datetime import datetime
from typing import List, Optional


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_alerts(self, limit: int = 50, chain: str = None,
                   severity: str = None, source: str = None,
                   alert_type: str = None, wallet_id: int = None) -> List[Alert]:
        q = self.db.query(Alert).order_by(desc(Alert.created_at))
        if chain:
            q = q.filter(Alert.chain == chain.upper())
        if severity:
            q = q.filter(Alert.severity == severity.lower())
        if source:
            q = q.filter(Alert.source == source.lower())
        if alert_type:
            q = q.filter(Alert.alert_type == alert_type)
        if wallet_id:
            q = q.filter(Alert.wallet_id == wallet_id)
        return q.limit(limit).all()

    def get_by_id(self, alert_id: int) -> Optional[Alert]:
        return self.db.query(Alert).filter_by(alert_id=alert_id).first()

    def mark_read(self, alert_id: int) -> Optional[Alert]:
        alert = self.get_by_id(alert_id)
        if alert:
            alert.status = "read"
            self.db.commit()
        return alert

    def mark_archived(self, alert_id: int) -> Optional[Alert]:
        alert = self.get_by_id(alert_id)
        if alert:
            alert.status = "archived"
            self.db.commit()
        return alert

    def create_alert(self, wallet_id: int, type: str, message: str, severity: str = "medium",
                     chain: str = None, title: str = None, source: str = "watchlist"):
        new_alert = Alert(
            wallet_id=wallet_id,
            alert_type=type,
            title=title or type,
            description=message,
            severity=severity,
            chain=chain,
            source=source,
            status="new",
            created_at=datetime.utcnow()
        )
        self.db.add(new_alert)
        self.db.commit()
        return new_alert
