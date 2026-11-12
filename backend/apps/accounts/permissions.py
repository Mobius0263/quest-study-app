from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """
    Allows access only to authenticated users with teacher role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_teacher
        )


class IsStudent(permissions.BasePermission):
    """
    Allows access only to authenticated users with student role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_student
        )


class IsTeacherOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access for any authenticated user, but write permissions only for teachers.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_teacher

