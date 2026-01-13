from __future__ import annotations

import csv
import io
from typing import Iterable, Mapping

from fastapi import Response


def build_csv_response(
    rows: Iterable[Mapping[str, object]],
    fieldnames: list[str],
    filename: str,
) -> Response:
    """
    Build a CSV HTTP response from an iterable of row mappings.

    Reason: centralising CSV generation keeps endpoints focused on query logic
    and makes it easy to tweak CSV formatting or headers in a single place.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    csv_data = buffer.getvalue()

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


