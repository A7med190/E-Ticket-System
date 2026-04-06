from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAgentOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('agent', 'admin')


class IsOrganizerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('organizer', 'admin')


class IsTicketReporterOrAssigneeOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if request.user.role in ('agent', 'organizer'):
            return obj.assignee == request.user or obj.reporter == request.user
        return obj.reporter == request.user


class IsEventOrganizerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if request.user.role == 'organizer':
            return obj.organizer == request.user
        return request.method in permissions.SAFE_METHODS and obj.is_published


class IsBookingOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if request.user.role == 'organizer':
            return obj.event.organizer == request.user
        return obj.user == request.user


class IsCommentAuthorOrTicketParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if obj.ticket.assignee == request.user:
            return True
        if obj.author == request.user:
            return True
        if obj.ticket.reporter == request.user and not obj.is_internal:
            return True
        return False
