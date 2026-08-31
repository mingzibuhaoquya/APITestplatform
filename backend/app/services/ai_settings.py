from sqlalchemy.orm import Session

from ..models import AiSetting


def get_active_ai_setting(db: Session) -> AiSetting | None:
    return (
        db.query(AiSetting)
        .filter(
            AiSetting.status == "active",
            AiSetting.provider_url != "",
            AiSetting.model_name != "",
        )
        .order_by(AiSetting.is_default.desc(), AiSetting.id.asc())
        .first()
    )
