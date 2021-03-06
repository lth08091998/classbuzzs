from __future__ import unicode_literals

import datetime
import uuid

import bcrypt
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin, User)
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


def format_value(value):
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value

class Role(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True)
    name = models.CharField(max_length=100)

# Create your models here.
class UserManager(BaseUserManager):
    # use_in_migrations = True

    def create_roles(self):
        role1 = Role(id=1, name='teacher')
        role2 = Role(id=2, name='student')
        role3 = Role(id=3, name='Virtual student')
        role1.save()
        role2.save()
        role3.save()

    #def _create_user(self, username, email_address, password, role, **extra_fields):
    def _create_user(self, **kargs):
        """
        Creates and saves a User with the given username, email and password.
        """
        self.create_roles()
        if 'username' not in kargs:
            raise ValueError('The given username must be set')

        role = kargs.pop('role', 2)
        password = kargs.pop('password', '12345')

        #email_address = self.normalize_email(kargs['email_address'])
        kargs['email_address'] = self.normalize_email(kargs['email_address'])
        user = self.model(**kargs)

        user.role = Role(id=role)
        user.set_password(password)

        # if(kargs['teacher_id']):
        #     teacher = User.objects.get(id=kargs['teacher_id'])
        #     user.teacher = teacher

        # Don't try-catch this command, as other functions will catch and return the error message
        user.save(using=self._db)

        # Create a notification instance for the user
        NotificationUser.objects.create(user=user)

        # Create a setting instance for the user
        UserSetting.objects.create(user=user)

        return user

    def create_user(self, **kargs):
        if 'is_staff' not in kargs:
            kargs['is_staff'] = False
        if 'is_superuser' not in kargs:
            kargs['is_superuser'] = False

        # kargs.setdefault('is_virtual_user', False)
        return self._create_user(role=2, **kargs)

    def create_virtual_user(self, **kargs):
        if 'is_staff' not in kargs:
            kargs['is_staff'] = True
        if 'is_superuser' not in kargs:
            kargs['is_superuser'] = False

        virtual_user =  self._create_user(role=3, **kargs)

        for group_member in GroupMember.objects.filter(user=kargs['teacher']):
            group_member.group.add_member(virtual_user)
        return virtual_user

    def create_superuser(self, **kargs):
        if 'is_staff' not in kargs:
            kargs['is_staff'] = True
        if 'is_superuser' not in kargs:
            kargs['is_superuser'] = True

        return self._create_user(role=1, **kargs)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sls_id = models.CharField(db_index=True, max_length=65530, default="")
    email_address = models.EmailField(max_length=255, unique=True)
    username = models.CharField(db_index=True, max_length=50, unique=True)
    realname = models.CharField(max_length=50)
    password = models.CharField(max_length=65530)
    gender = models.BooleanField(default=False)
    description = models.TextField(default="")
    date_of_birth = models.DateField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    profile_photo = models.ImageField(null=True)
    login_time = models.PositiveIntegerField(default=0)
    # screen_time = models.PositiveIntegerField(default=0)
    profile_photo = models.ImageField(default="default.png", null=True)

    teacher = models.ForeignKey('self', related_name='teacher_in_chage', on_delete=models.CASCADE, null=True)
    is_active = models.BooleanField(default=True)
    last_active_time = models.PositiveIntegerField(default=0)
    # role_id = models.ForeignKey(Role, related_name='post_owner', on_delete=models.CASCADE, default=0)
    role = models.ForeignKey(Role, related_name='group_owner', on_delete=models.CASCADE)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )

    USERNAME_FIELD = 'email_address'
    EMAIL_FIELD = 'email_address'

    REQUIRED_FIELDS = ["password", "is_active", "realname"]
    objects = UserManager()

class UserSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    receive_notifications = models.BooleanField(default=True)

    REQUIRED_FIELDS = ["user"]

class ScreenTime(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='screen_time', on_delete=models.CASCADE)
    date = models.DateField(_("Date"), default=datetime.date.today)
    total_time = models.FloatField(default=0)

class BlackListedToken(models.Model):
    token = models.CharField(max_length=500)
    user = models.ForeignKey(User, related_name="token_user", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("token", "user")

class GroupManager(models.Manager):
    #def create_group(self, name, creator):
    def create_group(self, **kargs):
        # The arguments passed formats the `value` in <list>, need to extract them
        kargs = {key: format_value(value) for key,value in iter(kargs.items())}

        creator = kargs.pop('creator', None)
        if creator is None:
            raise ValueError('creator is missing.')

        group = self.model(**kargs)
        group.creator = creator
        group.save(using=self._db)
        group.add_member(creator)
        return group

class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    picture = models.ImageField(null=True)
    creator = models.ForeignKey(User, related_name='group_owner', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    users = models.ManyToManyField(User, related_name='user_groups', through='GroupMember')

    REQUIRED_FIELDS = ["name"]
    objects = GroupManager()

    def add_member(self, user):
        group_member = GroupMember(group=self, user=user)
        group_member.save()
        if(user.is_superuser):
            for virtual_user in User.objects.filter(teacher=user, role_id=3):
                group_member = GroupMember(group=self, user=virtual_user)
                group_member.save()


class GroupMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('user', 'group')

class GroupSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    is_like_enabled = models.BooleanField(default=True)
    is_comment_enabled = models.BooleanField(default=True)
    is_share_enabled = models.BooleanField(default=True)
    is_flag_enabled = models.BooleanField(default=True)
    enable_reflection = models.BooleanField(default=False)


class PostManager(models.Manager):
    def create_post(self, **kargs):
        post = self.model(**kargs)
        post.save(using=self._db)
        return post

class Post(models.Model):
    # use_in_migrations = True
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    objects = PostManager()
    creator = models.ForeignKey(User, related_name='user_posts', on_delete=models.CASCADE, default=uuid.uuid4)
    group = models.ForeignKey(Group, related_name='post_group', on_delete=models.CASCADE, default=uuid.uuid4)
    likes = models.ManyToManyField(User, related_name='likes', through='UserLikePost')
    shares = models.ManyToManyField(User, related_name='shares', through='UserSharePost')
    flags = models.ManyToManyField(User, related_name='flags', through='UserFlagPost')
    picture = models.ImageField(null=True)
    link = models.URLField(null=True)
    ogp = models.TextField(null=True)
    is_deleted = models.BooleanField(default=False)
    is_sponsored = models.BooleanField(default=False)
    is_random = models.BooleanField(default=False)
    is_announcement = models.BooleanField(default=False)

    REQUIRED_FIELDS = ["content"]

    objects = PostManager()
    class Meta:
        ordering = ('created_at',)

class UserLikePost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    like_or_dislike = models.BooleanField(default=True)
    class Meta:
        unique_together = ["user", "post"]

class UserSharePost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    class Meta:
        unique_together = ["user", "post"]
# class CommentManager(models.Manager):
#     def create_comment(self, **kargs):
#         comment = self.model(**kargs)
#         comment.save(using=self._db)
#         return comment

class CommentManager(models.Manager):
    def create_comment(self, **kargs):
        comment = self.model(**kargs)
        comment.save(using=self._db)
        return comment

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    post = models.ForeignKey(Post, related_name='comments_post', on_delete=models.CASCADE, default=uuid.uuid4)
    creator = models.ForeignKey(User, related_name='comment_owner', on_delete=models.CASCADE, default=uuid.uuid4)
    likes = models.ManyToManyField(User, related_name='comment_likers', through='UserLikeComment')
    is_deleted = models.BooleanField(default=False)

    REQUIRED_FIELDS = ['post', 'creator', 'content']

    # use_in_migrations = True
    objects = CommentManager()

class UserLikeComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    like_or_dislike = models.BooleanField()
    class Meta:
        unique_together = ["user", "comment"]

class UserFlagPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True)
    status = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "comment", "post"]

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='user_notification', on_delete=models.CASCADE, default=uuid.uuid4)
    group = models.ForeignKey(Group, related_name='group_notification', on_delete=models.CASCADE, default=uuid.uuid4)
    post = models.ForeignKey(Post, related_name='post_notification', on_delete=models.CASCADE, null=True)
    comment =  models.ForeignKey(Comment, related_name='comment_notification', on_delete=models.CASCADE, null=True)
    action_user = models.ForeignKey(User, related_name='action_user_notification', on_delete=models.CASCADE, null=True)
    content = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ["content", "user"]

class NotificationUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='notification_user', on_delete=models.CASCADE, default=uuid.uuid4)
    number_of_unseen = models.PositiveIntegerField(default=0)

class Survey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(User, related_name='survey_creator', on_delete=models.CASCADE, default=uuid.uuid4)
    group = models.ForeignKey(Group, related_name='survey_group', on_delete=models.CASCADE, default=uuid.uuid4)
    title = models.CharField(max_length=2000, default='')
    preface = models.CharField(max_length=2000, default='')
    postface = models.CharField(max_length=2000, default='')
    is_pinned = models.BooleanField(default=False)
    stats = JSONField()
    """
    Stats' Format:
        num_of_responses: Int (default: 0),
        answers: {
            '0': [Int, Int, ...],    # Question 1
            '1': [Int, Int, ...],    # Question 2
            '2': [],     # Question 3 - Empty array = Text input
            ...
        }
    """
    questions_answers = JSONField()
    """
    Questions & Answers' Format:
        [
            {
                question: '',
                options: [...],     # (Optional)
                type: '',           # Front-end typecheck
                required: False,    # If True, backend checks before saving
            },    # Question 1
            ...
        ]
    """

    REQUIRED_FIELDS = ["questions_answers"]

class SurveyAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='survey_user', on_delete=models.CASCADE, default=uuid.uuid4)
    survey = models.ForeignKey(Survey, related_name='user_survey', on_delete=models.CASCADE)
    answers = ArrayField(models.CharField(max_length=2000))

    REQUIRED_FIELDS = ["user", "survey", "answers"]

    class Meta:
        unique_together = ("user", "survey")


### GAME ###

class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(User, related_name='game_creator', on_delete=models.CASCADE, default=uuid.uuid4)
    group = models.ForeignKey(Group, related_name='game_group', on_delete=models.CASCADE, default=uuid.uuid4)
    title = models.CharField(max_length=2000, default='')
    preface = models.CharField(max_length=2000, default='')
    first_scene = models.CharField(max_length=500, default='')
    last_scene = models.CharField(max_length=500, default='')
    stats = JSONField(null=True, blank=True)
    threshold = models.PositiveSmallIntegerField(default=0)
    """
    Stats' Format:
        num_of_responses: Int (default: 0),
        answers: {
            <id_of_scene_1>: [Int, Int, ...],    # Scene 1
            <id_of_scene_2>: [Int, Int, ...],    # Scene 2
            ...
        }
    """

class GameAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='game_answer_user', on_delete=models.CASCADE, default=uuid.uuid4)
    game = models.ForeignKey(Game, related_name='game_answer_game', on_delete=models.CASCADE)
    answers = ArrayField(models.IntegerField())
    ending = models.CharField(max_length=100, default='')

    REQUIRED_FIELDS = ["user", "game", "answers"]

class GameScene(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(Game, related_name='game_scene', on_delete=models.CASCADE)
    is_end = models.BooleanField(default=False)
    choices = JSONField(null=True, blank=True)
    '''
    Choices - a <List> of <Dict>. Each <Dict> has:
    - text(str)
    - tag(str)
    - pathway(ID)
    '''

    dialogue = JSONField()
    '''
    Dialogue: a <List> of <Dict>. Each <Dict> has:
    - name (str): The name of the person who speaks this dialogue. Only applicable if field is_end of its scene is False.
    - speech (str): The name's speech in the dialogue.
    - tag (str): To store the user's answers and his pathway. Only applicable if field is_end of its scene is True.
    '''
