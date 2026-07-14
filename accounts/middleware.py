from django.utils.deprecation import MiddlewareMixin
from .models import ActivityLog


class ActivityLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if request.user.is_authenticated and request.method in ('POST', 'PUT', 'DELETE'):
            path = request.path
            if any(p in path for p in ('/login', '/logout', '/static', '/media')):
                return response
        return response


def log_action(user, action, entity='', entity_id=None, request=None, meta=None):
    ActivityLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        ip_address=request.META.get('REMOTE_ADDR') if request else None,
        meta=meta,
    )
