"""Alertas activas."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertOut

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[AlertOut]:
    alerts = db.scalars(
        select(Alert).where(Alert.status == "active").order_by(Alert.started_at.desc())
    ).all()
    return [AlertOut.model_validate(alert) for alert in alerts]
