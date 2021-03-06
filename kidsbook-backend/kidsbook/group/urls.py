from django.urls import path
from kidsbook.group import views

urlpatterns = [
    # Return all groups or create a new group
    path('', views.group),

    # Get/update group's details
    path('<uuid:pk>/', views.group_detail),

    # Add new member or remove a member in a group
    path('<uuid:pk>/user/<uuid:user_id>/', views.group_member),

    # View all members public profile of this group
    path('<uuid:pk>/users/', views.get_all_members_in_group),

    # View all surveys in a group
    path('<uuid:pk>/surveys/', views.get_all_surveys),

    # Get all games in a group
    path('<uuid:pk>/games/', views.get_all_games),

    # Delete a group
    path('<uuid:pk>/delete/', views.delete_group),

    # Get / update group settings
    path('<uuid:pk>/setting/', views.group_settings),
]
