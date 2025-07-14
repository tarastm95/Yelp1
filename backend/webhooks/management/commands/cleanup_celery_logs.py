from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from webhooks.models import CeleryTaskLog

class Command(BaseCommand):
    help = "Delete CeleryTaskLog entries older than a given number of days"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete logs older than this many days (default: 30)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        cutoff = timezone.now() - timedelta(days=days)
        qs = CeleryTaskLog.objects.filter(
            Q(finished_at__lt=cutoff)
            | Q(finished_at__isnull=True, started_at__lt=cutoff)
            | Q(finished_at__isnull=True, started_at__isnull=True, eta__lt=cutoff)
        )
        deleted, _ = qs.delete()
        self.stdout.write(f"Deleted {deleted} CeleryTaskLog entries older than {days} days")

