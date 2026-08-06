from sqlalchemy.orm import Session

from ..models import OperationLog, User
from ..utils import dump_json


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


def log_system_exception(
    db: Session,
    method: str,
    path: str,
    error_type: str,
    message: str,
    ip: str = "",
) -> None:
    row = OperationLog(
        operator_id=None,
        module="system",
        action="exception",
        content=dump_json({
            "method": method,
            "path": path,
            "error_type": error_type,
            "message": message,
        })[:2000],
        result="error",
        ip=ip,
    )
    db.add(row)
    db.commit()
