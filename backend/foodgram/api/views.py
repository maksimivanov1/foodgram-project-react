from django.contrib.auth import get_user_model
from django.db.models.aggregates import Count, Sum
from django.db.models import F
from django.db.models.expressions import Exists, OuterRef, Value
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import generics, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action, api_view
from rest_framework.permissions import (SAFE_METHODS, AllowAny,
                                        IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from django.http.response import HttpResponse

from api.filters import IngredientFilter, RecipeFilter
from api.mixins import GetObjectMixin, PermissionAndPaginationMixin
from .serializers import (CustomUserCreateSerializer, CustomUserSerializer,
                          IngredientSerializer, RecipeReadSerializer,
                          RecipeWriteSerializer, SubscribeSerializer, 
                          TagSerializer, TokenSerializer,
                          UserPasswordSerializer)
from recipes.models import (FavoriteRecipe, Ingredient, Recipe, ShoppingCart,
                            Tag, RecipeIngredient)

User = get_user_model()
FILENAME = 'shoppingcart.pdf'


class AddAndDeleteSubscribe(
        generics.RetrieveDestroyAPIView,
        generics.ListCreateAPIView):
    """Подписка и отписка от пользователя."""

    serializer_class = SubscribeSerializer

    def get_queryset(self):
        return self.request.user.follower.select_related(
            'following'
        ).prefetch_related(
            'following__recipe'
        ).annotate(
            recipes_count=Count('following__recipe'),
        )

    def get_object(self):
        author_id = self.kwargs['author_id']
        author = get_object_or_404(User, id=author_id)
        self.check_object_permissions(self.request, author)
        return author

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        data.update({'author': instance})
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user.id, author=instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.follower.filter(author=instance).delete()


class AddDeleteFavoriteRecipe(
        GetObjectMixin,
        generics.RetrieveDestroyAPIView,
        generics.ListCreateAPIView):
    """Добавление и удаление рецепта в избранных."""

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        request.user.favorite_recipe.recipe.add(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.favorite_recipe.recipe.remove(instance)


class AuthToken(ObtainAuthToken):
    """Авторизация пользователя."""

    serializer_class = TokenSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {'auth_token': token.key},
            status=status.HTTP_201_CREATED)


class UsersViewSet(UserViewSet):
    """Пользователи."""
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method.lower() == 'post':
            return CustomUserCreateSerializer
        return CustomUserSerializer

    def perform_create(self, serializer):
        serializer.save(password=self.request.data['password'])

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        """Получить подписки пользователя."""

        queryset = request.user.follower.filter(user=request.user.id)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(
            pages, many=True,
            context={'request': request})
        return self.get_paginated_response(serializer.data)


class RecipesViewSet(viewsets.ModelViewSet): 
    """Рецепты.""" 
 
    filterset_class = RecipeFilter 
    permission_classes = (IsAuthenticatedOrReadOnly,) 
 
    def get_serializer_class(self): 
        if self.request.method in SAFE_METHODS: 
            return RecipeReadSerializer 
        return RecipeWriteSerializer 
 
    def get_queryset(self): 
        return Recipe.objects.annotate( 
            is_favorited=Exists( 
                FavoriteRecipe.objects.filter( 
                    user=self.request.user, recipe=OuterRef('id'))), 
            is_in_shopping_cart=Exists( 
                ShoppingCart.objects.filter( 
                    user=self.request.user, 
                    recipe=OuterRef('id'))) 
        ).select_related('author').prefetch_related( 
            'tags', 'ingredients', 'recipe', 
            'shopping_cart', 'favorite_recipe' 
        ) if self.request.user.is_authenticated else Recipe.objects.annotate( 
            is_in_shopping_cart=Value(False), 
            is_favorited=Value(False), 
        ).select_related('author').prefetch_related( 
            'tags', 'ingredients', 'recipe', 
            'shopping_cart', 'favorite_recipe') 
 
    def perform_create(self, serializer): 
        serializer.save(author=self.request.user) 
 
    @action(
        detail=False,
        methods=('get', ),
        permission_classes=(IsAuthenticated, )
    )
    def download_shopping_cart(self, request):
        """Скачивание ингредиентов из списка покупок."""
        ingredients = (
            RecipeIngredient.objects
            .filter(shopping_cart__user=request.user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(amount=Sum(F('amount')))
            .order_by()
        )
        shop_list = []
        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            measurement_unit = ingredient['ingredient__measurement_unit']
            amount = ingredient['amount']
            shop_list.append(
                f'\n{name} - {amount} {measurement_unit}')
        result = 'shop_list.txt'
        response = HttpResponse(
            shop_list,
            content_type='text/plain'
        )
        response['Content-Disposition'] = f'attachment; filename={result}'
        return response 


class AddDeleteShoppingCart( 
        GetObjectMixin, 
        generics.RetrieveDestroyAPIView, 
        generics.ListCreateAPIView): 
    """Добавить и удалить рецепт в корзине.""" 
 
    def create(self, request, *args, **kwargs): 
        instance = self.get_object() 
        request.user.shopping_cart.recipe.add(instance) 
        serializer = self.get_serializer(instance) 
        return Response(serializer.data, status=status.HTTP_201_CREATED) 
 
    def perform_destroy(self, instance): 
        self.request.user.shopping_cart.recipe.remove(instance) 



class TagsViewSet(
        PermissionAndPaginationMixin,
        viewsets.ModelViewSet):
    """Список тэгов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientsViewSet(
        PermissionAndPaginationMixin,
        viewsets.ModelViewSet):
    """Список ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter


@api_view(['post'])
def set_password(request):
    """Изменить пароль."""

    serializer = UserPasswordSerializer(
        data=request.data,
        context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(
            {'message': 'Пароль успешно изменен!'},
            status=status.HTTP_201_CREATED)
    return Response(
        {'error': 'Введите верные данные!'},
        status=status.HTTP_400_BAD_REQUEST)
