import json
import os
from pathlib import Path

import django
from django.test import TestCase

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "polysphere.settings")
django.setup()

from kanoodleApp.models import Piece  # noqa: E402
from kanoodleApp.util import generate_3d_orientations  # noqa: E402


def ensure_pyramid_pieces_loaded():
    """Load the bundled pyramid piece fixture if the test database is empty."""
    if Piece.objects.exists():
        return

    fixture_path = Path(__file__).resolve().parent / "kanoodleApp" / "JSONs" / "pyramid_piece_data.json"
    with open(fixture_path, "r") as f:
        data = json.load(f)

    for obj in data:
        if not obj["model"].endswith(".piece"):
            continue
        Piece.objects.create(
            id=obj["pk"],
            name=obj["fields"]["name"],
            shapeData=obj["fields"]["shapeData"],
            color=obj["fields"].get("color", "#999999"),
        )


class OrientationGenerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_pyramid_pieces_loaded()
        cls.sample_piece = Piece.objects.order_by("pk").first()

    def test_generate_unique_orientations_from_fixture_piece(self):
        self.assertIsNotNone(self.sample_piece, "No pieces available for orientation test")
        base_coords = [
            tuple(c) if len(c) == 3 else (c[0], c[1], 0)
            for c in self.sample_piece.shapeData
        ]

        orientations = list(generate_3d_orientations(base_coords))
        self.assertGreater(len(orientations), 0, "Expected at least one orientation")

        orientation_set = {tuple(shape) for shape in orientations}
        self.assertEqual(
            len(orientations),
            len(orientation_set),
            "Generated orientations should be unique",
        )
