from django.conf import settings
from django.db import models

MEALS = [('breakfast', 'Breakfast'), ('lunch', 'Lunch'), ('dinner', 'Dinner')]
WEEKDAYS = [(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')]


class MessSetting(models.Model):
    """Per-outlet planning inputs. Until real attendance exists these ARE the estimates."""
    outlet = models.OneToOneField('outlets.Outlet', on_delete=models.CASCADE, related_name='mess_setting')
    members = models.PositiveIntegerField(default=100)                     # people eligible to eat
    buffer_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5)   # safety margin on cooking quantity
    attendance = models.JSONField(default=dict, blank=True)                # {"mon": {"breakfast": 70, ...}} overrides defaults
    staff_plates_per_cook = models.PositiveIntegerField(default=60)        # plates one cook handles per meal
    staff_plates_per_server = models.PositiveIntegerField(default=40)


class SpecialDay(models.Model):
    """Holiday / exam / event: multiplies expected attendance (0.5 = half the usual crowd)."""
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='special_days')
    date = models.DateField()
    factor = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    note = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ('outlet', 'date')


class Recipe(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recipes')
    name = models.CharField(max_length=120)
    take_rate = models.DecimalField(max_digits=4, decimal_places=2, default=1)     # share of diners who take this dish
    popularity = models.DecimalField(max_digits=4, decimal_places=2, default=1)    # >1 favourite dish pulls more people
    is_estimate = models.BooleanField(default=True)                                # quantities not yet verified by the cook

    class Meta:
        unique_together = ('owner', 'name')
        ordering = ['name']


class RecipeLine(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='lines')
    material = models.ForeignKey('inventory.RawMaterial', on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=10, decimal_places=2)   # per ONE serving, in the material's consumption unit


class MealPlan(models.Model):
    """The weekly rotating menu: which dishes are served at which meal on which weekday."""
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='meal_plan')
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    meal = models.CharField(max_length=10, choices=MEALS)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    take_rate = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)   # overrides the dish default for this slot

    class Meta:
        unique_together = ('outlet', 'weekday', 'meal', 'recipe')


class Attendance(models.Model):
    """Actual people served. This is what the forecast learns from."""
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()
    meal = models.CharField(max_length=10, choices=MEALS)
    actual = models.PositiveIntegerField()
    prepared_portions = models.PositiveIntegerField(null=True, blank=True)
    leftover_portions = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('outlet', 'date', 'meal')


class ForecastSnapshot(models.Model):
    """The prediction as it stood BEFORE the meal, so accuracy can be measured honestly later."""
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE)
    date = models.DateField()
    meal = models.CharField(max_length=10, choices=MEALS)
    expected = models.PositiveIntegerField()
    method = models.CharField(max_length=20, default='estimate')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('outlet', 'date', 'meal')


class WastageLog(models.Model):
    REASONS = [('leftover', 'Cooked but not eaten'), ('spoiled', 'Spoiled / expired'), ('overcooked', 'Overcooked / burnt'),
               ('spill', 'Spill / damage'), ('prep', 'Prep trimming loss'), ('other', 'Other')]
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='wastage')
    date = models.DateField()
    meal = models.CharField(max_length=10, choices=MEALS, blank=True)
    recipe = models.ForeignKey(Recipe, null=True, blank=True, on_delete=models.SET_NULL)
    material = models.ForeignKey('inventory.RawMaterial', null=True, blank=True, on_delete=models.SET_NULL)
    qty = models.DecimalField(max_digits=12, decimal_places=3)       # in consumption unit (material) or portions (recipe)
    reason = models.CharField(max_length=12, choices=REASONS, default='leftover')
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

class DailyPlan(models.Model):
    """The plan the scheduler generated for a day (what to cook, buy, staff). Regenerated whenever the job runs."""
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='daily_plans')
    date = models.DateField()
    payload = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('outlet', 'date')
        ordering = ['-date']


class DailyReport(models.Model):
    """End-of-day summary: served vs forecast, cost, wastage, issues."""
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='daily_reports')
    date = models.DateField()
    payload = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('outlet', 'date')
        ordering = ['-date']


class AutoConsumption(models.Model):
    """What was deducted from stock for one meal (purchase units per material), so re-runs never double count."""
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE)
    date = models.DateField()
    meal = models.CharField(max_length=10, choices=MEALS)
    payload = models.JSONField(default=dict)         # {material_id: "qty in purchase units"}
    headcount = models.PositiveIntegerField(default=0)
    applied_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('outlet', 'date', 'meal')


class AutomationRun(models.Model):
    """Log of every scheduled/manual run so the portal can show what the automation did and when."""
    job = models.CharField(max_length=30, default='daily')
    outlet = models.ForeignKey('outlets.Outlet', null=True, blank=True, on_delete=models.SET_NULL)
    started_at = models.DateTimeField(auto_now_add=True)
    ok = models.BooleanField(default=True)
    summary = models.JSONField(default=dict)
    trigger = models.CharField(max_length=12, default='schedule')   # schedule | manual

    class Meta:
        ordering = ['-started_at']
