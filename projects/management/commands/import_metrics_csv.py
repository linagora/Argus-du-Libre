"""Management command to import software analysis results from CSV."""

import csv
import sys
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from projects.models import AnalysisResult, Field, Software


class Command(BaseCommand):
    help = "Import software analysis results (scores) from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="The path to the CSV file to import")

    def handle(self, *args, **options):
        file_path = options["file"]
        self.stdout.write(self.style.SUCCESS(f"Attempting to import from {file_path}"))

        try:
            with open(file_path, "r", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader)  # Read header row

                if not header or header[0] != "software":
                    raise ValueError(
                        "Invalid CSV format: first column must be 'software'"
                    )

                field_slugs = header[1:]
                # Pre-fetch all fields to reduce database queries
                fields_map = {f.slug: f for f in Field.objects.all()}

                imported_count = 0
                skipped_softwares = 0
                skipped_scores = 0
                total_scores = 0

                for row_num, row in enumerate(reader, start=2):
                    if not row:
                        continue

                    software_slug = row[0]
                    software = Software.objects.filter(slug=software_slug).first()

                    if not software:
                        self.stderr.write(
                            self.style.WARNING(
                                f"Skipping row {row_num}: Software with slug "
                                f"'{software_slug}' not found."
                            )
                        )
                        skipped_softwares += 1
                        continue

                    # Process scores for each field
                    for i, field_slug in enumerate(field_slugs):
                        total_scores += 1
                        if i + 1 >= len(row):  # Check if score column exists
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Skipping score for '{software_slug}' and "
                                    f"field '{field_slug}' in row {row_num}: "
                                    "Missing score value."
                                )
                            )
                            skipped_scores += 1
                            continue

                        score_str = row[i + 1].strip()
                        if not score_str:  # Skip empty scores
                            continue

                        field = fields_map.get(field_slug)
                        if not field:
                            self.stderr.write(
                                self.style.ERROR(
                                    f"Skipping score for '{software_slug}' and "
                                    f"field '{field_slug}' in row {row_num}: "
                                    "Field not found."
                                )
                            )
                            skipped_scores += 1
                            continue

                        try:
                            score = Decimal(score_str)
                            if not (1 <= score <= 5):
                                raise ValueError("Score must be between 1.00 and 5.00")

                            with transaction.atomic():
                                AnalysisResult.objects.update_or_create(
                                    software=software,
                                    field=field,
                                    defaults={"score": score, "is_published": True},
                                )
                            imported_count += 1
                        except InvalidOperation:
                            self.stderr.write(
                                self.style.ERROR(
                                    f"Skipping score for '{software_slug}' and "
                                    f"field '{field_slug}' in row {row_num}: "
                                    f"Invalid score value '{score_str}'. Must be a number."
                                )
                            )
                            skipped_scores += 1
                        except ValueError as e:
                            self.stderr.write(
                                self.style.ERROR(
                                    f"Skipping score for '{software_slug}' and "
                                    f"field '{field_slug}' in row {row_num}: {e}"
                                )
                            )
                            skipped_scores += 1

                self.stdout.write(self.style.SUCCESS("Import process complete."))
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully imported/updated {imported_count} analysis results."
                    )
                )
                if skipped_softwares > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped {skipped_softwares} rows due to non-existent softwares."
                        )
                    )
                if skipped_scores > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped {skipped_scores} individual scores due to errors."
                        )
                    )
                if (
                    imported_count == 0
                    and skipped_softwares == 0
                    and skipped_scores == 0
                    and total_scores > 0
                ):
                    self.stdout.write(
                        self.style.WARNING(
                            "No scores were imported. Please check your CSV file and data."
                        )
                    )

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Error: File '{file_path}' not found."))
            sys.exit(1)
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f"Error processing CSV: {e}"))
            sys.exit(1)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            sys.exit(1)
