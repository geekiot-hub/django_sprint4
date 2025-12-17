from django.urls import path

from . import views

# Пространство имен для приложения blog
app_name = "blog"

# Список URL-маршрутов для приложения blog
urlpatterns = [
    # Главная страница - список всех опубликованных постов
    path("", views.PostListView.as_view(), name="index"),
    # Редактирование профиля пользователя
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="edit_profile"),
    # Страница профиля пользователя с его постами
    path(
        "profile/<slug:username>/",
        views.ProfileListView.as_view(),
        name="profile",
    ),
    # Создание нового поста
    path("posts/create/", views.PostCreateView.as_view(), name="create_post"),
    # Просмотр детальной информации о посте
    path(
        "posts/<int:post_id>/",
        views.PostDetailView.as_view(),
        name="post_detail",
    ),
    # Редактирование поста (только для автора)
    path(
        "posts/<int:post_id>/edit/",
        views.PostUpdateView.as_view(),
        name="edit_post",
    ),
    # Удаление поста (только для автора)
    path(
        "posts/<int:post_id>/delete/",
        views.PostDeleteView.as_view(),
        name="delete_post",
    ),
    # Добавление комментария к посту
    path(
        "posts/<int:post_id>/comment/",
        views.CommentCreateView.as_view(),
        name="add_comment",
    ),
    # Редактирование комментария (только для автора)
    path(
        "posts/<int:post_id>/edit_comment/<int:comment_id>/",
        views.CommentUpdateView.as_view(),
        name="edit_comment",
    ),
    # Удаление комментария (только для автора)
    path(
        "posts/<int:post_id>/delete_comment/<int:comment_id>/",
        views.CommentDeleteView.as_view(),
        name="delete_comment",
    ),
    # Список постов по категории
    path(
        "category/<slug:category_slug>/",
        views.CategoryListlView.as_view(),
        name="category_posts",
    ),
]
