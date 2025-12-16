from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django.urls import reverse, reverse_lazy
from django.utils import timezone

from .forms import CommentForm, PostForm, ProfileForm
from .models import Category, Comment, Post


class IsAuthorMixin:
    """Примесь для проверки, является ли текущий пользователь автором объекта"""

    def dispatch(self, request, *args, **kwargs):
        # Проверяем, совпадает ли автор объекта с текущим пользователем
        if self.get_object().author.pk != request.user.pk:
            # Если нет - перенаправляем на страницу детального просмотра
            return redirect("blog:post_detail", post_id=self.get_object().pk)

        return super().dispatch(request, *args, **kwargs)


class PostDetailView(DetailView):
    """Представление для детального просмотра поста"""

    post_obj = None
    template_name = "blog/detail.html"
    model = Post
    pk_url_kwarg = "post_id"
    # Используем select_related для оптимизации запросов к связанным моделям
    queryset = Post.objects.select_related("location", "category", "author")

    def dispatch(self, request, *args, **kwargs):
        # Получаем объект поста
        self.post_obj = self.get_object()

        # Проверяем доступ к посту:
        # - пост не опубликован
        # - дата публикации в будущем
        # - категория поста не опубликована
        if (
            not self.post_obj.is_published
            or self.post_obj.pub_date > timezone.now()
            or not self.post_obj.category.is_published
        ):
            # Если текущий пользователь не является автором - ошибка 404
            if self.request.user.pk != self.post_obj.author.pk:
                raise Http404()

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Добавляем в контекст форму для комментариев и сами комментарии
        context = super().get_context_data(**kwargs)
        context["form"] = CommentForm()
        # Выбираем комментарии с информацией об авторах для оптимизации
        context["comments"] = self.post_obj.comments.select_related("author")
        return context


class PostEditMixin(LoginRequiredMixin):
    """Базовый класс для редактирования постов (требует авторизации)"""

    template_name = "blog/create.html"
    model = Post
    form_class = PostForm
    pk_url_kwarg = "post_id"


class PostCreateView(PostEditMixin, CreateView):
    """Представление для создания нового поста"""

    template_name = "blog/create.html"
    model = Post
    form_class = PostForm

    def form_valid(self, form):
        # Устанавливаем текущего пользователя как автора поста
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        # После создания перенаправляем на профиль пользователя
        return reverse_lazy(
            "blog:profile", kwargs={"username": self.request.user.username}
        )


class PostUpdateView(IsAuthorMixin, PostEditMixin, UpdateView):
    """Представление для редактирования поста (только для автора)"""

    def get_success_url(self):
        # После редактирования возвращаемся на страницу поста
        return reverse_lazy(
            "blog:post_detail", kwargs={"post_id": self.get_object().pk}
        )


class PostDeleteView(IsAuthorMixin, PostEditMixin, DeleteView):
    """Представление для удаления поста (только для автора)"""

    def get_context_data(self, **kwargs):
        # Добавляем форму в контекст (возможно, для подтверждения удаления)
        context = super().get_context_data(**kwargs)
        context["form"] = CommentDeleteView(instance=self.get_object())
        return context

    def get_success_url(self):
        # После удаления возвращаемся в профиль пользователя
        return reverse_lazy(
            "blog:profile", kwargs={"username": self.request.user.username}
        )


class PostListMixin(ListView):
    """Базовый класс для списков постов с пагинацией и аннотациями"""

    models = Post
    paginate_by = 10

    def get_queryset(self):
        # Аннотируем queryset количеством комментариев и выбираем связанные объекты
        queryset = (
            Post.objects.annotate(comment_count=Count("comments"))
            .select_related(
                "category",  # Оптимизация запроса к категории
                "location",  # Оптимизация запроса к местоположению
                "author",  # Оптимизация запроса к автору
            )
            .order_by("-pub_date")
        )  # Сортировка по дате публикации (сначала новые)
        return queryset


class PostListView(PostListMixin):
    """Представление для главной страницы - список опубликованных постов"""

    template_name = "blog/index.html"

    def get_queryset(self):
        # Фильтруем только опубликованные посты, которые уже должны быть видны
        queryset = (
            super()
            .get_queryset()
            .filter(
                pub_date__lt=timezone.now(),  # Посты с датой публикации в прошлом
                is_published=True,  # Только опубликованные посты
                category__is_published=True,  # Только посты из опубликованных категорий
            )
        )
        return queryset


class CategoryListlView(PostListView):
    """Представление для списка постов по категории"""

    template_name = "blog/category.html"
    category = None

    def dispatch(self, request, *args, **kwargs):
        # Получаем категорию по slug, проверяя что она опубликована
        self.category = get_object_or_404(
            Category.objects.filter(is_published=True),
            slug=self.kwargs.get("category_slug"),
        )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Фильтруем посты по выбранной категории
        queryset = (
            super().get_queryset().filter(category__slug=self.category.slug)
        )
        return queryset

    def get_context_data(self, **kwargs):
        # Добавляем категорию в контекст для шаблона
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        return context


class ProfileListView(PostListMixin):
    """Представление для профиля пользователя - его посты"""

    username = None
    template_name = "blog/profile.html"

    def dispatch(self, request, *args, **kwargs):
        # Сохраняем имя пользователя из URL
        self.username = self.kwargs.get("username")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        username = self.kwargs.get("username")
        # Получаем посты пользователя
        queryset = super().get_queryset().filter(author__username=username)

        # Если просматривает не сам пользователь - показываем только опубликованные посты
        if self.request.user.username != username:
            queryset.filter(
                pub_date__lt=timezone.now(),
                is_published=True,
                category__is_published=True,
            )
        return queryset

    def get_context_data(self, **kwargs):
        # Добавляем информацию о профиле в контекст
        context = super().get_context_data(**kwargs)
        context["profile"] = get_object_or_404(
            get_user_model(), username=self.kwargs.get("username")
        )
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования профиля пользователя"""

    model = get_user_model()
    form_class = ProfileForm
    template_name = "blog/user.html"

    def get_object(self):
        # Возвращаем текущего пользователя
        return self.request.user

    def get_success_url(self):
        # После сохранения возвращаемся на страницу профиля
        return reverse_lazy(
            "blog:profile", kwargs={"username": self.get_object().username}
        )


class CommentCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания комментария к посту"""

    post_obj = None
    model = Comment
    form_class = CommentForm

    def dispatch(self, request, *args, **kwargs):
        # Получаем пост, к которому будет добавлен комментарий
        self.post_obj = get_object_or_404(Post, pk=kwargs["post_id"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Устанавливаем автора комментария и привязку к посту
        form.instance.author = self.request.user
        form.instance.post = self.post_obj
        return super().form_valid(form)

    def get_success_url(self):
        # После добавления комментария возвращаемся на страницу поста
        return reverse("blog:post_detail", kwargs={"post_id": self.post_obj.pk})


class CommentMixin:
    """Базовый класс для операций с комментариями"""

    pk_url_kwarg = "comment_id"
    template_name = "blog/comment.html"
    model = Comment
    form_class = CommentForm

    def dispatch(self, request, *args, **kwargs):
        # Получаем пост, к которому относится комментарий
        self.post_obj = get_object_or_404(Post, pk=kwargs["post_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        # После операции возвращаемся на страницу поста
        return reverse(
            "blog:post_detail", kwargs={"post_id": self.get_object().post.pk}
        )


class CommentUpdateView(
    LoginRequiredMixin, IsAuthorMixin, CommentMixin, UpdateView
):
    """Представление для редактирования комментария (только для автора)"""

    pass


class CommentDeleteView(
    LoginRequiredMixin, IsAuthorMixin, CommentMixin, DeleteView
):
    """Представление для удаления комментария (только для автора)"""

    pass
