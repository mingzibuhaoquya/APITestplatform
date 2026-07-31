from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..schemas import MockUserLoginIn


router = APIRouter(prefix="/mock", tags=["mock"])


@router.post("/userLogin")
def user_login(payload: MockUserLoginIn):
    if payload.username == "zmn" and payload.password == "123456":
        return {"result": "success"}
    return JSONResponse(status_code=401, content={"result": "failed"})
