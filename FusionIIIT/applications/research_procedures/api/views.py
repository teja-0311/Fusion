from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q
import logging

from applications.research_procedures.models import (
    Patent, ResearchGroup, ResearchArea
)
from applications.globals.models import Faculty, HoldsDesignation, Designation
from .serializers import (
    PatentSerializer, ResearchGroupSerializer, ResearchGroupListSerializer,
    ResearchAreaSerializer, ResearchAreaListSerializer
)
from ..role_filters import get_user_roles, get_faculty_by_username

logger = logging.getLogger(__name__)


class PatentViewSet(ModelViewSet):
    queryset = Patent.objects.all()
    serializer_class = PatentSerializer
    permission_classes = [IsAuthenticated]


class ResearchGroupViewSet(ModelViewSet):
    """
    ViewSet for Research Groups (UC-003, BR-RSPC-07)
    
    Permissions:
    - Create: Only faculty (PI-eligible)
    - Read: All authenticated users
    - Update: Group head or RSPC Admin only
    - Delete: RSPC Admin only
    """
    queryset = ResearchGroup.objects.all()
    serializer_class = ResearchGroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ResearchGroupListSerializer
        return ResearchGroupSerializer
    
    def get_queryset(self):
        queryset = ResearchGroup.objects.select_related(
            'discipline', 'head'
        ).prefetch_related('members')
        
        # Filter by discipline if provided
        discipline_id = self.request.query_params.get('discipline_id')
        if discipline_id:
            queryset = queryset.filter(discipline_id=discipline_id)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-created_date')
    
    def create(self, request, *args, **kwargs):
        """Create research group (UC-003)"""
        # Check: Only faculty can create
        faculty = get_faculty_by_username(request.user.username)
        if not faculty:
            return Response(
                {'error': 'Only faculty members can create research groups'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check: Faculty must be PI-eligible
        roles = get_user_roles(request.user.username)
        if not roles['pi']:
            return Response(
                {'error': 'Faculty must be PI-eligible to create research groups (BR-RSPC-07)'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Auto-set head if not provided
        if not serializer.validated_data.get('head'):
            serializer.validated_data['head'] = faculty
        
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update group (head or admin only - BR-RSPC-07)"""
        group = self.get_object()
        faculty = get_faculty_by_username(request.user.username)
        roles = get_user_roles(request.user.username)
        
        # Check authorization: head or admin
        if group.head_id != (faculty.id if faculty else None) and not roles['rspc_admin']:
            return Response(
                {'error': 'Only group head or RSPC Admin can update group (BR-RSPC-07)'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete group (admin only - BR-RSPC-07)"""
        roles = get_user_roles(request.user.username)
        
        if not roles['rspc_admin']:
            return Response(
                {'error': 'Only RSPC Admin can delete research groups (BR-RSPC-07)'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add faculty member to group"""
        group = self.get_object()
        faculty_id = request.data.get('faculty_id')
        
        if not faculty_id:
            return Response(
                {'error': 'faculty_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            faculty = Faculty.objects.get(id=faculty_id)
            group.members.add(faculty)
            return Response(
                {'message': f'Faculty {faculty.user.get_full_name()} added to group'},
                status=status.HTTP_200_OK
            )
        except Faculty.DoesNotExist:
            return Response(
                {'error': 'Faculty not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Remove faculty member from group"""
        group = self.get_object()
        faculty_id = request.data.get('faculty_id')
        
        if not faculty_id:
            return Response(
                {'error': 'faculty_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            faculty = Faculty.objects.get(id=faculty_id)
            group.members.remove(faculty)
            return Response(
                {'message': f'Faculty {faculty.user.get_full_name()} removed from group'},
                status=status.HTTP_200_OK
            )
        except Faculty.DoesNotExist:
            return Response(
                {'error': 'Faculty not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ResearchAreaViewSet(ModelViewSet):
    """
    ViewSet for Research Areas
    
    Permissions:
    - Read: All authenticated users
    - Create/Update/Delete: RSPC Admin only
    """
    queryset = ResearchArea.objects.all()
    serializer_class = ResearchAreaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ResearchAreaListSerializer
        return ResearchAreaSerializer
    
    def get_queryset(self):
        queryset = ResearchArea.objects.select_related(
            'discipline', 'parent_area'
        ).prefetch_related('faculty_experts')
        
        # Filter by discipline if provided
        discipline_id = self.request.query_params.get('discipline_id')
        if discipline_id:
            queryset = queryset.filter(discipline_id=discipline_id)
        
        # Filter by parent area for hierarchy
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            queryset = queryset.filter(parent_area_id=parent_id)
        
        return queryset.order_by('name')
    
    def create(self, request, *args, **kwargs):
        """Create research area (admin only)"""
        roles = get_user_roles(request.user.username)
        
        if not roles['rspc_admin']:
            return Response(
                {'error': 'Only RSPC Admin can create research areas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update research area (admin only)"""
        roles = get_user_roles(request.user.username)
        
        if not roles['rspc_admin']:
            return Response(
                {'error': 'Only RSPC Admin can update research areas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete research area (admin only)"""
        roles = get_user_roles(request.user.username)
        
        if not roles['rspc_admin']:
            return Response(
                {'error': 'Only RSPC Admin can delete research areas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)