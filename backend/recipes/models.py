from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.crypto import get_random_string

from api.constants import MIN_AMOUNT, MAX_AMOUNT, URL_LINK_LENGTH
from users.models import User


class Tag(models.Model):
    """Модель тегов."""
    name = models.CharField('Название тега', max_length=32, unique=True)
    slug = models.SlugField('Слаг тега', max_length=32, unique=True)

    class Meta:
        ordering = ['name', 'id']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.slug


class Ingredient(models.Model):
    """Модель ингредиентов."""
    name = models.CharField('Название ингредиента', max_length=128)
    measurement_unit = models.CharField('Единица измерения', max_length=64)

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецепта."""
    name = models.CharField('Название', max_length=256)
    text = models.TextField('Описание рецепта')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='recipes', verbose_name='Автор')
    ingredients = models.ManyToManyField(
        'Ingredient', related_name='recipes',
        through='RecipeIngredient',
        verbose_name='Ингредиент'
    )
    image = models.ImageField('Изображение рецепта', upload_to='media/recipes')
    tags = models.ManyToManyField('Tag', related_name='recipes',
                                  verbose_name='Тег')
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='recipes', verbose_name='Автор')
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[
            MinValueValidator(MIN_AMOUNT, message='Минимальное значение 1'),
            MaxValueValidator(MAX_AMOUNT,
                              message='Максимальное значение 32000')
        ]
    )
    pub_date = models.DateTimeField(verbose_name="Дата публикации",
                                    auto_now_add=True)
    url_link = models.CharField(max_length=128, unique=True)

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Сохраняет экземпляр рецепта."""
        if not self.url_link:
            while True:
                self.url_link = get_random_string(length=URL_LINK_LENGTH)
                if not Recipe.objects.filter(url_link=self.url_link).exists():
                    break
        super().save(*args, **kwargs)


class RecipeIngredient(models.Model):
    """Промежуточная модель для связи рецептов и ингредиентов."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='recipe_ingredient_set'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        verbose_name='Ингредиенты',
        related_name='recipe_ingredient_set'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        default=1,
        validators=[
            MinValueValidator(MIN_AMOUNT, message='Минимальное значение 1'),
            MaxValueValidator(MAX_AMOUNT,
                              message='Максимальное значение 32,000')
        ]
    )

    class Meta:
        ordering = ['recipe', 'ingredient']
        verbose_name = 'Ингредиенты рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'

    def __str__(self):
        return f'Ингредиенты {self.ingredient.name} в {self.recipe.name}'


class UserRecipeAbstract(models.Model):
    """Абстрактная модель для связи пользователей и рецептов."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True


class FavoriteRecipe(UserRecipeAbstract):
    """Модель избранных рецептов."""

    class Meta(UserRecipeAbstract.Meta):
        ordering = ['recipe']
        default_related_name = 'favorite_recipes'
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='favorite_recipes',
                violation_error_message='Поля не уникальный.')]

    def __str__(self):
        return f'Рецепты пользователя: {self.user}'


class ShoppingCart(UserRecipeAbstract):
    """Модель корзины покупок."""

    class Meta(UserRecipeAbstract.Meta):
        ordering = ['recipe']
        default_related_name = 'shopping_carts'
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='shopping_cart_recipe',
                violation_error_message='Поля не уникальный.',
            ),
        ]

    def __str__(self):
        return f'Список покупок пользователя: {self.user}'
