from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


def session_required(view):
    protected_view = login_required(view)

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        response = protected_view(request, *args, **kwargs)
        if (
            not request.user.is_authenticated
            and request.headers.get("HX-Request") == "true"
            and response.status_code == 302
        ):
            return HttpResponse(headers={"HX-Redirect": response["Location"]})
        return response

    return wrapped
