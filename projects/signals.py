from django.db.models.signals import post_delete
from django.dispatch import receiver

from public.aggregator import CostScoreAggregator

from .models import CostFeedbackEntry


@receiver(post_delete, sender=CostFeedbackEntry)
def recompute_cost_scores_on_entry_delete(sender, instance, **kwargs):
    """Recompute crowdsourced cost scores when an entry is removed."""
    submission = getattr(instance, "submission", None)
    if submission is None:
        return

    software = getattr(submission, "software", None)
    if software is None:
        return

    CostScoreAggregator(software).run()
