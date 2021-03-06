from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework import status, generics

from kidsbook.serializers import *
from kidsbook.models import *
from kidsbook.permissions import *
from kidsbook.utils import *

User = get_user_model()

## GROUP ##

def get_user_id_from_request_data(request_data: dict):
    uuid = request_data.pop('creator', None)

    if isinstance(uuid, list) and len(uuid) == 1:
        return uuid[0]
    return uuid

def get_groups(request):
    """Return all created groups."""

    try:
        groups = Group.objects.all()
    except Exception as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    serializer = GroupSerializer(groups, many=True)
    return Response({'data': serializer.data})

def create_group(request):
    # Make a copy of data, as it is immutable
    request_data = request.data.dict().copy()

    try:
        creator = request.user
    except Exception as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    serializer = GroupSerializer(data=request_data)

    # Use `id` as `is_valid()` requires an UUID
    request_data['creator'] = creator.id
    if serializer.is_valid():
        try:
            # Re-assign the `User` object
            request_data['creator'] = creator
            new_group = Group.objects.create_group(**request_data)

            # Create a GroupSetting instance
            GroupSettings.objects.create(group=new_group)

            serializer = GroupSerializer(new_group)
            return Response({'data': serializer.data}, status=status.HTTP_202_ACCEPTED)
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated, IsTokenValid, IsSuperUser))
def group(request):
    """Return all groups or create a new group."""

    function_mappings = {
        'GET': get_groups,
        'POST': create_group
    }
    if request.method in function_mappings:
        return function_mappings[request.method](request)
    return Response({'error': 'Bad request.'}, status=status.HTTP_400_BAD_REQUEST)


#################################################################################################################
## GROUP MEMBER ##

def add_member_to_group(user, group):
    group.add_member(user)

    payload = {
        'user': user,
        'group': group,
        'content': 'You have been added to group {}'.format(group.name)
    }
    noti = Notification.objects.create(**payload)
    noti_user = NotificationUser.objects.get(user_id=user.id)
    noti_user.number_of_unseen += 1
    noti_user.save()

    # Push the notification the newly added user
    if UserSetting.objects.get(user_id=user.id).receive_notifications:
        noti_serializer = NotificationSerializer(noti).data
        push_notification(noti_serializer)

def delete_member_from_group(user, group):
    # Remove the link between the user and group
    if user.id == group.creator.id:
        raise ValueError('Cannot delete the Creator from the group.')

    GroupMember.objects.get(user_id=user.id, group_id=group.id).delete()

    payload = {
        'user': user,
        'group': group,
        'content': 'You have been removed from group {}'.format(group.name)
    }
    noti = Notification.objects.create(**payload)
    noti_user = NotificationUser.objects.get(user_id=user.id)
    noti_user.number_of_unseen += 1
    noti_user.save()

    # Push the notification to the deleted user
    if UserSetting.objects.get(user_id=user.id).receive_notifications:
        noti_serializer = NotificationSerializer(noti).data
        push_notification(noti_serializer)

@api_view(['POST', 'DELETE'])
@permission_classes((IsAuthenticated, IsTokenValid, IsSuperUser))
def group_member(request, **kargs):
    """Add new member or remove a member in a group."""

    function_mappings = {
        'POST': add_member_to_group,
        'DELETE': delete_member_from_group
    }

    try:
        group_id = kargs.get('pk', None)
        user_id = kargs.get('user_id', None)
        if group_id and user_id:
            new_member = User.objects.get(id=user_id)
            target_group = Group.objects.get(id=group_id)

            # Both POST and DELETE requests require getting group_id and user_id
            function_mappings[request.method](new_member, target_group)

            return Response({}, status=status.HTTP_202_ACCEPTED)
    except Exception as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'error': 'Bad request.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes((IsAuthenticated, IsTokenValid, IsInGroup))
def get_all_members_in_group(request, **kargs):
    try:
        users = Group.objects.get(id=kargs.get('pk', '')).users
        # Define different Serializer depends on the requester
        if request.user.is_superuser:
            serializer = UserSerializer(users, many=True)
        else:
            serializer = UserPublicSerializer(users, many=True)
        return Response({'data': serializer.data})
    except Exception as exc:
        Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'error': 'Bad request.'}, status=status.HTTP_400_BAD_REQUEST)

#################################################################################################################
## GROUP DETAILS ##

def get_group_detail(request, kargs):
    error = ''
    try:
        group = Group.objects.get(id=kargs.get('pk'))
        serializer = GroupSerializer(group)
        return Response({'data': serializer.data})
    except Exception as exc:
        error = str(exc)
    return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

def update_group_detail(request, kargs):
    try:
        group = Group.objects.get(id=kargs.get('pk'))

        group_fields = set(Group.__dict__.keys())
        if request.user.id != group.creator.id:
            return Response({'error': "Only the creator can modify group's details."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        for attr, value in iter(request.data.dict().items()):
            if attr in group_fields:
                setattr(group, attr, value)
        group.save()
    except Exception as exc:
        Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    serializer = GroupSerializer(group)
    return Response({'data': serializer.data}, status=status.HTTP_202_ACCEPTED)


@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated, IsTokenValid, IsInGroup))
def group_detail(request, **kargs):
    function_mappings = {
        'GET': get_group_detail,
        'POST': update_group_detail
    }

    if request.method in function_mappings:
        return function_mappings[request.method](request, kargs)

    return Response({'error': 'Bad request.'}, status=status.HTTP_400_BAD_REQUEST)


#################################################################################################################
## GROUP MANAGE ##

@api_view(['DELETE'])
@permission_classes((IsAuthenticated, IsTokenValid, IsGroupCreator))
def delete_group(request, **kargs):
    """Delete a group."""
    try:
        group_id = kargs.get('pk', None)

        if group_id:
            target_group = Group.objects.get(id=group_id)

            # The relations in GroupMember table are also auto-removed
            target_group.delete()
            return Response({}, status=status.HTTP_202_ACCEPTED)
    except Exception as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'error': 'Bad request.'}, status=status.HTTP_400_BAD_REQUEST)

#################################################################################################################
## GROUP SETTINGS ##

def get_group_settings(request, kargs):
    try:
        error = ''
        group = GroupSettings.objects.get(group_id=kargs.get('pk'))
        serializer = GroupSettingsSerializer(group)
        return Response({'data': serializer.data})
    except Exception as exc:
        error = str(exc)
    return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

def update_group_settings(request, kargs):
    try:
        group_setting = GroupSettings.objects.get(group_id=kargs.get('pk'))
        group = Group.objects.get(id=kargs.get('pk'))
        group_fields = set(GroupSettings.__dict__.keys())
        group_setting_meta = GroupSettings._meta

        if not request.user.is_superuser:
            return Response({'error': "Only superusers can modify group's settings."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        for attr, value in iter(request.data.dict().items()):
            if attr in group_fields:
                if 'boolean' in str(group_setting_meta.get_field(attr).get_internal_type()).lower():
                    setattr(group_setting, attr, str(value).lower()=='true')
                    continue

                setattr(group_setting, attr, value)
        group_setting.save()
    except Exception as exc:
        Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    serializer = GroupSettingsSerializer(group_setting)
    return Response({'data': serializer.data}, status=status.HTTP_202_ACCEPTED)


@api_view(['GET', 'POST'])
@permission_classes((IsAuthenticated, IsTokenValid, IsInGroup))
def group_settings(request, **kargs):
    function_mappings = {
        'GET': get_group_settings,
        'POST': update_group_settings
    }

    if request.method in function_mappings:
        return function_mappings[request.method](request, kargs)

    return Response({'error': 'Bad request.'}, status=status.HTTP_400_BAD_REQUEST)

#################################################################################################################
## GROUP SURVEYS ##

@api_view(['GET'])
@permission_classes((IsAuthenticated, IsTokenValid, IsInGroup))
def get_all_surveys(request, **kargs):
    group_id = kargs.get('pk', '')
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response(
            {'error': "Requested group doesn't exist."},
            status=status.HTTP_400_BAD_REQUEST
        )

    surveys = Survey.objects.filter(group__id=group.id)
    params = request.query_params
    if 'is_pinned' in params:
        is_pinned = str(params.get('is_pinned', 'false')).lower() == 'true'
        surveys = surveys.filter(is_pinned=is_pinned)

    if 'is_completed' in params:
        is_completed = str(params.get('is_completed', 'false')).lower() == 'true'
        surveys_has_answers = SurveyAnswer.objects.filter(
            survey__in=surveys, user=request.user
        ).values_list('survey', flat=True)

        if is_completed:
            surveys = surveys.filter(id__in=surveys_has_answers)
        else:
            surveys = surveys.exclude(id__in=surveys_has_answers)


    if request.user.role.id <= 1:
        serializer_class = SurveySuperuserSerializer
    else:
        serializer_class = SurveySerializer

    serializer = serializer_class(surveys, many=True)
    return Response({'data': serializer.data})


#################################################################################################################
## GROUP GAMES ##

@api_view(['GET'])
@permission_classes((IsAuthenticated, IsTokenValid, IsInGroup))
def get_all_games(request, **kargs):
    group_id = kargs.get('pk', '')
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response(
            {'error': "Requested group doesn't exist."},
            status=status.HTTP_400_BAD_REQUEST
        )

    games = Game.objects.filter(group__id=group.id)
    if request.user.role.id <= 1:
        serializer_class = GameSuperuserSerializer
    else:
        serializer_class = GameSerializer

    serializer = serializer_class(games, many=True)
    return Response({'data': serializer.data})
