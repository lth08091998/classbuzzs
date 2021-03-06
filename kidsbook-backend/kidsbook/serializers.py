from rest_framework import serializers, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
import opengraph
import json
from kidsbook.models import *
from kidsbook.utils import censor


User = get_user_model()

# This is for private profile
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'sls_id', 'username', 'email_address', 'is_active', 'profile_photo', 'is_superuser', 'description', "realname", 'user_posts', 'role', 'created_at', 'last_active_time', 'user_groups')
        depth = 1

# This class is for public profile
class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'sls_id', 'is_active', 'is_superuser', 'profile_photo', 'username', 'description', 'user_posts', 'user_groups')
        depth = 1

class UserSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSetting
        fields = ('id', 'user', 'receive_notifications')
        depth = 1

class NestedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email_address', 'is_active', 'profile_photo', 'is_superuser', 'description', "realname", 'role', 'created_at', 'last_active_time')

class PostSerializer(serializers.ModelSerializer):
    creator = NestedUserSerializer(read_only=True)
    content = serializers.SerializerMethodField()

    def get_content(self, obj):
        return censor(obj.content)

    def create(self, data):
        try:
            group = Group.objects.get(id=self.context['view'].kwargs.get("pk"))
        except Exception:
            raise PermissionError('Group Not found')
        current_user = self.context['request'].user
        data = self.context['request'].data
        return Post.objects.create(
            ogp=opengraph.OpenGraph(url=data["link"]).__str__() if 'link' in data else "",
            link=data.get("link", None),
            picture=data.get("picture", None),
            content=data["content"],
            group=group,
            creator=current_user,
            is_sponsored=(data.get("is_sponsored", 'false').strip().lower()=='true'),
            is_announcement=(data.get("is_announcement", 'false').strip().lower()=='true')
        )

    def setup_eager_loading(queryset):
        queryset = queryset.select_related('creator', 'group')
        queryset = queryset.prefetch_related('flags', 'likes', 'group__users')
        return queryset

    class Meta:
        model = Post
        fields = ('id', 'created_at', 'content', 'creator', 'group', 'picture', 'link', 'ogp', 'likes', 'flags', 'shares', 'is_sponsored', 'is_random', 'is_announcement')
        #depth = 1

class NotificationSerializer(serializers.ModelSerializer):
    user = NestedUserSerializer(read_only=True)
    action_user = NestedUserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ('id', 'created_at', 'content', 'user', 'group', 'post', 'action_user')
        #depth = 1

class NotificationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationUser
        fields = ('id', 'user', 'number_of_unseen')
        #depth = 1

class PostSuperuserSerializer(serializers.ModelSerializer):
    creator = NestedUserSerializer(read_only=True)
    filtered_content = serializers.SerializerMethodField()

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.select_related('creator', 'group')
        queryset = queryset.prefetch_related('flags', 'likes', 'group__users')
        return queryset

    def get_filtered_content(self, obj):
        return censor(obj.content)

    def create(self, data):
        try:
            group = Group.objects.get(id=self.context['view'].kwargs.get("pk"))
        except Exception:
            raise PermissionError('Group Not found')
        current_user = self.context['request'].user
        data = self.context['request'].data
        return Post.objects.create(
            ogp=opengraph.OpenGraph(url=data["link"]).__str__() if 'link' in data else "",
            link=data.get("link", None),
            picture=data.get("picture", None),
            content=data["content"],
            group=group,
            creator=current_user,
            is_sponsored=(data.get("is_sponsored", 'false').strip().lower()=='true'),
            is_announcement=(data.get("is_announcement", 'false').strip().lower()=='true')
        )

    class Meta:
        model = Post
        fields = ('id', 'created_at', 'content', 'creator', 'group', 'picture', 'link', 'ogp', 'likes', 'flags', 'filtered_content', 'is_deleted', 'is_sponsored', 'is_random', 'is_announcement')
        #depth = 1


class CommentSerializer(serializers.ModelSerializer):

    creator = NestedUserSerializer(read_only=True)
    content = serializers.SerializerMethodField()

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.select_related('creator', 'post')
        queryset = queryset.prefetch_related('likes', 'post__creator', 'post__group', 'post__likes', 'post__shares', 'post__flags')
        return queryset

    def get_content(self, obj):
        return censor(obj.content)

    class Meta:
        model = Comment
        fields = ('id', 'content', 'created_at', 'post', 'creator' , 'likes')
        #depth = 1

    def create(self, data):
        post = Post.objects.get(id=self.context['view'].kwargs.get("pk"))
        is_comment_enabled = GroupSettings.objects.get(group=post.group).is_comment_enabled
        if is_comment_enabled:
            current_user = self.context['request'].user
            data = self.context['request'].data
            return Comment.objects.create(content=data["content"], post=post, creator=current_user)
        else:
            raise PermissionError('Commenting is disabled for this group')

class CommentSuperuserSerializer(serializers.ModelSerializer):

    creator = NestedUserSerializer(read_only=True)
    filtered_content = serializers.SerializerMethodField()

    def get_filtered_content(self, obj):
        return censor(obj.content)

    def create(self, data):
        post = Post.objects.get(id=self.context['view'].kwargs.get("pk"))
        is_comment_enabled = GroupSettings.objects.get(group=post.group).is_comment_enabled
        if is_comment_enabled:
            current_user = self.context['request'].user
            data = self.context['request'].data
            return Comment.objects.create(content=data["content"], post=post, creator=current_user)
        else:
            raise PermissionError('Commenting is disabled for this group')

    class Meta:
        model = Comment
        fields = ('id', 'content', 'created_at', 'post', 'creator', 'filtered_content', 'is_deleted', 'likes')
        #depth = 1


class PostLikeSerializer(serializers.ModelSerializer):

    post = PostSerializer(required=False)

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.select_related('user', 'post')
        queryset = queryset.prefetch_related('post__creator', 'post__group', 'post__likes', 'post__shares', 'post__flags')
        return queryset

    class Meta:
        model = UserLikePost
        fields = ('id', 'user', 'post', 'like_or_dislike')
        depth = 1

    def create(self, data):
        post = Post.objects.get(id=self.context['view'].kwargs.get("pk"))
        is_like_enabled = GroupSettings.objects.get(group=post.group).is_like_enabled
        if is_like_enabled:
            current_user = self.context['request'].user
            data = self.context['request'].data
            new_post, created = UserLikePost.objects.update_or_create(post=post, user=current_user, defaults={'like_or_dislike': str(data.get("like_or_dislike", 'true')).strip().lower() == 'true'})
            return new_post
        else:
            raise PermissionError('Liking is disabled for this group')

class CommentLikeSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserLikeComment
        fields = ('id', 'user', 'comment', 'like_or_dislike')
        depth = 1

    def create(self, data):
        comment = Comment.objects.get(id=self.context['view'].kwargs.get("pk"))
        is_like_enabled = GroupSettings.objects.get(group=comment.post.group).is_like_enabled
        if is_like_enabled:
            current_user = self.context['request'].user
            data = self.context['request'].data
            new_comment, created = UserLikeComment.objects.update_or_create(comment=comment, user=current_user, defaults={'like_or_dislike': str(data.get("like_or_dislike", 'true')).strip().lower() == 'true'})
            if(data["like_or_dislike"] == False):
                old_comment_like = UserLikeComment.objects.get(comment=comment, user=current_user)
                old_comment_like.delete()
            return new_comment
        else:
            raise PermissionError('Liking is disabled for this group')

class PostFlagSerializer(serializers.ModelSerializer):

    user = NestedUserSerializer(read_only=True)
    post = PostSerializer(required=False)
    comment = CommentSerializer(required=False)

    class Meta:
        model = UserFlagPost
        fields = ('id', 'user', 'post', 'status', 'comment', 'created_at')
        #depth = 1

    def create(self, data):
        post = Post.objects.get(id=self.context['view'].kwargs.get("pk"))
        is_flag_enabled = GroupSettings.objects.get(group=post.group).is_flag_enabled
        if is_flag_enabled:
            current_user = self.context['request'].user
            data = self.context['request'].data
            new_obj, created = UserFlagPost.objects.update_or_create(post=post, user=current_user, comment__isnull=True, defaults={'status': data["status"], 'comment': None})
            return new_obj
        else:
            raise PermissionError('Flagging is disabled for this group')

class CommentFlagSerializer(serializers.ModelSerializer):

    user = NestedUserSerializer(read_only=True)
    comment = CommentSerializer(required=False)
    post = PostSerializer(required=False)

    class Meta:
        model = UserFlagPost
        fields = ('id', 'user', 'post', 'status', 'comment', 'created_at')
        #depth = 1

    def create(self, data):
        comment = Comment.objects.get(id=self.context['view'].kwargs.get("pk"))
        is_flag_enabled = GroupSettings.objects.get(group=comment.post.group).is_flag_enabled
        if is_flag_enabled:
            post = comment.post
            current_user = self.context['request'].user
            data = self.context['request'].data
            new_obj, created = UserFlagPost.objects.update_or_create(post=post, user=current_user, comment=comment, defaults={'status': data["status"]})
            return new_obj
        else:
            raise PermissionError('Flagging is disabled for this group')

class PostShareSerializer(serializers.ModelSerializer):

    post = PostSerializer(required=False)

    class Meta:
        model = UserSharePost
        fields = ('id', 'user', 'post')
        depth = 1

    def create(self, data):
        post = Post.objects.get(id=self.context['view'].kwargs.get("pk"))
        is_share_enabled = GroupSettings.objects.get(group=post.group).is_share_enabled
        if is_share_enabled:
            current_user = self.context['request'].user
            new_post, created = UserSharePost.objects.get_or_create(post=post, user=current_user)
            return new_post
        else:
            raise PermissionError('Sharing is disabled for this group')

class GroupSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupSettings
        fields = ('is_like_enabled', 'is_comment_enabled', 'is_share_enabled', 'is_flag_enabled', 'enable_reflection')

class GroupSerializer(serializers.ModelSerializer):
    group_settings = GroupSettingsSerializer(read_only=True)
    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'picture', 'creator', 'created_at', 'users', 'group_settings')

## Survey ##

class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ('id', 'creator', 'group', 'title', 'preface', 'postface', 'is_pinned', 'questions_answers')

class SurveySuperuserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ('id', 'creator', 'group', 'title', 'preface', 'postface', 'is_pinned', 'stats', 'questions_answers')

class SurveyAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyAnswer
        fields = ('id', 'user', 'survey', 'answers')


## Game ##

class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ('id', 'creator', 'group', 'title', 'preface', 'first_scene', 'last_scene', 'threshold')

class GameSuperuserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ('id', 'creator', 'group', 'title', 'preface', 'stats', 'first_scene', 'last_scene', 'threshold')

class GameAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameAnswer
        fields = ('id', 'user', 'game', 'answers', 'ending')

class GameSceneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameScene
        fields = ('id', 'game', 'is_end', 'choices', 'dialogue')
