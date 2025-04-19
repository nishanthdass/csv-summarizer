from fastapi import HTTPException, Request
from starlette.status import HTTP_401_UNAUTHORIZED


async def verify_session(request: Request):
    """
    Verifies the session and returns the user data.
    """
    if "user_data" not in request.session:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return request.session["user_data"]


async def get_user_id(request: Request) -> str:
    user = request.session.get("user_data")
    if not user or "name" not in user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    return user["name"]   