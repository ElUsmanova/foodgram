from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsStaffOrIsAuthorOrReadOnly(BasePermission):
    """Разрешение, позволяющее доступ к объектам
    только если пользователь является автором."""

    def has_permission(self, request, view):
        """Проверяет, имеет ли пользователь доступ к представлению."""
        return bool(request.method in SAFE_METHODS
                    or request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        """Проверяет, имеет ли пользователь доступ к конкретному объекту."""
        return bool(
            request.method in SAFE_METHODS
            or request.user.is_authenticated
            and (request.user == obj.author or request.user.is_staff)
        )
