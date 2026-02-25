"""Management command to export software metrics to CSV."""

import csv
import sys

from django.core.management.base import BaseCommand

from projects.models import AnalysisResult, Field, Software


class Command(BaseCommand):
    help = "Export published softwares with their published field scores to CSV"

    def handle(self, *args, **options):
        fields = list(
            Field.objects.select_related("category").order_by(
                "category__weight", "weight", "id"
            )
        )
        field_slugs = [f.slug for f in fields]

        softwares = Software.objects.filter(state=Software.STATE_PUBLISHED).order_by(
            "slug"
        )

        scores = AnalysisResult.objects.filter(
            software__state=Software.STATE_PUBLISHED,
            is_published=True,
        ).values_list("software_id", "field_id", "score")

        score_map = {(sw_id, field_id): score for sw_id, field_id, score in scores}

        writer = csv.writer(sys.stdout)
        writer.writerow(["software"] + field_slugs)

        for software in softwares:
            row = [software.slug]
            for field in fields:
                score = score_map.get((software.id, field.id))
                row.append(str(score) if score else "")
            writer.writerow(row)
