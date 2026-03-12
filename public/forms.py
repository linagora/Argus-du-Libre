from django import forms


SCORE_CHOICES = [(str(i), str(i)) for i in range(1, 6)]


class CostFeedbackForm(forms.Form):
    """
    Dynamic form for rating the four Costs fields.

    Accepts `fields` (a list of Field instances) at init time to build
    per-field score and note inputs. Field order matches the passed list.
    """

    general_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    locale = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, fields=None, locale=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._cost_fields = fields or []
        for field in self._cost_fields:
            score_key = f"score_{field.slug}"
            note_key = f"note_{field.slug}"
            if locale:
                translation = field.get_translation(locale)
                field_label = translation.name if translation else field.slug
            else:
                field_label = field.slug
            self.fields[score_key] = forms.ChoiceField(
                choices=SCORE_CHOICES,
                widget=forms.RadioSelect(),
                label=field_label,
            )
            self.fields[note_key] = forms.CharField(
                required=False,
                widget=forms.Textarea(attrs={"rows": 2}),
            )

    def get_field_rows(self):
        """
        Returns a list of (field, score_bound_field, note_bound_field) tuples
        for template rendering.
        """
        rows = []
        for field in self._cost_fields:
            rows.append(
                (
                    field,
                    self[f"score_{field.slug}"],
                    self[f"note_{field.slug}"],
                )
            )
        return rows
