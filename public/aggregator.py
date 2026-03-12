from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Avg

from projects.models import (
    AnalysisResult,
    CostFeedbackEntry,
    Field,
    Software,
    COSTS_FIELD_SLUGS,
)


class CostScoreAggregator:
    """
    Computes mean CostFeedbackEntry scores per Costs field for a single
    Software instance and writes the results into AnalysisResult.

    Only fields whose slug is in COSTS_FIELD_SLUGS are ever written;
    all other AnalysisResult rows are left untouched.

    If a field has no entries, the corresponding AnalysisResult is left as-is.
    """

    def __init__(self, software: Software):
        self.software = software
        self._costs_fields = list(Field.objects.filter(slug__in=COSTS_FIELD_SLUGS))

    def run(self):
        with transaction.atomic():
            for field in self._costs_fields:
                avg = CostFeedbackEntry.objects.filter(
                    submission__software=self.software,
                    field=field,
                ).aggregate(avg=Avg("score"))["avg"]
                if avg is None:
                    continue  # no entries -- leave existing result untouched
                score = Decimal(str(avg)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                AnalysisResult.objects.update_or_create(
                    software=self.software,
                    field=field,
                    defaults={
                        "score": score,
                        "is_published": True,
                        "is_manual": True,
                    },
                )
