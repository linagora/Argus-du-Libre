"""Management command to import software tags from a CSV file."""

import csv

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from projects.models import Software, Tag


class Command(BaseCommand):
    help = "Import software tags from a CSV file (columns: Software, Tag 1, Tag 2, Tag 3). Replaces existing tags."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to the CSV file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes will be made."))

        try:
            with open(csv_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                next(reader)  # skip header row
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")

        not_found = []
        updated = 0

        for row in rows:
            if not row or not row[0].strip():
                continue

            software_name = row[0].strip()
            tag_names = [cell.strip() for cell in row[1:] if cell.strip()]

            try:
                software = Software.objects.get(name__iexact=software_name)
            except Software.DoesNotExist:
                not_found.append(software_name)
                continue

            tags = []
            for tag_name in tag_names:
                if not dry_run:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name,
                        defaults={"slug": slugify(tag_name)},
                    )
                    tags.append(tag)
                    if created:
                        self.stdout.write(f"  Created tag: {tag_name}")

            if not dry_run:
                software.tags.set(tags)
            else:
                self.stdout.write(
                    f"  {software_name}: would set tags to {tag_names or '(none)'}"
                )

            updated += 1

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Updated tags for {updated} software(s).")
            )
        else:
            self.stdout.write(f"Would update {updated} software(s).")

        if not_found:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{len(not_found)} software(s) not found in the database:"
                )
            )
            for name in not_found:
                self.stdout.write(f"  - {name}")
