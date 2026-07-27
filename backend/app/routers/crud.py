from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..models import ApiDefinition, Environment, OperationLog, Project, ScenarioCase, TestCase, User
from ..schemas import ApiDefinitionIn, EnvironmentIn, ProjectIn, ScenarioCaseIn, TestCaseIn
from ..utils import dump_json, fmt_time, parse_json


router = APIRouter(tags=["crud"])


def _base(row):
    data = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    data["create_date"] = fmt_time(row.create_date)
    data["update_date"] = fmt_time(row.update_date)
    return data


@router.get("/projects")
def list_projects(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_base(row) for row in db.query(Project).order_by(Project.id.desc()).all()]


@router.post("/projects")
def create_project(payload: ProjectIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = Project(name=payload.name, description=payload.description, status=payload.status, creator_id=user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _base(row)


@router.get("/environments")
def list_environments(project_id: int | None = None, _: User = Depends(current_user), db: Session = Depends(get_db)):
    query = db.query(Environment)
    if project_id:
        query = query.filter(Environment.project_id == project_id)
    return [{**_base(row), "headers": parse_json(row.headers_json, {}), "variables": parse_json(row.variables_json, {})} for row in query.order_by(Environment.id.desc()).all()]


@router.post("/environments")
def create_environment(payload: EnvironmentIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = Environment(project_id=payload.project_id, name=payload.name, base_url=payload.base_url, headers_json=dump_json(payload.headers), variables_json=dump_json(payload.variables))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _base(row)


@router.get("/apis")
def list_apis(project_id: int | None = None, _: User = Depends(current_user), db: Session = Depends(get_db)):
    query = db.query(ApiDefinition)
    if project_id:
        query = query.filter(ApiDefinition.project_id == project_id)
    return [{**_base(row), "headers": parse_json(row.headers_json, {}), "query": parse_json(row.query_json, {}), "body": parse_json(row.body_json, {})} for row in query.order_by(ApiDefinition.id.desc()).all()]


@router.post("/apis")
def create_api(payload: ApiDefinitionIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = ApiDefinition(
        project_id=payload.project_id,
        module=payload.module,
        name=payload.name,
        method=payload.method,
        path=payload.path,
        headers_json=dump_json(payload.headers),
        query_json=dump_json(payload.query),
        body_json=dump_json(payload.body),
        description=payload.description,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _base(row)


@router.get("/cases")
def list_cases(project_id: int | None = None, _: User = Depends(current_user), db: Session = Depends(get_db)):
    query = db.query(TestCase)
    if project_id:
        query = query.filter(TestCase.project_id == project_id)
    return [{**_base(row), "request_headers": parse_json(row.request_headers_json, {}), "request_query": parse_json(row.request_query_json, {}), "request_body": parse_json(row.request_body_json, {}), "assertions": parse_json(row.assertions_json, []), "extractors": parse_json(row.extractors_json, [])} for row in query.order_by(TestCase.id.desc()).all()]


@router.post("/cases")
def create_case(payload: TestCaseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(ApiDefinition, payload.api_id):
        raise HTTPException(status_code=404, detail="接口不存在")
    row = TestCase(
        project_id=payload.project_id,
        api_id=payload.api_id,
        name=payload.name,
        request_headers_json=dump_json(payload.request_headers),
        request_query_json=dump_json(payload.request_query),
        request_body_json=dump_json(payload.request_body),
        assertions_json=dump_json([item.model_dump() for item in payload.assertions]),
        extractors_json=dump_json([item.model_dump() for item in payload.extractors]),
        tags=payload.tags,
        priority=payload.priority,
        status=payload.status,
        maintainer_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _base(row)


@router.get("/scenarios")
def list_scenarios(project_id: int | None = None, _: User = Depends(current_user), db: Session = Depends(get_db)):
    query = db.query(ScenarioCase)
    if project_id:
        query = query.filter(ScenarioCase.project_id == project_id)
    return [{**_base(row), "steps": parse_json(row.steps_json, [])} for row in query.order_by(ScenarioCase.id.desc()).all()]


@router.post("/scenarios")
def create_scenario(payload: ScenarioCaseIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = ScenarioCase(project_id=payload.project_id, name=payload.name, steps_json=dump_json(payload.steps), failure_strategy=payload.failure_strategy, status=payload.status)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _base(row)


@router.get("/logs")
def list_logs(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_base(row) for row in db.query(OperationLog).order_by(OperationLog.id.desc()).limit(200).all()]

