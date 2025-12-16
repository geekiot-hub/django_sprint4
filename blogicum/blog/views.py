from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth import login, get_user_model
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.db.models import Count
from .models import Post, Category, User, Comment
from .forms import CreationForm, PostForm, CommentForm
from django import forms

POSTS_PER_PAGE = 10


def get_published_posts():
    return Post.objects.select_related("location", "author", "category").filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now(),
    )


def index(request):
    template_name = "blog/index.html"
    post_list = (
        get_published_posts()
        .order_by("-pub_date")
        .annotate(comment_count=Count("comments"))
    )
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"page_obj": page_obj}
    return render(request, template_name, context)


def profile(request, username):
    template = "blog/profile.html"
    author = get_object_or_404(User, username=username)

    post_list = (
        author.post_set.all()
        .order_by("-pub_date")
        .annotate(comment_count=Count("comments"))
    )
    if request.user != author:
        post_list = (
            get_published_posts()
            .filter(author=author)
            .order_by("-pub_date")
            .annotate(comment_count=Count("comments"))
        )
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"page_obj": page_obj, "author": author}
    return render(request, template, context)


def category_posts(request, category_slug):
    template_name = "blog/category.html"
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True
    )
    post_list = (
        get_published_posts()
        .filter(category=category)
        .order_by("-pub_date")
        .annotate(comment_count=Count("comments"))
    )
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"page_obj": page_obj, "category": category}
    return render(request, template_name, context)


def post_detail(request, post_id):
    template_name = "blog/detail.html"
    post = get_object_or_404(
        Post.objects.select_related("location", "author", "category"),
        pk=post_id,
    )
    is_author = request.user == post.author
    if not post.is_published and not is_author:
        from django.http import Http404

        raise Http404("Пост не найден")
    comments = post.comments.select_related("author")
    form = CommentForm()
    context = {"post": post, "comments": comments, "form": form}
    return render(request, template_name, context)


def user_register(request):
    template = "registration/registration_form.html"
    if request.method == "POST":
        form = CreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("blog:profile", args=[user.username]))
    else:
        form = CreationForm()
    return render(request, template, {"form": form})


@login_required
def post_create(request):
    template = "blog/create.html"
    if request.method == "POST":
        form = PostForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("blog:profile", username=post.author.username)
        return render(request, template, {"form": form})

    form = PostForm()
    return render(request, template, {"form": form})


@login_required
def post_edit(request, post_id):
    template = "blog/create.html"
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect("blog:post_detail", post_id=post.pk)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if form.is_valid():
        form.save()
        return redirect("blog:post_detail", post_id=post.pk)
    return render(request, template, {"form": form, "is_edit": True})


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect("blog:post_detail", post_id=post.pk)
    if request.method == "POST":
        post.delete()
        return redirect("blog:profile", username=request.user.username)
    return render(
        request, "blog/detail.html", {"post": post, "confirm_delete": True}
    )


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
    return redirect("blog:post_detail", post_id=post.pk)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    post = get_object_or_404(Post, pk=post_id)
    if request.user != comment.author:
        return redirect("blog:post_detail", post_id=post.pk)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect("blog:post_detail", post_id=post.pk)
    comments = post.comments.select_related("author")
    context = {
        "form": form,
        "post": post,
        "comments": comments,
        "is_edit_comment": comment,
    }
    return render(request, "blog/detail.html", context)


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user != comment.author:
        return redirect("blog:post_detail", post_id=post_id)
    if request.method == "POST":
        comment.delete()
    return redirect("blog:post_detail", post_id=post_id)


class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email")


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = CustomUserChangeForm(
            request.POST, request.FILES or None, instance=request.user
        )
        if form.is_valid():
            form.save()
            return redirect("blog:profile", username=request.user.username)
        # Если форма не валидна, продолжаем отображать форму с ошибками
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, "blog/user.html", {"form": form})
