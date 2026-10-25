
from functools import wraps

from utils.common_classes import ProblemJSONContent, ProblemJSONResponse
from accounts.models import AccessToken


def auth_required(view_method):
    """APIView methods decorator when logged in user is required. Returns 401 when not authenticated (no AccessToken)."""

    @wraps(view_method)
    def wrapper(self, request, *args, **kwargs):
        if not isinstance(getattr(request, "auth", None), AccessToken):
            return ProblemJSONResponse(ProblemJSONContent.UNAUTHORIZED, status=401).get_response()
        return view_method(self, request, *args, **kwargs)

    return wrapper