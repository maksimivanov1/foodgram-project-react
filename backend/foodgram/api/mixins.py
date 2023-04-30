from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from api.permissions import IsAdminOrReadOnly
from recipes.models import Recipe
from .serializers import SubscribeRecipeSerializer


class GetObjectMixin:
    """Миксин для удаления/добавления рецептов избранных/корзины."""

    serializer_class = SubscribeRecipeSerializer
    permission_classes = (AllowAny,)

    def get_object(self):
        recipe_id = self.kwargs['recipe_id']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        self.check_object_permissions(self.request, recipe)
        return recipe


class PermissionAndPaginationMixin:
    """Миксин для списка тегов и ингридиентов."""

    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None
