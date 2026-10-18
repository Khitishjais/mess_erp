"""
Estimated starting data for a mess with a 7-day rotating menu. EVERY number here is an estimate
(typical Indian mess portions and market prices) -- replace with the cook's real recipes and bills.
The same numbers are listed on the 'Assumptions' sheet of TRACKER.xlsx.
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.inventory.models import RawMaterial
from apps.mess.models import MealPlan, MessSetting, Recipe, RecipeLine
from apps.outlets.models import Outlet

# name: (category, purchase_unit, consumption_unit, conversion, Rs per purchase unit, shelf_life_days, edible_yield_%, pack_step)
MATERIALS = {
    'Rice': ('Grocery', 'kg', 'gm', 1000, 55, 180, 100, 1), 'Atta': ('Grocery', 'kg', 'gm', 1000, 40, 90, 100, 1),
    'Maida': ('Grocery', 'kg', 'gm', 1000, 42, 90, 100, 1), 'Toor Dal': ('Grocery', 'kg', 'gm', 1000, 130, 180, 100, 1),
    'Moong Dal': ('Grocery', 'kg', 'gm', 1000, 110, 180, 100, 1), 'Rajma': ('Grocery', 'kg', 'gm', 1000, 140, 180, 100, 1),
    'Chole (Kabuli Chana)': ('Grocery', 'kg', 'gm', 1000, 120, 180, 100, 1), 'Poha': ('Grocery', 'kg', 'gm', 1000, 60, 120, 100, 1),
    'Suji (Rava)': ('Grocery', 'kg', 'gm', 1000, 50, 120, 100, 1), 'Idli/Dosa Batter': ('Grocery', 'kg', 'gm', 1000, 60, 2, 100, 1),
    'Potato': ('Vegetable', 'kg', 'gm', 1000, 30, 14, 90, 1), 'Onion': ('Vegetable', 'kg', 'gm', 1000, 35, 14, 90, 1),
    'Tomato': ('Vegetable', 'kg', 'gm', 1000, 40, 4, 95, 1), 'Cauliflower': ('Vegetable', 'kg', 'gm', 1000, 50, 3, 75, 1),
    'Bhindi (Okra)': ('Vegetable', 'kg', 'gm', 1000, 60, 3, 90, 1), 'Cabbage': ('Vegetable', 'kg', 'gm', 1000, 30, 5, 85, 1),
    'Mixed Vegetables': ('Vegetable', 'kg', 'gm', 1000, 50, 3, 80, 1), 'Green Peas': ('Vegetable', 'kg', 'gm', 1000, 80, 3, 50, 1),
    'Paneer': ('Dairy', 'kg', 'gm', 1000, 340, 3, 100, 1), 'Chicken': ('Meat', 'kg', 'gm', 1000, 220, 1, 80, 1),
    'Egg': ('Meat', 'pc', 'pc', 1, 7, 10, 100, 30), 'Milk': ('Dairy', 'ltr', 'ml', 1000, 56, 1, 100, 1),
    'Curd': ('Dairy', 'kg', 'gm', 1000, 70, 3, 100, 1), 'Butter': ('Dairy', 'kg', 'gm', 1000, 520, 20, 100, 0.5),
    'Tea Powder': ('Grocery', 'kg', 'gm', 1000, 400, 180, 100, 0.5), 'Sugar': ('Grocery', 'kg', 'gm', 1000, 45, 180, 100, 1),
    'Cooking Oil': ('Grocery', 'ltr', 'ml', 1000, 130, 180, 100, 1), 'Masala Mix (spices)': ('Grocery', 'kg', 'gm', 1000, 400, 120, 100, 0.5),
    'Bread': ('Bakery', 'pc', 'pc', 1, 4, 3, 100, 20),
}
# dish: (take_rate, popularity, {material: qty per ONE serving in consumption unit})
RECIPES = {
    'Poha': (1, 1, {'Poha': 60, 'Onion': 25, 'Potato': 30, 'Cooking Oil': 8, 'Masala Mix (spices)': 2}),
    'Tea': (.8, 1, {'Milk': 100, 'Tea Powder': 2, 'Sugar': 10}),
    'Idli Sambar': (1, 1.05, {'Idli/Dosa Batter': 120, 'Toor Dal': 25, 'Mixed Vegetables': 40, 'Onion': 15, 'Masala Mix (spices)': 3, 'Cooking Oil': 5}),
    'Upma': (1, .9, {'Suji (Rava)': 60, 'Onion': 20, 'Green Peas': 10, 'Cooking Oil': 8, 'Masala Mix (spices)': 2}),
    'Aloo Paratha': (1, 1.1, {'Atta': 80, 'Potato': 70, 'Cooking Oil': 10, 'Masala Mix (spices)': 2}),
    'Curd': (.7, 1, {'Curd': 80}),
    'Bread Egg': (1, 1, {'Bread': 2, 'Egg': 1, 'Onion': 10, 'Cooking Oil': 5}),
    'Puri Bhaji': (1, 1.1, {'Atta': 90, 'Cooking Oil': 25, 'Potato': 100, 'Onion': 15, 'Masala Mix (spices)': 3}),
    'Masala Dosa': (1, 1.1, {'Idli/Dosa Batter': 130, 'Potato': 80, 'Onion': 25, 'Cooking Oil': 10, 'Masala Mix (spices)': 2}),
    'Steamed Rice': (1, 1, {'Rice': 100}),
    'Roti': (1, 1, {'Atta': 60, 'Cooking Oil': 3}),
    'Dal Tadka': (1, 1, {'Toor Dal': 40, 'Onion': 15, 'Tomato': 20, 'Cooking Oil': 8, 'Masala Mix (spices)': 3}),
    'Rajma': (1, 1.05, {'Rajma': 50, 'Onion': 30, 'Tomato': 30, 'Cooking Oil': 10, 'Masala Mix (spices)': 5}),
    'Chole': (1, 1.05, {'Chole (Kabuli Chana)': 70, 'Onion': 30, 'Tomato': 30, 'Cooking Oil': 10, 'Masala Mix (spices)': 6}),
    'Aloo Gobi': (1, .95, {'Potato': 60, 'Cauliflower': 80, 'Onion': 20, 'Tomato': 15, 'Cooking Oil': 10, 'Masala Mix (spices)': 4}),
    'Bhindi Fry': (1, .9, {'Bhindi (Okra)': 100, 'Onion': 20, 'Cooking Oil': 12, 'Masala Mix (spices)': 3}),
    'Mix Veg': (1, .95, {'Mixed Vegetables': 120, 'Green Peas': 15, 'Onion': 20, 'Tomato': 20, 'Cooking Oil': 10, 'Masala Mix (spices)': 4}),
    'Cabbage Poriyal': (1, .85, {'Cabbage': 100, 'Onion': 10, 'Cooking Oil': 8, 'Masala Mix (spices)': 2}),
    'Sambar': (1, 1, {'Toor Dal': 30, 'Mixed Vegetables': 50, 'Onion': 15, 'Cooking Oil': 6, 'Masala Mix (spices)': 4}),
    'Egg Curry': (.8, 1.05, {'Egg': 2, 'Onion': 40, 'Tomato': 30, 'Cooking Oil': 12, 'Masala Mix (spices)': 5}),
    'Chicken Curry': (.75, 1.1, {'Chicken': 150, 'Onion': 50, 'Tomato': 40, 'Cooking Oil': 15, 'Masala Mix (spices)': 8}),
    'Paneer Butter Masala': (1, 1.1, {'Paneer': 80, 'Onion': 40, 'Tomato': 60, 'Butter': 10, 'Cooking Oil': 8, 'Masala Mix (spices)': 5}),
    'Dal Makhani': (1, 1.05, {'Rajma': 25, 'Toor Dal': 25, 'Butter': 10, 'Cooking Oil': 5, 'Masala Mix (spices)': 4}),
    'Veg Pulao': (1, 1, {'Rice': 100, 'Mixed Vegetables': 60, 'Green Peas': 15, 'Onion': 20, 'Cooking Oil': 10, 'Masala Mix (spices)': 4}),
    'Veg Biryani': (1, 1.05, {'Rice': 110, 'Mixed Vegetables': 70, 'Onion': 30, 'Curd': 25, 'Cooking Oil': 14, 'Masala Mix (spices)': 6}),
    'Chicken Biryani': (.75, 1.15, {'Rice': 110, 'Chicken': 130, 'Onion': 50, 'Curd': 30, 'Cooking Oil': 15, 'Masala Mix (spices)': 8}),
    'Raita': (.6, 1, {'Curd': 80, 'Onion': 10, 'Masala Mix (spices)': 1}),
    'Khichdi': (1, .9, {'Rice': 70, 'Moong Dal': 30, 'Cooking Oil': 8, 'Masala Mix (spices)': 2}),
    'Kheer': (.8, 1.1, {'Milk': 150, 'Rice': 15, 'Sugar': 20}),
}
# weekday 0=Mon .. 6=Sun ; (dish, optional take-rate override for that slot)
PLAN = {
    0: {'breakfast': ['Poha', 'Tea'], 'lunch': ['Steamed Rice', 'Dal Tadka', 'Aloo Gobi', 'Roti'], 'dinner': ['Steamed Rice', 'Rajma', 'Mix Veg', 'Roti']},
    1: {'breakfast': ['Idli Sambar', 'Tea'], 'lunch': ['Steamed Rice', 'Dal Tadka', 'Bhindi Fry', 'Roti'], 'dinner': ['Steamed Rice', 'Egg Curry', ('Dal Tadka', .5), 'Roti']},
    2: {'breakfast': ['Upma', 'Tea'], 'lunch': ['Veg Pulao', 'Raita', 'Dal Tadka'], 'dinner': ['Steamed Rice', 'Chicken Curry', ('Dal Tadka', .5), 'Roti']},
    3: {'breakfast': ['Aloo Paratha', 'Curd', 'Tea'], 'lunch': ['Steamed Rice', 'Chole', 'Roti'], 'dinner': ['Steamed Rice', 'Dal Tadka', 'Paneer Butter Masala', 'Roti']},
    4: {'breakfast': ['Bread Egg', 'Tea'], 'lunch': ['Steamed Rice', 'Sambar', 'Cabbage Poriyal', 'Roti'], 'dinner': ['Veg Biryani', 'Raita']},
    5: {'breakfast': ['Puri Bhaji', 'Tea'], 'lunch': ['Steamed Rice', 'Dal Makhani', 'Mix Veg', 'Roti'], 'dinner': ['Chicken Biryani', ('Veg Biryani', .35), 'Raita']},
    6: {'breakfast': ['Masala Dosa', 'Tea'], 'lunch': ['Steamed Rice', 'Paneer Butter Masala', 'Roti', 'Kheer'], 'dinner': ['Khichdi', 'Raita']},
}


class Command(BaseCommand):
    help = 'Create an estimated mess setup: materials, recipes, the 7-day x 3-meal plan.'

    def add_arguments(self, p):
        p.add_argument('--members', type=int, default=120)

    def handle(self, *a, members, **kw):
        owner = User.objects.filter(is_owner=True).first()
        if not owner:
            self.stderr.write('No owner user found. Run seed_demo first or create an owner.')
            return
        outlet, _ = Outlet.objects.get_or_create(owner=owner, code='2001', defaults={'name': 'Hostel Mess', 'kind': 'mess', 'brand': 'Mess'})
        s, _ = MessSetting.objects.get_or_create(outlet=outlet)
        s.members = members
        s.save()
        mats = {}
        for name, (cat, pu, cu, conv, cost, shelf, yld, pack) in MATERIALS.items():
            m, _ = RawMaterial.objects.update_or_create(owner=owner, name=name, defaults=dict(
                category=cat, purchase_unit=pu, consumption_unit=cu, conversion=conv, unit_cost=cost,
                shelf_life_days=shelf, yield_pct=yld, pack_size=pack))
            mats[name] = m
        rec = {}
        for dish, (take, pop, lines) in RECIPES.items():
            r, _ = Recipe.objects.update_or_create(owner=owner, name=dish, defaults={'take_rate': take, 'popularity': pop, 'is_estimate': True})
            r.lines.all().delete()
            RecipeLine.objects.bulk_create([RecipeLine(recipe=r, material=mats[m], qty=q) for m, q in lines.items()])
            rec[dish] = r
        MealPlan.objects.filter(outlet=outlet).delete()
        n = 0
        for wd, meals in PLAN.items():
            for meal, dishes in meals.items():
                for d in dishes:
                    name, take = (d, None) if isinstance(d, str) else d
                    MealPlan.objects.create(outlet=outlet, weekday=wd, meal=meal, recipe=rec[name], take_rate=take)
                    n += 1
        self.stdout.write(self.style.SUCCESS(f'Mess "{outlet.name}": {len(mats)} materials, {len(rec)} recipes, {n} menu slots, {members} members (all estimates).'))