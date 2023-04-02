import json

from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from recipes.models import Ingredient


class Command(BaseCommand):
    def handle(self, *args, **options):

        with open("/Users/maksim/Desktop/!/dev/foodgram-project-react/data/ingredients.json", "rb") as f:
            data = json.load(f)

            for val in data:
                try:
                    ingredient = Ingredient()
                    ingredient.name = val["name"]
                    ingredient.measurement_unit = val["measurement_unit"]
                    ingredient.save()
                except IntegrityError:
                    continue
        print("finished")
        