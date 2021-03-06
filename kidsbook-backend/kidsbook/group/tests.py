from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from kidsbook.models import Group
from kidsbook.user.views import generate_token

User = get_user_model()
url_prefix = '/api/v1'

class TestGroup(APITestCase):
    def setUp(self):
        self.url = url_prefix + '/group/'
        self.username = "john"
        self.email = "john@snow.com"
        self.password = "you_know_nothing"
        self.user = User.objects.create_superuser(username=self.username, email_address=self.email, password=self.password)
        self.token = self.get_token(self.user)

    def get_token(self, user):
        token = generate_token(user)
        return 'Bearer {0}'.format(token.decode('utf-8'))

    def changes_reflect_in_response(self, request_changes, previous_state, current_state):
        difference = { k : current_state[k] for k in set(current_state) - set(previous_state) }

        for key, prev_val in iter(previous_state.items()):
            # If the un-modified value changes
            if key not in request_changes and current_state.get(key, '') != prev_val:
                return False

            # If the un-modified value doesnt match
            if key in request_changes and str(request_changes[key]).lower() != str(current_state.get(key, '')).lower():
                return False
        return True

    def test_create_group(self):
        response = self.client.post(self.url, {"name": "testing group"}, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(202, response.status_code)

    def test_create_existing_group(self):
        self.client.post(self.url, {"name": "testing group"}, HTTP_AUTHORIZATION=self.token)
        response = self.client.post(self.url, {"name": "testing group"}, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(400, response.status_code)

    def test_create_group_by_non_superuser(self):
        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)
        token = self.get_token(user)

        response = self.client.post(self.url, {"name": "testing group"}, HTTP_AUTHORIZATION=token)
        self.assertEqual(403, response.status_code)

    def test_create_group_without_token(self):
        response = self.client.post(self.url, {"name": "testing group"})
        self.assertEqual(401, response.status_code)

    def test_get_all_groups(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(200, response.status_code)

    def test_get_all_groups_by_non_superuser(self):
        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)
        token = self.get_token(user)

        response = self.client.get(self.url, HTTP_AUTHORIZATION=token)
        self.assertEqual(403, response.status_code)

    def test_get_all_groups_without_token(self):
        response = self.client.get(self.url)
        self.assertEqual(401, response.status_code)

    def test_get_group_detail(self):
        # Create a group
        group_info = {"name": "testing group", 'creator': self.user}
        group = Group.objects.create_group(**group_info)
        response = self.client.get(self.url + str(group.id) + '/', HTTP_AUTHORIZATION=self.token)
        self.assertEqual(200, response.status_code)

    def test_get_group_detail_by_non_member(self):
        group_info = {"name": "testing group", 'creator': self.user}
        group = Group.objects.create_group(**group_info)

        # Create a random user
        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)
        token = self.get_token(user)

        response = self.client.get(self.url + str(group.id) + '/', HTTP_AUTHORIZATION=token)
        self.assertEqual(403, response.status_code)

    def test_get_group_detail_without_token(self):
        group_info = {"name": "testing group", 'creator': self.user}
        group = Group.objects.create_group(**group_info)

        response = self.client.get(self.url + str(group.id) + '/')
        self.assertEqual(401, response.status_code)

    def test_update_group_detail(self):
        # Create a group
        group_info = {"name": "testing group", 'creator': self.user}
        group = Group.objects.create_group(**group_info)
        url = self.url + str(group.id) + '/'
        changes = {
            'name': 'new name',
            'description': 'new descript'
        }

        prev_state = self.client.get(url, HTTP_AUTHORIZATION=self.token).data.get('data', {})
        response = self.client.post(url, data=changes, HTTP_AUTHORIZATION=self.token)

        self.assertEqual(202, response.status_code)
        cur_state = self.client.get(url, HTTP_AUTHORIZATION=self.token).data.get('data', {})
        self.assertTrue(
            self.changes_reflect_in_response(changes, prev_state, cur_state)
        )

    def test_update_group_detail_by_non_creator(self):
        # Create a random user
        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)
        token = self.get_token(user)

        # Create a group
        group_info = {"name": "testing group", 'creator': self.user}
        group = Group.objects.create_group(**group_info)
        url = self.url + str(group.id) + '/'
        changes = {
            'name': 'new name',
            'description': 'new descript'
        }

        response = self.client.post(url, data=changes, HTTP_AUTHORIZATION=token)
        self.assertEqual(403, response.status_code)

    def test_update_group_detail_without_token(self):
        # Create a random user
        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)
        token = self.get_token(user)

        # Create a group
        group_info = {"name": "testing group", 'creator': self.user}
        group = Group.objects.create_group(**group_info)
        url = self.url + str(group.id) + '/'
        changes = {
            'name': 'new name',
            'description': 'new descript'
        }

        response = self.client.post(url, data=changes)
        self.assertEqual(401, response.status_code)


class TestGroupMember(APITestCase):
    def setUp(self):
        # Creator
        self.username = "john"
        self.email = "john@snow.com"
        self.password = "you_know_nothing"
        self.creator = User.objects.create_superuser(username=self.username, email_address=self.email, password=self.password)
        token = generate_token(self.creator)
        self.creator_token = 'Bearer {0}'.format(token.decode('utf-8'))

        # User
        self.username = "hey"
        self.email = "kid@s.sss"
        self.password = "want_some_cookies?"
        self.member = User.objects.create_user(username=self.username, email_address=self.email, password=self.password)
        token = generate_token(self.member)
        self.member_token = 'Bearer {0}'.format(token.decode('utf-8'))

        # Group
        response = self.client.post(url_prefix + '/group/', {"name": "testing group"}, HTTP_AUTHORIZATION=self.creator_token)
        self.group_id = response.data.setdefault('data', {}).get('id', '')

        self.url = "{}/group/{}/".format(url_prefix, self.group_id)

    def test_add_new_group_member(self):
        response = self.client.post("{}user/{}/".format(self.url, str(self.member.id)), HTTP_AUTHORIZATION=self.creator_token)
        self.assertEqual(202, response.status_code)

    def test_add_new_group_member_without_token(self):
        response = self.client.post("{}user/{}/".format(self.url, str(self.member.id)))
        self.assertEqual(401, response.status_code)

    def test_add_new_group_member_by_non_creator(self):
        self.client.post("{}user/{}/".format(self.url,str(self.member.id)), HTTP_AUTHORIZATION=self.creator_token)

        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)

        # Add the user to be a member
        url = "{}user/{}/".format(self.url, str(user.id))
        response = self.client.post(url, HTTP_AUTHORIZATION=self.member_token)

        self.assertEqual(403, response.status_code)

    def test_add_duplicated_group_member(self):
        url = self.url + 'user/' + str(self.member.id) + '/'
        self.client.post(url, HTTP_AUTHORIZATION=self.creator_token)

        response = self.client.post(url, HTTP_AUTHORIZATION=self.creator_token)
        self.assertEqual(400, response.status_code)

    def test_delete_group_member(self):
        url = self.url + 'user/' + str(self.member.id) + '/'
        self.client.post(url, HTTP_AUTHORIZATION=self.creator_token)
        response = self.client.delete(url, HTTP_AUTHORIZATION=self.creator_token)
        self.assertEqual(202, response.status_code)

    def test_delete_group_member_by_non_creator(self):
        self.client.post(self.url + 'user/' + str(self.member.id) + '/', HTTP_AUTHORIZATION=self.creator_token)

        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)

        # Add the user to be a member
        url = self.url + 'user/' + str(user.id) + '/'
        self.client.post(url, HTTP_AUTHORIZATION=self.creator_token)

        response = self.client.delete(url, HTTP_AUTHORIZATION=self.member_token)

        self.assertEqual(403, response.status_code)

    def test_delete_not_joined_group_member(self):
        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)

        url = self.url + 'user/' + str(user.id) + '/'
        response = self.client.delete(url, HTTP_AUTHORIZATION=self.creator_token)
        self.assertEqual(400, response.status_code)

    def test_delete_group_creator(self):
        url = self.url + 'user/' + str(self.creator.id) + '/'
        response = self.client.delete(url, HTTP_AUTHORIZATION=self.creator_token)
        self.assertEqual(400, response.status_code)

    def test_view_all_members_as_member(self):
        self.test_add_new_group_member()
        response = self.client.get("{}users/".format(self.url), HTTP_AUTHORIZATION=self.member_token)
        self.assertEqual(200, response.status_code)
        self.assertTrue(
            all( field not in response.data.get('data', {}) for field in ('email_address', 'realname'))
        )

    def test_view_all_members_as_creator(self):
        response = self.client.get("{}users/".format(self.url), HTTP_AUTHORIZATION=self.creator_token)
        self.assertEqual(200, response.status_code)
        self.assertTrue(
            all( field in user for field in ('email_address', 'realname')
            for user in iter(response.data.get('data', []))
            )
        )

    def test_view_all_members_without_token(self):
        response = self.client.get("{}users/".format(self.url))
        self.assertEqual(401, response.status_code)

    def test_view_all_members_as_non_member(self):
        username = "Another"
        email = "one@b.ites"
        password = "the_dust"
        user = User.objects.create_user(username=username, email_address=email, password=password)
        token = generate_token(user)
        token = 'Bearer {0}'.format(token.decode('utf-8'))

        response = self.client.get("{}users/".format(self.url), HTTP_AUTHORIZATION=token)
        self.assertEqual(403, response.status_code)


class TestGroupManage(APITestCase):
    def setUp(self):
        self.url = url_prefix + '/group/'

        # Creator
        self.username = "john"
        self.email = "john@snow.com"
        self.password = "you_know_nothing"
        self.creator = User.objects.create_superuser(username=self.username, email_address=self.email, password=self.password)
        token = generate_token(self.creator)
        self.creator_token = 'Bearer {0}'.format(token.decode('utf-8'))

    def test_create_group_by_non_superuser(self):
        # Create a non-super user
        username = "Hey"
        email = "kid@do.sss"
        password = "You want some cakes?"
        user = User.objects.create_user(username=username, email_address=email, password=password)
        token = generate_token(user)
        token = 'Bearer {0}'.format(token.decode('utf-8'))

        # Create a group
        response = self.client.post(url_prefix + '/group/', {"name": "testing group"}, HTTP_AUTHORIZATION=token)
        self.assertEqual(403, response.status_code)

    def test_create_group_without_token(self):
        response = self.client.post(url_prefix + '/group/', {"name": "testing group"})
        self.assertEqual(401, response.status_code)

    def test_delete_group(self):
        response = self.client.post(self.url, {"name": "testing group"}, HTTP_AUTHORIZATION=self.creator_token)

        group_id = str(response.data.setdefault('data',{}).get('id', ''))
        url = "{}{}/delete/".format(self.url, group_id)

        response = self.client.delete(url, HTTP_AUTHORIZATION=self.creator_token)
        self.assertEqual(202, response.status_code)

    def test_delete_group_without_token(self):
        response = self.client.post(self.url, {"name": "testing group"}, HTTP_AUTHORIZATION=self.creator_token)

        group_id = str(response.data.setdefault('data',{}).get('id', ''))
        url = "{}{}/delete/".format(self.url, group_id)

        response = self.client.delete(url)
        self.assertEqual(401, response.status_code)

    def test_delete_group_by_non_creator(self):
        # Create a group
        group_response = self.client.post(self.url, {"name": "testing group"}, HTTP_AUTHORIZATION=self.creator_token)
        group_id = str(group_response.data.setdefault('data',{}).get('id', ''))
        url = self.url + group_id + '/'

        # Creat a non-creator
        username = "james"
        email = "james@yong.com"
        password = "testing_ppp"
        user = User.objects.create_user(username=username, email_address=email, password=password)
        token = 'Bearer {0}'.format(generate_token(user).decode('utf-8'))

        response = self.client.delete(url, HTTP_AUTHORIZATION=token)
        self.assertEqual(403, response.status_code)


class TestGroupSettings(APITestCase):
    def setUp(self):
        self.url = url_prefix + '/group/'

        # Creator
        self.username = "john"
        self.email = "john@snow.com"
        self.password = "you_know_nothing"
        self.creator = User.objects.create_superuser(username=self.username, email_address=self.email, password=self.password)
        token = generate_token(self.creator)
        self.creator_token = 'Bearer {0}'.format(token.decode('utf-8'))

        # A member
        username = "sabaton"
        email = "heavy@metal.com"
        password = "you_know_nothing"
        self.member = User.objects.create_user(username=username, email_address=email, password=password)
        token = generate_token(self.member)
        self.member_token = 'Bearer {0}'.format(token.decode('utf-8'))

        # Create a group
        response = self.client.post(url_prefix + '/group/', {"name": "testing group"}, HTTP_AUTHORIZATION=self.creator_token)
        self.group = Group.objects.get(id=response.data.get('data', {}).get('id'))
        self.url = "{}/group/{}/setting/".format(url_prefix, self.group.id)
        self.group.add_member(self.member)

    def changes_reflect_in_response(self, request_changes, previous_state, current_state):
        difference = { k : current_state[k] for k in set(current_state) - set(previous_state) }

        for key, prev_val in iter(previous_state.items()):
            # If the un-modified value changes
            if key not in request_changes and current_state.get(key, '') != prev_val:
                return False

            # If the un-modified value doesnt match
            if key in request_changes and str(request_changes[key]).lower() != str(current_state.get(key, '')).lower():
                return False
        return True

    def test_get_group_settings(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION=self.member_token)
        self.assertEqual(200, response.status_code)


    def test_update_group_settings_by_creator(self):
        prev_state = self.client.get(self.url, HTTP_AUTHORIZATION=self.creator_token).data.get('data', {})

        changes = {
            'is_like_enabled': 'false',
            'is_comment_enabled': True,
            'is_share_enabled': False,
            'enable_reflection': 'true'
        }

        response = self.client.post(self.url, data=changes, HTTP_AUTHORIZATION=self.creator_token)
        self.assertEqual(202, response.status_code)

        cur_state = self.client.get(self.url, HTTP_AUTHORIZATION=self.creator_token).data.get('data', {})
        self.assertTrue(
            self.changes_reflect_in_response(changes, prev_state, cur_state)
        )

    def test_update_group_settings_by_non_creator(self):
        changes = {
            'is_like_enabled': 'false',
            'is_comment_enabled': 'false'
        }
        response = self.client.post(self.url, changes, HTTP_AUTHORIZATION=self.member_token)
        self.assertEqual(405, response.status_code)
