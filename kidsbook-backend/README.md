# Backend API Documentation
[![Build Status](https://travis-ci.org/Ang-YC/kidsbook-backend.svg?branch=master)](https://travis-ci.org/Ang-YC/kidsbook-backend)

# Notes

## 1. URLs
The prefix for all requests is */api/v1/*.
All requests must end with a slash `/`.

Any endpoints having empty description indicates either not implemented or currently being developed.

## 2. Authentication

The format of the authentication token is `Bearer <token>`, where `token` is returned from [/user/login/](#1-user).

## 3. Response
Unsuccessful responses will have a key `error` containing the error message.
Successful responses will have a key `data` containing the requested info.

## 4. Common HTTP status codes

Status Code | Method | Description
--- | --- | --- |
200 | `GET` | For ALL successful `GET` requests.
202 | `POST`, `DELETE` | For ALL successful `POST`, `DELETE` requests.
301 | `GET`, `POST`, `DELETE` | Missing a suffix slash `/`.
400 | `GET`, `POST`, `DELETE` | Caused by an internal error. The error message is returned in `response.data.data`.
401 | `GET`, `POST`, `DELETE` | Caused by missing an authentication token.
403 | `GET`, `POST`, `DELETE` | The sender does not has permissions to perform this action. Handled by permission checks.
404 | `GET`, `POST`, `DELETE` | URL not found.
405 | `GET`, `POST`, `DELETE` | The sender does not has permissions to perform this action. Handled by custom logic.

## 5. Notifications
Notifications are created when:
- A group that the user is in has new posts.
- The post of  the user has 1 more like/dislike.
- The comment of  the user has 1 more like/dislike.
- Another user comments on the user's post.
- Another user comments on a post that the user comments.
- The user is added to a group.
- The user is removed from a group.

# Web API References

Column `Arguments` refers to the keyword arguments in the requests' body.

`*` in column `Arguments` refers the fields of [the return model](./kidsbook/models.py).

However, only the fields defined in the [serializers](./kidsbook/serializers.py) are returned.

## 1. User

```
When a virtual user is created, it will be automatically added to all groups the creator is in.
```

Method | Endpoint | Arguments | Description | Permissions | Return
--- | --- | --- | --- | --- | --- |
`GET` | /user/<user_id>/ | | Get the user's information. | IsAuthenticated | User: *dict*
`GET` | /user/<user_id>/groups/ | | Get all the groups the user is in. | IsAuthenticated | User: *list*
`GET` | /user/<user_id>/posts/ | | Get all posts created by the user. | IsAuthenticated | User: *list*
`POST` | /user/login/ | email_address:*str*, password:*str* | Return an authentication token for the user. | AllowAny | {data: {id: '', token: ''}}
`POST` | /user/login_as_virtual/ | email_address:*str* | Return an authentication for the `virtual` user. | IsAuthenticated, IsSuperUser | {data: {name: '', token: ''}}
`POST` | /user/register/ | * | Create an user using the given arguments. | IsAuthenticated, IsSuperUser | User: *dict*
`GET` | /user/virtual_users/ | | Get all `virtual` users created by the requester. | IsAuthenticated, IsSuperUser | User: *list*
`POST` | /user/logout/ | | Disable the requester's token. | IsAuthenticated | {}
`POST` | /user/update/<user_id/ | * (If update password then need `oldPassword` and `password`) | Update an user using the given arguments. | IsAuthenticated. The requester must be either the creator of the user, the user himself or a superuser in a same group. | User: *dict*
`POST` | /user/record_time/ |'timestamp': The current epoch time | Ping request to record time. | IsAuthenticated | {}


## 2. Users

Method | Endpoint | Arguments | Description | Permissions | Return
--- | --- | --- | --- | --- | --- |
`GET` | /users/ | | Get all superusers, all users in the same group or have no groups or created by the requester. | IsAuthenticated, IsSuperUser | User:*list*
`GET` | /users/non_group/ | | Get all users who are not in any groups. | IsAuthenticated, IsSuperUser | User:*list*

## 3. Setting

**_Note_**: The POST requests for likes/dislikes, creating comments, shares and flags will return a response with HTTP code `405` if the `GroupSettings` for that action is set to `False`.

Method | Endpoint | Arguments | Description | Permissions | Return
--- | --- | --- | --- | --- | --- |
`GET` | /user/setting/ | | Get all settings of the requester. | IsAuthenticated | UserSetting:*dict*
`POST` | /user/setting/ | * | Update the settings of the requester. | IsAuthenticated | UserSetting:*dict*
`GET` | /group/<group_id>/setting/ | | Get the setting of the group. | IsAuthenticated, IsInGroup | GroupSettings:*dict*
`POST` | /group/<group_id>/setting/ | * | Update the setting of the group. | IsAuthenticated, IsInGroup, IsSuperUser | GroupSettings:*dict*


## 3. Notifications
Method | Endpoint | Arguments | Description | Permissions | Return
--- | --- | --- | --- | --- | --- |
`GET` | /notifications/ | | Get at most 50 notifications and the count of unseen ones of the requester. | IsAuthenticated | Notification:*list*
`POST` | /notifications/ | | Reset the count of unseen notifications to 0. | IsAuthenticated | NotificationUser:*dict*

## 4. Post

```
All posts and comments are censored by replacing the each letter with a asterisk `*`.
```

Method | Endpoint | Arguments | Description | Permissions | Return
--- | --- | --- | --- | --- | --- |
`GET` | /group/<group_id>/posts/ | | Get all posts in the group (exclude deleted ones). | IsAuthenticated, IsInGroup | Post: *list*
`GET` | /group/<group_id>/posts/?all=*bool* | | Get all posts in the group (include deleted ones). `bool` is case-insensitive. | IsAuthenticated, IsInGroup, IsSuperUser | Post: *list*
`POST` | /group/<group_id>/posts/ | * | Create a post in the group. | IsAuthenticated, IsInGroup | Post: *dict*
`GET` | group/<group_id>/flagged/ | Get all flagged posts in the group. | IsAuthenticated, IsInGroup, IsSuperUser | Post: *list*
`GET` | /post/<post_id>/ | | Get post's details by ID. | IsAuthenticated, HasAccessToPost | Post: *dict*
`POST` | /post/<post_id>/ | * | Update the post. | IsAuthenticated, HasAccessToPost | Post: *dict*
`DELETE` | /post/<post_id>/ | * | Set the flag `is_deleted` of the post to `True`. | IsAuthenticated, HasAccessToPost | {}
`GET` | /post/<post_id>/likes/ | | Get all likes/dislikes of the post. | IsAuthenticated, HasAccessToPost | UserLikePost: *list*
`POST` | /post/<post_id>/likes/ | like_or_dislike: *bool* | Like/dislike the post. | IsAuthenticated, HasAccessToPost | UserLikePost: *dict*
`GET` | /post/<post_id>/shares/ | | Get all shares of the post. | IsAuthenticated, HasAccessToPost | UserSharePost: *list*
`POST` | /post/<post_id>/shares/ | | User `shares` the post.  | IsAuthenticated, HasAccessToPost | UserSharePost: *dict*
`GET` | /post/<post_id>/comments/ | | Get all comments of the post (exclude deleted ones). | IsAuthenticated, HasAccessToPost | Comment: *list*
`GET` | /post/<post_id>/comments/?all=*bool* | | Get all comments of the post (include deleted ones). `bool` is case-insensitive.. | IsAuthenticated, HasAccessToPost, IsSuperUser | Comment: *list*
`POST` | /post/<post_id>/comments/ | content:*str* | Create a comment for the post. | IsAuthenticated, HasAccessToPost | Comment: *dict*
`GET` | /post/<post_id>/flags/ | | Get all flags of the post. | IsAuthenticated, HasAccessToPost | UserFlagPost: *list*
`POST` | /post/<post_id>/flags/ | status:*str* | Create a flag for the post. | IsAuthenticated, HasAccessToPost | UserFlagPost: *dict*
`GET` | /comment/<comment_id>/ | | Get comment's details by ID. | IsAuthenticated, HasAccessToComment | Comment: *dict*
`POST` | /comment/<comment_id>/ | content:*str* | Update the comment. | IsAuthenticated, HasAccessToComment | Comment: *dict*
`DELETE` | /comment/<comment_id>/ | | Set the flag `is_deleted` of the comment to `True`. | IsAuthenticated, HasAccessToComment | {}
`GET` | /comment/<comment_id>/likes/ | | Get the likes/dislikes of the comment. | IsAuthenticated, HasAccessToComment | UserLikeComment: *list*
`POST` | /comment/<comment_id>/likes/ | like_or_dislike:*bool* | User likes/dislikes a comment. | IsAuthenticated, HasAccessToComment | UserLikeComment: *dict*
`GET` | /comment/<comment_id>/flags/ | | Get the flags of the comment. | IsAuthenticated, HasAccessToComment | UserFlagPost: *list*
`POST` | /comment/<comment_id>/flags/ | status:*str* | Create a flag for the comment. | IsAuthenticated, HasAccessToComment | UserFlagPost: *dict*

## 6. Group

Method | Endpoint | Arguments | Description | Permissions | Return
--- | --- | --- | --- | --- | --- |
`GET` | /group/ | | Get all groups. | IsAuthenticated, IsSuperUser | Group: *list*
`POST` | /group/ | * | Create a group. | IsAuthenticated, IsSuperUser | Group: *dict*
`GET` | /group/<group_id>/ | | Get the group's details. | IsAuthenticated, IsInGroup | Group: *dict*
`POST` | /group/<group_id>/ | * | Update the group's details. | IsAuthenticated, IsInGroup, IsGroupCreator | Group: *dict*
`GET` | /group/<group_id>/users/ | | Get all members in the group. | IsAuthenticated, IsInGroup | User:*list*
`POST` | /group/<group_id>/user/<user_id>/ | | Add the user to the group. | IsAuthenticated, IsGroupCreator | {}
`DELETE` | /group/<group_id>/user/<user_id>/ | | Remove the user to the group. | IsAuthenticated, IsGroupCreator | {}
`DELETE` | /group/<group_id>/delete/ | | Remove the group. | IsAuthenticated, IsGroupCreator| {}
`GET` | /group/<group_id>/surveys/ | | Get all surveys in the group. | IsAuthenticated, IsInGroup | Survey:*list*

## 7. Batch
An URL argument `file_name` is required by [FileUploadParser](https://www.django-rest-framework.org/api-guide/parsers/#fileuploadparser).

A header row is required for the `.csv` files. The headers allowed include:
```
username,email_address,password,realname,gender,description
```
 Empty `gender` will default to 0.

An example `.csv` file:
```
username,email_address,password,realname,gender
chris,chris@email.com,password_for_kris,Christiana Messi,0
james,james@email.com,password_for_kris,Christiana Messi,1
ama,ama@email.com,ama_pwd,Ama Johnson,1
```

Method | Endpoint | Arguments | Description | Permissions | Return
--- | --- | --- | --- | --- | --- |
`POST` | /batch/create/user/<file_name>/ | file | Create users from the uploaded file. The UUIDs of created users are returned. | IsAuthenticated, IsSuperUser | {data: {created_users: []}}

## 8. Survey

The answers sent to server can be either `Int`, `String`. However, the answers sent **FROM** server are always `String` due to Django's internal process.

A survey having responses cannot be updated. All the responses should be manually deleted or create a new survey.

### Request: Format of Survey's stats:
```
{
    num_of_responses: Int (default: 0),
    answers: {
        '0': [Int, Int, ...],    # Question 1
        '1': [Int, Int, ...],    # Question 2
        '2': [],     # Question 3 - Empty array = Text input
        ...
    }
}
```

### Request: Format of Survey's questions:
```
[
    {
        question: '',
        options: [...],     # (Optional)
        type: '',           # Front-end typecheck
        required: False,    # If True, backend checks before saving
    },    # Question 1
    ...
]
```

### Response: Format of Survey's answers:
**IMPORTANT**: All values in list of answers are converted to `String` by Django.

```
[
    '0',                # Used to be Int
    '3',                # Used to be Int
    '[1, 2]',           # Used to be Array
    'This is a text.',  # Text
    ...
]
```

Method | Endpoint | Arguments | Description | Permissions | Return
--- | --- | --- | --- | --- | --- |
`GET` | /surveys/ | | Get all surveys from all groups of requester. | IsAuthenticated | Survey: *list*
`GET` | /survey/ | | Get all surveys of superuser. | IsAuthenticated, IsSuperUser | Survey: *list*
`POST` | /survey/ | questions_answers, group | Create a new survey. | IsAuthenticated, IsSuperUser | Survey: *dict*
`GET` | /survey/<survey_id> | | Get a new survey's questions and stats. | IsAuthenticated | Survey: *dict*
`POST` | /survey/<survey_id> | questions_answers | Update a new survey's questions. | IsAuthenticated, IsSuperUser | Survey: *dict*
`DELETE` | /survey/<survey_id> | | Delete a new survey. | IsAuthenticated, IsSuperUser | {}
`GET` | /survey/<survey_id>/user/<user_id>/ | | Get the survey's answers of an user. | IsAuthenticated, IsSuperUser or IsOwner | SurveyAnswer: *dict*
`POST` | /survey/<survey_id>/user/<user_id>/ | answers | Update the survey's questions. | IsAuthenticated, IsSuperUser or IsOwner | SurveyAnswer: *dict*
`DELETE` | /survey/<survey_id>/user/<user_id>/ | | Delete a survey's response. | IsAuthenticated, IsSuperUser | {}
