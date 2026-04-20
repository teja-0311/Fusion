"""
RSPC Notifications API Views (UC-015)

5 Endpoints:
1. GET /rspc/api/notifications/ - List notifications (paginated, limit 50)
2. POST /rspc/api/notifications/{id}/mark-read/ - Mark single as read
3. POST /rspc/api/notifications/mark-all-read/ - Mark all as read
4. DELETE /rspc/api/notifications/{id}/ - Delete notification
5. GET /rspc/api/notifications/unread-count/ - Count unread
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q

from ..models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationMarkReadSerializer,
    NotificationFilterSerializer,
    UnreadCountResponseSerializer,
)


class NotificationPagination(PageNumberPagination):
    """Pagination for notifications - max 50 per page"""
    page_size = 50
    page_size_query_param = 'limit'
    max_page_size = 50


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notifications management (UC-015)
    
    Endpoints:
    - GET /notifications/ - List notifications for current user
    - GET /notifications/{id}/ - Get single notification
    - DELETE /notifications/{id}/ - Delete notification
    - POST /notifications/{id}/mark-read/ - Mark single as read
    - POST /notifications/mark-all-read/ - Mark all notifications as read
    - GET /notifications/unread-count/ - Get unread count
    """
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination
    
    def get_queryset(self):
        """Get notifications for current user, newest first"""
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'mark_read':
            return NotificationMarkReadSerializer
        elif self.action == 'filter_notifications':
            return NotificationFilterSerializer
        elif self.action == 'unread_count':
            return UnreadCountResponseSerializer
        return NotificationSerializer
    
    def list(self, request, *args, **kwargs):
        """
        GET /rspc/api/notifications/
        List all notifications for user with optional filtering
        
        Query params:
        - read_status: 'all', 'read', 'unread' (default: all)
        - event_type: specific event type filter (optional)
        - entity_type: specific entity type filter (optional)
        - limit: max 50 per page (default: 50)
        - offset: pagination offset (default: 0)
        """
        queryset = self.get_queryset()
        
        # Filter by read status
        read_status = request.query_params.get('read_status', 'all')
        if read_status == 'read':
            queryset = queryset.filter(is_read=True)
        elif read_status == 'unread':
            queryset = queryset.filter(is_read=False)
        
        # Filter by event type
        event_type = request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Filter by entity type
        entity_type = request.query_params.get('entity_type')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /rspc/api/notifications/{id}/
        Get single notification details
        """
        notification = self.get_object()
        
        # Verify user owns this notification
        if notification.recipient != request.user:
            return Response(
                {'detail': 'You do not have permission to view this notification.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /rspc/api/notifications/{id}/
        Delete a notification
        """
        notification = self.get_object()
        
        # Verify user owns this notification
        if notification.recipient != request.user:
            return Response(
                {'detail': 'You do not have permission to delete this notification.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification.delete()
        return Response(
            {'detail': 'Notification deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        POST /rspc/api/notifications/{id}/mark-read/
        Mark single notification as read
        """
        notification = self.get_object()
        
        # Verify user owns this notification
        if notification.recipient != request.user:
            return Response(
                {'detail': 'You do not have permission to modify this notification.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification.is_read = True
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        POST /rspc/api/notifications/mark-all-read/
        Mark all notifications for user as read
        """
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        )
        
        count = notifications.count()
        notifications.update(is_read=True)
        
        return Response(
            {
                'detail': f'{count} notifications marked as read.',
                'count': count
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        GET /rspc/api/notifications/unread-count/
        Get count of unread notifications
        """
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        total_count = Notification.objects.filter(
            recipient=request.user
        ).count()
        
        return Response(
            {
                'unread_count': unread_count,
                'total_notifications': total_count
            },
            status=status.HTTP_200_OK
        )
