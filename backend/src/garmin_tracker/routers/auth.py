from fastapi import APIRouter, HTTPException, status

from garmin_tracker.auth import create_access_token, hash_password, verify_password
from garmin_tracker.deps import CurrentUser
from garmin_tracker.models import User, new_id
from garmin_tracker.schemas import TokenOut, UserCreate, UserLogin, UserOut
from garmin_tracker.store import repo

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token(user: User) -> TokenOut:
    token = create_access_token(user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate) -> TokenOut:
    try:
        user = repo.create_user(
            User(
                id=new_id(),
                email=body.email.lower(),
                password_hash=hash_password(body.password),
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Email already registered") from exc
    return _token(user)


@router.post("/login", response_model=TokenOut)
def login(body: UserLogin) -> TokenOut:
    user = repo.get_user_by_email(body.email.lower())
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
