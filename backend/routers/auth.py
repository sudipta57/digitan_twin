from fastapi import APIRouter, HTTPException, Request, Response
from backend.models.schemas import GoogleAuthRequest, UserInfo
from backend.services.auth_service import AuthService
from backend.services.session import set_session_cookie, clear_session_cookie, get_user_id

router = APIRouter(prefix="/auth", tags=["auth"])
auth_svc = AuthService()


@router.post("/google", response_model=UserInfo)
async def google_login(body: GoogleAuthRequest, response: Response):
    try:
        user = auth_svc.verify_google_token(body.token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    set_session_cookie(response, user.user_id)
    return user


@router.get("/me", response_model=UserInfo)
async def get_me(request: Request):
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = auth_svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    return user


@router.post("/logout")
async def logout(response: Response):
    clear_session_cookie(response)
    return {"status": "logged_out"}
