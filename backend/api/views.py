from django.http import JsonResponse
from django.db.models import Count
from rest_framework.generics import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet

from .filters import RecipeFilter, IngredientSearchFilter
from users.models import User
from recipes.models import (Tag, Ingredient, Recipe,
                            FavoriteRecipe, ShoppingCart)
from .permissions import IsStaffOrIsAuthorOrReadOnly
from .pagination import PagePagination
from .serializers import (UserSerializer, AvatarSerializer, TagSerializer,
                          IngredientSerializer, RecipeReadSerializer,
                          RecipeCreateUpdateSerializer,
                          FavoriteRecipeSerializer, ShoppingCartSerializer,
                          SubscriptionsSerializer, SubscribeSerializer)

from .pdf import create_ingredients_list, create_pdf


class RecipeViewSet(ModelViewSet):
    """Вьюсет для работы с рецептами."""

    permission_classes = (IsStaffOrIsAuthorOrReadOnly,)
    http_method_names = ('get', 'post', 'patch', 'delete')
    pagination_class = PagePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        """Возвращает список рецептов
        с предварительной выборкой связанных данных."""
        return Recipe.objects.select_related(
            'author').prefetch_related('ingredients', 'tags')

    def get_serializer_class(self, *args, **kwargs):
        """Возвращает соответствующий сериализатор
        в зависимости от действия."""
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeCreateUpdateSerializer

    @staticmethod
    def add_method(serializer_cls, request, pk):
        """Добавляет рецепт в избранное или в корзину покупок."""
        if not Recipe.objects.filter(id=pk).exists():
            return Response(data={
                'error': 'Вы пытаетесь добавить несуществующий рецепт'},
                status=status.HTTP_404_NOT_FOUND)
        serializer = serializer_cls(data={
            'user': request.user.id,
            'recipe': pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_method(model, request, pk):
        """Удаляет рецепт из избранного или корзины покупок."""
        if not Recipe.objects.filter(id=pk).exists():
            return Response(
                data={
                    'error': 'Вы пытаетесь удалить несуществующий рецепт'},
                status=status.HTTP_404_NOT_FOUND
            )
        del_item, item = model.objects.filter(
            user=request.user, recipe=pk).delete()
        if del_item:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response('Нет в добавленных.',
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=('get',), url_path='get-link')
    def get_link(self, request, pk):
        """Возвращает короткую ссылку на рецепт."""
        recipe = get_object_or_404(Recipe, id=pk)
        url_link = (
            f'https://foodgram-best.zapto.org/recipes/s/{recipe.url_link}')
        return JsonResponse({'short-link': url_link})

    @action(detail=True, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk):
        """Добавляет рецепт в избранное."""
        return self.add_method(FavoriteRecipeSerializer, request, pk)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        """Удаляет рецепт из избранного."""
        return self.delete_method(FavoriteRecipe, request, pk)

    @action(detail=True, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        """Добавляет рецепт в корзину покупок."""
        return self.add_method(ShoppingCartSerializer, request, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        """Удаляет рецепт из корзины покупок."""
        return self.delete_method(ShoppingCart, request, pk)

    @action(methods=('get',), detail=False,
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        """Загружает список ингредиентов из корзины покупок в формате PDF."""
        final_list = create_ingredients_list(request)
        return create_pdf(final_list, "ingredients_list.pdf")


class IngredientViewSet(ReadOnlyModelViewSet):
    """Вьюсет ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientSearchFilter,)
    search_fields = ('^name',)


class TagViewSet(ReadOnlyModelViewSet):
    """Вьюсет тэгов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class UserViewSet(DjoserUserViewSet):
    """Вьюсет для работы с пользователями"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = PagePagination

    def get_queryset(self):
        """Получение списка пользователей,
        на которых подписан текущий пользователь."""
        user = self.request.user
        return User.objects.filter(subscribers=user).annotate(
            recipes_count=Count('recipes'))

    @action(detail=True, methods=['post'],
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id):
        """"Подписка на указанного пользователя по ID."""
        user = request.user
        if not User.objects.filter(id=id).exists():
            return Response(
                data={
                    'error': (
                        'Вы пытаетесь подписаться на несуществующего юзера'
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SubscribeSerializer(
            data={'user': user.id, 'following': id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        """Удаление подписки."""
        if not User.objects.filter(id=id).exists():
            return Response(
                data={
                    'Вы пытаетесь удалить несуществующего подписчика',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        del_item, item = request.user.follower.filter(
            following=id).delete()
        if del_item:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response('Нет в добавленных.',
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        """Получение списка подписок текущего пользователя."""
        queryset = User.objects.filter(
            following__user=self.request.user)
        pag = self.paginate_queryset(queryset)
        serializer = SubscriptionsSerializer(
            pag, context={'request': request}, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=('put',), url_path='me/avatar',
            permission_classes=(IsAuthenticated,))
    def update_avatar(self, request):
        """Обновление аватара текущего пользователя."""
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @update_avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаление аватара."""
        request.user.avatar.delete()
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Получение информации о текущем пользователе."""
        serializer = UserSerializer(
            request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecipeByShortCodeDetailView(RetrieveAPIView):
    """Вьюсет обработки короткой ссылки на рецепт."""

    serializer_class = RecipeReadSerializer
    lookup_field = 'url_link'
    lookup_url_kwarg = 'short_code'

    def get_queryset(self):
        """Возвращает все рецепты для обработки запросов."""
        return Recipe.objects.all()

    def get_object(self):
        """Получает объект рецепта по короткой ссылке."""
        short_code = self.kwargs['short_code']
        return get_object_or_404(Recipe, url_link=short_code)
