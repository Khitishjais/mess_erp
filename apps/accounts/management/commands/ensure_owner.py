"""Create the first owner from environment secrets (OWNER_EMAIL, OWNER_PASSWORD, OWNER_NAME). Does nothing when an owner already exists,
so it is safe to run on every start. Used for hosted deployments, where no demo data / demo password may exist."""
import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User


def owner_exists():
    return User.objects.filter(is_owner=True).exists()


class Command(BaseCommand):
    help = 'Create the first owner account from OWNER_EMAIL / OWNER_PASSWORD (skipped if an owner exists).'

    def handle(self, *args, **opts):
        if owner_exists():
            self.stdout.write('An owner already exists; nothing to do.')
            return
        email, password = os.environ.get('OWNER_EMAIL', '').strip(), os.environ.get('OWNER_PASSWORD', '')
        if not email or len(password) < 10:
            self.stdout.write(self.style.WARNING('No owner created: set OWNER_EMAIL and an OWNER_PASSWORD of at least 10 characters.'))
            return
        User.objects.create_user(email=email, password=password, name=os.environ.get('OWNER_NAME', 'Owner'), is_owner=True)
        self.stdout.write(self.style.SUCCESS(f'Owner {email} created.'))
