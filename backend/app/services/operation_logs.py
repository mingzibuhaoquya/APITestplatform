from sqlalchemy.orm import Session

from ..models import OperationLog, User


def log_operation(
    db: Session,
    operator: User | None,
    module: str,
    action: str,
    content: str = "",
    result: str = "success",
    ip: str = "",
) -> None:
    row = OperationLog(
        operator_id=operator.id if operator else None,
        module=module,
        action=action,
        content=content[:2000],
        result=result,
        ip=ip,
    )
    db.add(row)
    db.commit()
