from typing import Optional, Dict, Any, List
from nicegui import app, ui


def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieves current user dictionary from browser session storage."""
    return app.storage.user.get("user")


def is_authenticated() -> bool:
    """Checks if valid access token exists in user storage."""
    return bool(app.storage.user.get("access_token") and app.storage.user.get("user"))


def login_user(access_token: str, user_data: Dict[str, Any]) -> None:
    """Stores session credentials in browser storage."""
    app.storage.user["access_token"] = access_token
    app.storage.user["user"] = user_data


def logout_user() -> None:
    """Clears stored session tokens and redirects to login."""
    app.storage.user.pop("access_token", None)
    app.storage.user.pop("user", None)
    ui.navigate.to("/login")


def require_auth(allowed_roles: Optional[List[str]] = None) -> bool:
    """Guards route access against unauthenticated or wrong-role users."""
    if not is_authenticated():
        ui.navigate.to("/login")
        return False

    user = get_current_user()
    if not user:
        ui.navigate.to("/login")
        return False

    if allowed_roles and user.get("role") not in allowed_roles:
        # Redirect to appropriate home
        if user.get("role") == "admin":
            ui.navigate.to("/admin")
        else:
            ui.navigate.to("/worker")
        return False

    return True
