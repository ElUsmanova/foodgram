from dataclasses import dataclass
from django.http import HttpResponse
from django.db.models import Sum

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .constants import (FONT_NAME, FONT_SIZE, LINE_SPACING,
                        START_Y_POSITION, TEXT_LEFT_MARGIN)
from recipes.models import RecipeIngredient


@dataclass
class IngredientInfo:
    name: str
    measurement_unit: str
    total_amount: int


def create_ingredients_list(request):
    """Создает список ингредиентов для пользователя
    на основе его покупательской корзины."""
    ingredients = RecipeIngredient.objects.filter(
        recipe__shopping_carts__user=request.user
    ).values(
        'ingredient__name',
        'ingredient__measurement_unit'
    ).annotate(
        total_amount=Sum('amount')
    ).order_by('ingredient__name')

    ingredient_info_list = [
        IngredientInfo(
            name=ingredient['ingredient__name'],
            measurement_unit=ingredient['ingredient__measurement_unit'],
            total_amount=ingredient['total_amount']
        )
        for ingredient in ingredients
    ]

    return ingredient_info_list


def create_pdf(final_list, filename):
    """Создает PDF-документ со списком ингредиентов
    и возвращает его в ответе."""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    p = canvas.Canvas(response, pagesize=letter)
    p.setFont(FONT_NAME, FONT_SIZE)
    y = START_Y_POSITION
    p.drawString(TEXT_LEFT_MARGIN, y, 'Список ингредиентов:')
    y -= LINE_SPACING
    for ingredient_info in final_list:
        name = ingredient_info.name.capitalize()
        measurement_unit = ingredient_info.measurement_unit
        total_amount = ingredient_info.total_amount
        p.drawString(TEXT_LEFT_MARGIN, y,
                     f'{name} ({measurement_unit}): {total_amount}')
        y -= LINE_SPACING
    p.showPage()
    p.save()
    return response
