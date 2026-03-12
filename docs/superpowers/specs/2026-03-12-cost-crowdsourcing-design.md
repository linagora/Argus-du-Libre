# Cost crowdsourcing design

## Overview

We currently publish automated scores for the Community, Tech and Security categories via qsos-lng, but we have no reliable signal for Costs yet. The goal of this feature is to collect anonymous, crowd-sourced input for the four Costs fields (degree of openness, support cost, deployment cost, training cost), compute the mean of those ratings, and treat the average as the project score in each field. Users should also be able to leave a short note per field so their rationale is visible on the project detail page. Feedback must be anonymous (no login) but we will keep the request IP for basic abuse tracing and we display submissions immediately without manual approval.

## Requirements

1. Allow web visitors to rate the four Costs fields, supplying a 1–5 integer and an optional text note for each field plus an optional general comment.
2. Store feedback per software, per locale, with the submitter IP and creation timestamp.
3. Aggregate all ratings per software + field into a mean and persist that value in the same place that the public views currently read (`AnalysisResult`) so the UI stays consistent.
4. Show the latest crowd comments (per field notes + optional general comment) on the project detail page, immediately after submission and without approval.
5. Provide a smooth, mobile-friendly UI for the rating form, reusing existing styling conventions where possible.
6. Provide automated tests covering the new form, aggregation logic, and display of comments.

## Data model

### `CostFeedbackSubmission`
- `software`: FK to `projects.Software` (cascade)
- `locale`: language code the commenter was viewing (max 10 chars)
- `general_comment`: optional text field for overall context
- `ip_address`: anonymized request IP (same format as Django `GenericIPAddressField`)
- `created_at`: auto `DateTimeField`

### `CostFeedbackEntry`
- `submission`: FK to `CostFeedbackSubmission` (cascade)
- `field`: FK to `projects.Field`, constrained to the four Costs field slugs (`openness-degree`, `support-cost`, `deployment-cost`, `training-cost`) so both validation and aggregation use a deterministic set
- `score`: `PositiveSmallIntegerField` limited to 1..5
- `note`: optional short text describing what informed the score

Unique constraint on `(submission, field)` ensures one entry per field per submission. The entries table provides easy filtering, summaries, and cataloguing of notes for each field.

## Submission flow

1. The project detail page renders a new `CostFeedbackForm` that exposes four labelled score-and-note rows (one per Costs field) plus an optional general comment textarea and a hidden locale value.
2. Each row provides a 1–5 selector (e.g., radio buttons or a stylized slider) and a small textarea for field-specific notes.
3. The form posts to a new view (`public:create_cost_feedback`) that accepts POST only, validates scores/notes, and atomically creates one `CostFeedbackSubmission` plus four `CostFeedbackEntry` objects.
4. Validation enforces that each entry references the same four Costs field slugs (`openness-degree`, `support-cost`, `deployment-cost`, `training-cost`) and that scores fall within 1–5.
5. After saving, `create_cost_feedback` triggers the aggregation service (see below) inside `transaction.on_commit` so the fresh averages land in `AnalysisResult` before the user is redirected back to the project detail page with a success message.

## Aggregation service

We introduce a lightweight helper class (`CostScoreAggregator`) that:

1. Accepts a `Software` and optional `Field` queryset (defaults to the four costs fields).
2. Queries `CostFeedbackEntry` grouped by field + software, computes the average of `score` (Decimal with two decimal places), and either updates or creates an `AnalysisResult` for that field with `is_manual=True` (and `is_published=True`).
3. Runs inside `transaction.atomic` (wrapped via `on_commit`) so the new submission immediately affects the displayed scores. A periodic management command (`uv run python manage.py compute_cost_scores`) can also call this helper to recalculate everything in case of data corruption or bulk imports; it simply iterates over published softwares using the same helper.

The aggregator only touches the cost fields to avoid overwriting other automated scores. It looks up those fields by the same slug list so we never accidentally include unrelated fields. If there are no feedback entries for a field, the helper simply skips that field, leaving any previously stored `AnalysisResult` untouched so the category continues to hide the field until ratings arrive again.

## Score display

The public views already compute field and category scores from `AnalysisResult`. Because the aggregation service writes into that table, the category calculation automatically uses the crowd average without further changes.

To make the feedback context visible, the project detail template will render a new card below the costs category called “User cost feedback,” showing:

1. A summary row per field with the current average (including the existing badges) so the user sees how the community rated the field.
2. A list of the 5 most recent submissions per field (or per software) showing the note text plus the submission timestamp and locale.
3. The optional general comment (if provided by a submission) rendered between the summary row and the individual notes so the collective rationale is visible up front.
4. A CTA “Share your experience” that expands/collapses the rating form (or anchors to it).

Metrics and related templates reuse existing CSS for cards/badges; the new card inherits the `.category-card` style.

## API & routing

1. Add `path('<slug>/cost-feedback/', create_cost_feedback, name='create_cost_feedback')` to the `public` URLconf.
2. The view enforces POST/CSRF and returns `HttpResponseRedirect` to the project detail page with `?feedback=created` query parameter for success messaging.
3. The form builder uses Django forms to pre-validate score ranges and required fields. Field notes stay optional.
4. No API endpoint is exposed for data export; we read feedback via Django admin for moderation.

## Security & moderation

1. The view records `request.META.get('REMOTE_ADDR')` (with fallback to `request.META.get('HTTP_X_FORWARDED_FOR')`) to `CostFeedbackSubmission.ip_address` so we can trace abusive submitters. No personally identifiable user data is collected.
2. The form is rate-limited using Django’s `ratelimit` decorator (if available) or a combination of IP+timestamp checks to prevent spam.
3. Comments publish immediately but can be removed through standard Django admin actions if abuse arises; we do not track additional moderation flags yet.

## Testing

1. Form tests: ensure only the four costs fields can be submitted, invalid scores are rejected, and notes/locale round-trip correctly.
2. View tests: POSTing valid data creates the submission/entries and redirects with a message; invalid POST returns errors.
3. Aggregator tests: new feedback averages update/insert the correct `AnalysisResult`; deleting all entries leaves the score untouched until new data arrives.
4. Template tests: the project detail page renders the new card with the aggregate score, latest comments, and the submission form when `?feedback=created` is in the query string.

## Next steps

1. Implement the data models + form.
2. Wire the aggregation helper and hook the view to call it.
3. Update the project detail template with the new card/form.
4. Add unit tests and manual QA verifying the scoring flow.
