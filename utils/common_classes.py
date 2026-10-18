from dataclasses import dataclass
from enum import Enum
from rest_framework.response import Response


class ProblemJSONContent(Enum):
    INVALID_REQUEST = {'title': "Invalid Request", 'detail': "The request is invalid or malformed."}
    INVALID_CREDENTIALS = {'title': "Invalid Credentials", 'detail': "The provided username or password are invalid."}
    METHOD_NOT_ALLOWED = {'title': "Method Not Allowed", 'detail': "The requested method is not allowed."}
    UNAUTHORIZED = {'title': "Unauthorized", 'detail': "The request requires user authentication."}
    FORBIDDEN = {'title': "Forbidden", 'detail': "The request is forbidden."}
    NOT_FOUND = {'title': "Not Found", 'detail': "The requested resource was not found."}
    NOT_ACCEPTABLE = {'title': "Not Acceptable", 'detail': "The requested resource is not acceptable."}


@dataclass
class ProblemJSONResponse:
    def __init__(self, content: ProblemJSONContent, status: int = 400, instance=None, errors: dict = {}):
        self.title = content.value['title']
        self.status = status
        self.detail = content.value['detail'] if 'detail' in content.value else None
        self.instance = instance
        self.content_type = "application/problem+json"
        self.errors = errors

    def get_response(self):
        result = {
            "type": "about:blank",
            "title": self.title,
            "status": self.status
        }
        if self.detail is not None:
            result["detail"] = self.detail
        if self.instance is not None:
            result["instance"] = self.instance
        if len(self.errors) > 0:
            result["errors"] = self.errors
        return Response(result, status=self.status, content_type=self.content_type)