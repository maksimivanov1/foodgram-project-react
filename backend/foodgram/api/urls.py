from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (AddAndDeleteSubscribe, AddDeleteFavoriteRecipe,
                       AuthToken, IngredientsViewSet,
                       RecipesViewSet, TagsViewSet, UsersViewSet, set_password)

app_name = 'api'

router = DefaultRouter()
router.register('users', UsersViewSet, basename='users')
router.register('tags', TagsViewSet, basename='tags')
router.register('ingredients', IngredientsViewSet, basename='ingredients')
router.register(r'recipes', RecipesViewSet)


urlpatterns = [
     path('auth/token/login/',
          AuthToken.as_view(),
          name='login'),
     path('users/set_password/',
          set_password,
          name='set_password'),
     path('users/<int:author_id>/subscribe/',
          AddAndDeleteSubscribe.as_view(),
          name='subscribe'),
     path('recipes/<int:recipe_id>/favorite/',
          AddDeleteFavoriteRecipe.as_view(),
          name='favorite_recipe'),
     path('', include(router.urls)),
     path('', include('djoser.urls')),
     path('auth/', include('djoser.urls.authtoken')),
]
