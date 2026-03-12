from django.core.management.base import BaseCommand

from projects.models import Software
from public.aggregator import CostScoreAggregator


class Command(BaseCommand):
    help = (
        "Recompute crowd-sourced cost scores for all published software. "
        "Reads CostFeedbackEntry rows, averages per field, and writes to AnalysisResult."
    )

    def handle(self, *args, **options):
        softwares = Software.objects.filter(state=Software.STATE_PUBLISHED)
        total = softwares.count()
        self.stdout.write(f"Computing cost scores for {total} published software(s)...")

        for software in softwares:
            CostScoreAggregator(software).run()
            self.stdout.write(f"  {software.name}")

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {total} software(s)."))
