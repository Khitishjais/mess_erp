"""Live knowledge: this business's own records turned into short, readable facts. ALWAYS scoped to one tenant."""
from apps.catalog.models import Item
from apps.inventory.models import RawMaterial
from apps.mess.models import MealPlan, MessSetting, Recipe

from ..models import Feedback
from .docs import Chunk

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def _n(v):
    return f'{float(v):g}'


def menu_items(owner):
    return [Chunk(f'Menu item: {i.name}', f"{i.name} costs Rs {_n(i.price)} ({i.category.name}, {'veg' if i.is_veg else 'non-veg'}"
                  f"{'' if i.is_active else ', currently inactive'}).", 'data', 'Menu')
            for i in Item.objects.filter(owner=owner).select_related('category')[:400]]


def materials(owner):
    return [Chunk(f'Raw material: {m.name}', f"{m.name} ({m.category or 'general'}): Rs {_n(m.unit_cost)} per {m.purchase_unit}, "
                  f"stays good {m.shelf_life_days} days, edible yield {_n(m.yield_pct)}%, bought in steps of {_n(m.pack_size)} {m.purchase_unit}.",
                  'data', 'Raw materials') for m in RawMaterial.objects.filter(owner=owner)[:400]]


def recipes(owner):
    out = []
    for r in Recipe.objects.filter(owner=owner).prefetch_related('lines__material')[:300]:
        parts = ', '.join(f'{ln.material.name} {_n(ln.qty)} {ln.material.consumption_unit}' for ln in r.lines.all())
        out.append(Chunk(f'Recipe: {r.name}', f"One plate of {r.name} needs: {parts or 'no ingredients entered yet'}."
                         f"{' (estimate, not yet verified by the cook)' if r.is_estimate else ''}", 'data', 'Recipes'))
    return out


def weekly_menu(outlets):
    out = []
    for o in outlets:
        for wd in range(7):
            rows = MealPlan.objects.filter(outlet=o, weekday=wd).select_related('recipe').order_by('meal')
            by = {}
            for r in rows:
                by.setdefault(r.meal, []).append(r.recipe.name)
            if by:
                out.append(Chunk(f'{o.name} menu on {DAYS[wd]}', f"{o.name}, {DAYS[wd]}: " + '; '.join(f"{m}: {', '.join(v)}" for m, v in by.items()) + '.',
                                 'data', 'Weekly menu'))
    return out


def settings(outlets):
    return [Chunk(f'Mess settings: {s.outlet.name}', f"{s.outlet.name} is planned for {s.members} members with a {_n(s.buffer_pct)}% safety buffer.",
                  'data', 'Mess settings') for s in MessSetting.objects.filter(outlet__in=outlets).select_related('outlet')]


def feedback(outlets):
    return [Chunk(f'Feedback {f.date}', f"Feedback ({f.date}, {f.meal or 'any meal'}, rating {f.rating or 'n/a'}, {f.sentiment or 'unrated'}): {f.text[:300]}",
                  'data', 'Feedback') for f in Feedback.objects.filter(outlet__in=outlets).order_by('-id')[:60]]


def live_chunks(owner, outlets):
    return menu_items(owner) + materials(owner) + recipes(owner) + weekly_menu(outlets) + settings(outlets) + feedback(outlets)
