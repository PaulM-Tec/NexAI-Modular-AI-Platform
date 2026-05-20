# auth_utils.py
import os, jwt, datetime
 
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")  # set in env; default safe for local
 
def issue_token(sub: str, scopes: list[str], minutes: int = 60) -> str:
    """
    Issue a HS256 JWT for local dev.
    """
    payload = {
        "sub": sub,
        "scope": " ".join(scopes),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
 
def verify_scope(authorization_header: str, required_scope: str) -> dict:
    """
    Verify 'Bearer <token>' and scope membership. Returns claims dict if valid.
    Raises ValueError if invalid/missing.
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise ValueError("Missing token")
    token = authorization_header.split(" ", 1)[1]
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        raise ValueError(f"Invalid token: {e}")
    scopes = claims.get("scope", "").split()
    if required_scope not in scopes:
        raise ValueError("Insufficient scope")
    return claims