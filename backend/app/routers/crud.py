from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..models import ApiDefinition, Environment, OperationLog, Project, ScenarioCase, TestCase, User
from ..schemas import ApiDefinitionIn, ApiDefinitionUpdate, EnvironmentIn, EnvironmentUpdate, ProjectIn, ProjectUpdate, ScenarioCaseIn, TestCaseIn, TestCaseUpdate
from ..utils import dump_json, fmt_time, parse_json


router = APIRouter(tags=["crud"])


def _base(row):
    data = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    data["create_date"] = fmt_time(row.create_date)
    data["update_date"] = fmt_time(row.update_date)
    return data


def _active_project(project_id: int, db: Session):
    project = db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _environment_out(row: Environment, db: Session):
    project = db.get(Project, row.project_id)
    return {
        **_base(row),
        "project_name": project.name if project and not project.is_deleted else "",
        "headers": parse_json(row.headers_json, {}),
        "variables": parse_json(row.variables_json, {}),
    }


def _api_out(row: ApiDefinition, db: Session):
    project = db.get(Project, row.project_id)
    environment = db.get(Environment, row.environment_id) if row.environment_id else None
    return {
        **_base(row),
        "project_name": project.name if project and not project.is_deleted else "",
        "environment_name": environment.name if environment and not environment.is_deleted else "",
        "headers": parse_json(row.headers_json, {}),
        "query": parse_json(row.query_json, {}),
        "body": parse_json(row.body_json, {}),
    }


def _case_out(row: TestCase, db: Session):
    project = db.get(Project, row.project_id)
    api = db.get(ApiDefinition, row.api_id)
    return {
        **_base(row),
        "project_name": project.name if project and not project.is_deleted else "",
        "api_name": api.name if api else "",
        "request_headers": parse_json(row.request_headers_json, {}),
        "request_query": parse_json(row.request_query_json, {}),
        "request_body": parse_json(row.request_body_json, {}),
        "assertions": parse_json(row.assertions_json, []),
        "extractors": parse_json(row.extractors_json, []),
    }


def _active_environment(environment_id: int, project_id: int, db: Session):
    environment = db.get(Environment, environment_id)
    if not environment or environment.is_deleted:
        raise HTTPException(status_code=404, detail="environment does not exist")
    if environment.project_id != project_id:
        raise HTTPException(status_code=400, detail="environment does not belong to project")
    return environment


def _ensure_environment_name_available(project_id: int, name: str, db: Session, environment_id: int | None = None):
    exists = db.query(Environment).filter(
        Environment.project_id == project_id,
        Environment.name == name,
        Environment.is_deleted.is_(False),
    )
    if environment_id is not None:
        exists = exists.filter(Environment.id != environment_id)
    if exists.first():
        raise HTTPException(status_code=400, detail="环境名称已存在")


def _ensure_api_name_available(project_id: int, name: str, db: Session, api_id: int | None = None):
    exists = db.query(ApiDefinition).filter(
        ApiDefinition.project_id == project_id,
        ApiDefinition.name == name,
    )
    if api_id is not None:
        exists = exists.filter(ApiDefinition.id != api_id)
    if exists.first():
        raise HTTPException(status_code=400, detail="api name already exists")


def _environment_port(protocol: str, port: int | None):
    if port is None:
        return 80 if protocol == "http" else 443
    if port < 1:
        raise HTTPException(status_code=400, detail="端口号必须为正整数")
    return port


@router.get("/projects")
def list_projects(
    name: str = "",
    page: int | None = None,
    page_size: int | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Project).filter(Project.is_deleted.is_(False))
    if name.strip():
        query = query.filter(Project.name.like(f"%{name.strip()}%"))
    if page is None and page_size is None:
        return [_base(row) for row in query.order_by(Project.id.desc()).all()]
    page = max(page or 1, 1)
    page_size = min(max(page_size or 10, 1), 10)
    total = query.count()
    rows = query.order_by(Project.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_base(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/projects")
def create_project(payload: ProjectIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = payload.name.strip()
    description = payload.description.strip()
    if not name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    if not description:
        raise HTTPException(status_code=400, detail="描述不能为空")
    if db.query(Project).filter(Project.name == name, Project.is_deleted.is_(False)).first():
        raise HTTPException(status_code=400, detail="项目名称已存在")
    row = Project(name=name, description=description, status="active", creator_id=user.id, is_deleted=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _base(row)


@router.put("/projects/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Project, project_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    row.name = name
    row.description = payload.description
    db.commit()
    db.refresh(row)
    return _base(row)


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Project, project_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    return _base(row)


@router.get("/environments")
def list_environments(
    project_id: int | None = None,
    name: str = "",
    page: int | None = None,
    page_size: int | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Environment).join(Project, Environment.project_id == Project.id).filter(
        Environment.is_deleted.is_(False),
        Project.is_deleted.is_(False),
    )
    if project_id:
        query = query.filter(Environment.project_id == project_id)
    if name.strip():
        query = query.filter(Environment.name.like(f"%{name.strip()}%"))
    if page is None and page_size is None:
        return [_environment_out(row, db) for row in query.order_by(Environment.id.desc()).all()]
    page = max(page or 1, 1)
    page_size = min(max(page_size or 10, 1), 10)
    total = query.count()
    rows = query.order_by(Environment.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_environment_out(row, db) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/environments")
def create_environment(payload: EnvironmentIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    _active_project(payload.project_id, db)
    name = payload.name.strip()
    base_url = payload.base_url.strip()
    port = _environment_port(payload.protocol, payload.port)
    if not name:
        raise HTTPException(status_code=400, detail="环境名称不能为空")
    if not base_url:
        raise HTTPException(status_code=400, detail="Base URL不能为空")
    _ensure_environment_name_available(payload.project_id, name, db)
    row = Environment(
        project_id=payload.project_id,
        name=name,
        protocol=payload.protocol,
        base_url=base_url,
        port=port,
        headers_json=dump_json(payload.headers),
        variables_json=dump_json(payload.variables),
        is_deleted=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _environment_out(row, db)


@router.put("/environments/{environment_id}")
def update_environment(environment_id: int, payload: EnvironmentUpdate, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Environment, environment_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="环境不存在")
    _active_project(payload.project_id, db)
    name = payload.name.strip()
    base_url = payload.base_url.strip()
    port = _environment_port(payload.protocol, payload.port)
    if not name:
        raise HTTPException(status_code=400, detail="环境名称不能为空")
    if not base_url:
        raise HTTPException(status_code=400, detail="Base URL不能为空")
    _ensure_environment_name_available(payload.project_id, name, db, environment_id=environment_id)
    row.project_id = payload.project_id
    row.name = name
    row.protocol = payload.protocol
    row.base_url = base_url
    row.port = port
    db.commit()
    db.refresh(row)
    return _environment_out(row, db)


@router.delete("/environments/{environment_id}")
def delete_environment(environment_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Environment, environment_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="环境不存在")
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    return _environment_out(row, db)


@router.get("/apis")
def list_apis(
    project_id: int | None = None,
    environment_id: int | None = None,
    name: str = "",
    url: str = "",
    page: int | None = None,
    page_size: int | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ApiDefinition).join(Project, ApiDefinition.project_id == Project.id).filter(
        Project.is_deleted.is_(False),
    )
    if project_id:
        query = query.filter(ApiDefinition.project_id == project_id)
    if environment_id:
        query = query.filter(ApiDefinition.environment_id == environment_id)
    if name.strip():
        query = query.filter(ApiDefinition.name.like(f"%{name.strip()}%"))
    if url.strip():
        query = query.filter(ApiDefinition.path.like(f"%{url.strip()}%"))
    if page is None and page_size is None:
        return [_api_out(row, db) for row in query.order_by(ApiDefinition.id.desc()).all()]
    page = max(page or 1, 1)
    page_size = min(max(page_size or 10, 1), 10)
    total = query.count()
    rows = query.order_by(ApiDefinition.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_api_out(row, db) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/apis")
def create_api(payload: ApiDefinitionIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    _active_project(payload.project_id, db)
    name = payload.name.strip()
    path = payload.path.strip()
    description = payload.description.strip()
    if not name:
        raise HTTPException(status_code=400, detail="api name is required")
    if not path:
        raise HTTPException(status_code=400, detail="api path is required")
    _ensure_api_name_available(payload.project_id, name, db)
    row = ApiDefinition(
        project_id=payload.project_id,
        environment_id=payload.environment_id or 0,
        module="",
        name=name,
        method=payload.method,
        path=path,
        headers_json=dump_json(payload.headers),
        query_json=dump_json(payload.query),
        body_json=dump_json(payload.body),
        description=description,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _api_out(row, db)


@router.put("/apis/{api_id}")
def update_api(api_id: int, payload: ApiDefinitionUpdate, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(ApiDefinition, api_id)
    if not row:
        raise HTTPException(status_code=404, detail="api does not exist")
    _active_project(payload.project_id, db)
    name = payload.name.strip()
    path = payload.path.strip()
    description = payload.description.strip()
    if not name:
        raise HTTPException(status_code=400, detail="api name is required")
    if not path:
        raise HTTPException(status_code=400, detail="api path is required")
    _ensure_api_name_available(payload.project_id, name, db, api_id=api_id)
    row.project_id = payload.project_id
    row.environment_id = payload.environment_id or 0
    row.module = ""
    row.name = name
    row.method = payload.method
    row.path = path
    row.headers_json = dump_json(payload.headers)
    row.query_json = dump_json(payload.query)
    row.body_json = dump_json(payload.body)
    row.description = description
    db.commit()
    db.refresh(row)
    return _api_out(row, db)


@router.delete("/apis/{api_id}")
def delete_api(api_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(ApiDefinition, api_id)
    if not row:
        raise HTTPException(status_code=404, detail="api does not exist")
    if db.query(TestCase).filter(TestCase.api_id == api_id, TestCase.is_deleted.is_(False)).first():
        raise HTTPException(status_code=400, detail="api is referenced by test cases")
    data = _api_out(row, db)
    db.delete(row)
    db.commit()
    return data


@router.get("/cases")
def list_cases(
    project_id: int | None = None,
    api_id: int | None = None,
    page: int | None = None,
    page_size: int | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(TestCase).filter(TestCase.is_deleted.is_(False))
    if project_id:
        query = query.filter(TestCase.project_id == project_id)
    if api_id:
        query = query.filter(TestCase.api_id == api_id)
    ordered = query.order_by(TestCase.create_date.asc(), TestCase.id.asc())
    if page is None and page_size is None:
        return [_case_out(row, db) for row in ordered.all()]
    page = max(page or 1, 1)
    page_size = min(max(page_size or 10, 1), 10)
    total = query.count()
    rows = ordered.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_case_out(row, db) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/cases")
def create_case(payload: TestCaseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _active_project(payload.project_id, db)
    api = db.get(ApiDefinition, payload.api_id)
    if not api:
        raise HTTPException(status_code=404, detail="接口不存在")
    if api.project_id != payload.project_id:
        raise HTTPException(status_code=400, detail="接口不属于所选项目")
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
        is_deleted=False,
        maintainer_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _case_out(row, db)


@router.put("/cases/{case_id}")
def update_case(case_id: int, payload: TestCaseUpdate, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(TestCase, case_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="用例不存在")
    _active_project(payload.project_id, db)
    api = db.get(ApiDefinition, payload.api_id)
    if not api:
        raise HTTPException(status_code=404, detail="接口不存在")
    if api.project_id != payload.project_id:
        raise HTTPException(status_code=400, detail="接口不属于所选项目")
    row.project_id = payload.project_id
    row.api_id = payload.api_id
    row.name = payload.name
    row.request_headers_json = dump_json(payload.request_headers)
    row.request_query_json = dump_json(payload.request_query)
    row.request_body_json = dump_json(payload.request_body)
    row.assertions_json = dump_json([item.model_dump() for item in payload.assertions])
    row.extractors_json = dump_json([item.model_dump() for item in payload.extractors])
    row.tags = payload.tags
    row.priority = payload.priority
    db.commit()
    db.refresh(row)
    return _case_out(row, db)


@router.delete("/cases/{case_id}")
def delete_case(case_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(TestCase, case_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="用例不存在")
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    return _case_out(row, db)


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
