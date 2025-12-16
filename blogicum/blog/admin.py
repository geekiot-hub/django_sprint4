from django.contrib import admin

from blog.models import Category, Location, Post

# Устанавливаем значение по умолчанию для пустых полей в админке
admin.site.empty_value_display = "Не задано"


class PostInline(admin.StackedInline):
    """Вложенный класс для отображения постов в админке категорий и локаций"""

    model = Post  # Модель, которую будем отображать
    extra = 0  # Количество пустых форм для добавления новых записей


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Админ-панель для управления категориями"""

    list_display = (
        "title",  # Отображаемое название
        "is_published",  # Статус публикации
        "slug",  # Уникальный идентификатор для URL
    )
    list_editable = (
        "is_published",  # Возможность редактировать статус прямо из списка
        "slug",  # Возможность редактировать slug прямо из списка
    )
    inlines = (PostInline,)  # Встраиваем форму постов для удобства управления


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Админ-панель для управления местоположениями"""

    list_display = (
        "name",  # Название места
        "is_published",  # Статус публикации
    )
    list_editable = (
        "is_published",  # Возможность редактировать статус прямо из списка
    )
    inlines = (PostInline,)  # Встраиваем форму постов для удобства управления


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Админ-панель для управления публикациями"""

    list_display = (
        "title",  # Заголовок поста
        "is_published",  # Статус публикации
        "pub_date",  # Дата и время публикации
        "author",  # Автор поста
        "category",  # Категория поста
        "location",  # Местоположение поста
    )
    list_editable = (
        "is_published",  # Возможность редактировать статус прямо из списка
    )
