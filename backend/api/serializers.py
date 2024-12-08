from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from drf_extra_fields.fields import Base64ImageField

from .constants import MIN_AMOUNT, MAX_AMOUNT
from users.models import User, Follow
from recipes.models import (
    Recipe,
    Tag,
    RecipeIngredient,
    Ingredient,
    FavoriteRecipe,
    ShoppingCart,
)


class UserSerializer(serializers.ModelSerializer):
    """Серилизатор для модели пользователя."""
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = '__all__'

    def get_is_subscribed(self, obj):
        """Проверка, подписан ли текущий пользователь
        на данного пользователя."""
        request = self.context['request']
        user = request.user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, following=obj).exists()


class AvatarSerializer(serializers.ModelSerializer):
    """Серилизатор для аватарки."""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    """Серилизатор для тегов."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Серилизатор ингредиентов."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления или обновления ингредиентов в рецепте."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), required=True)
    amount = serializers.IntegerField(min_value=MIN_AMOUNT,
                                      max_value=MAX_AMOUNT)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Серилизатор для отображения ингредиентов."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = '__all__'


class RecipeReadSerializer(serializers.ModelSerializer):
    """Серилизатор для чтения информации о рецептов."""

    tags = TagSerializer(many=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipe_ingredient_set')
    is_favorited = serializers.SerializerMethodField(
        read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(
        read_only=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_is_favorited(self, obj):
        """Проверка, добавлен ли рецепт в избранное текущим пользователем."""
        request = self.context['request']
        user = request.user
        if user.is_anonymous:
            return False
        return user.favorite_recipes.filter(recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверка, находится ли рецепт в корзине текущего пользователя."""
        request = self.context['request']
        user = request.user
        if user.is_anonymous:
            return False
        return user.shopping_carts.filter(recipe=obj).exists()


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Серилизатор добавления рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all())
    author = UserSerializer(read_only=True)
    ingredients = IngredientCreateUpdateSerializer(
        many=True,
    )
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'name', 'image', 'text', 'cooking_time')
        read_only_fields = ('author',)

    def validate(self, attrs):
        """Валидация данных перед созданием или обновлением рецепта."""
        tags = attrs.get('tags')
        ingredients = attrs.get('ingredients')
        cooking_time = attrs.get('cooking_time')

        if not ingredients:
            raise serializers.ValidationError({
                'ingredients': 'Поле отсутствует'
            })
        if not tags:
            raise serializers.ValidationError({'tags': 'Поле отсутствует'})
        if cooking_time is None or not (
                MIN_AMOUNT <= cooking_time <= MAX_AMOUNT):
            error_message = (
                f'Должно быть от {MIN_AMOUNT} до {MAX_AMOUNT} минут.'
            )
            raise serializers.ValidationError({'cooking_time': error_message})
        return attrs

    def create(self, validated_data):
        """Создание нового рецепта."""
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(
            author=self.context['request'].user, **validated_data)
        recipe.tags.set(tags)
        self._create_recipe_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        """Обновление существующего рецепта."""
        tags = validated_data.pop('tags', None)
        if tags is not None:
            instance.tags.set(tags)
        ingredients = validated_data.pop('ingredients', None)
        if ingredients is not None:
            instance.ingredients.clear()
            self._create_recipe_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def _create_recipe_ingredients(self, recipe, ingredients):
        """Создание ингредиентов для рецепта."""
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(recipe=recipe,
                             ingredient=ingredient['id'],
                             amount=ingredient['amount'])
            for ingredient in ingredients
        )

    def to_representation(self, instance):
        """Преобразование экземпляра рецепта в формат для отображения."""
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShopFavorSerializer(serializers.ModelSerializer):
    """Серилизатор для добавления изображения рецепта."""

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class SubscriptionsSerializer(UserSerializer):
    """Сериализатор для отображения подписок на пользователей."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes',
                  'recipes_count', 'avatar',)

    def get_recipes(self, obj):
        """Получение списка рецептов пользователя."""
        recipes = obj.recipes.all()
        recipes_limit = self.context[
            'request'].query_params.get('recipes_limit')
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        return RecipeShopFavorSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        """Получение количества рецептов пользователя."""
        return obj.recipes.count()


class SubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор для управления подписками на пользователей."""

    class Meta:
        model = Follow
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=['user', 'following'],
                message='Вы уже подписаны на этого автора!',
            )
        ]

    def validate(self, attrs):
        """Валидация данных для подписки."""
        user = attrs['user']
        following = attrs['following']
        if user == following:
            raise serializers.ValidationError(
                {'error': 'Нельзя подписаться на себя.'})
        return attrs

    def to_representation(self, instance):
        """Преобразование экземпляра подписки в формат для отображения."""
        return SubscriptionsSerializer(
            instance.following, context=self.context).data


class BaseRecipeSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для избранного и корзины."""

    class Meta:
        abstract = True
        model = None
        fields = ('user', 'recipe')

    def to_representation(self, instance):
        """Преобразование экземпляра в формат для отображения."""
        return RecipeShopFavorSerializer(instance.recipe,
                                         context=self.context).data


class ShoppingCartSerializer(BaseRecipeSerializer):
    """Сериализатор для управления корзиной покупок."""

    class Meta(BaseRecipeSerializer.Meta):
        model = ShoppingCart
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=['user', 'recipe'],
                message='Вы уже добавили рецепт в корзину!',
            )
        ]


class FavoriteRecipeSerializer(BaseRecipeSerializer):
    """Сериализатор для управления избранными рецептами."""

    class Meta(BaseRecipeSerializer.Meta):
        model = FavoriteRecipe
        validators = [
            UniqueTogetherValidator(
                queryset=FavoriteRecipe.objects.all(),
                fields=['user', 'recipe'],
                message='Вы уже подписаны на этого автора!',
            )
        ]
