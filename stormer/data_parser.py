"""Parsing et stockage des données reçues depuis Arduino."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DataPoint:
    timestamp: datetime
    raw_line: str
    values: dict[str, float]


@dataclass
class SessionData:
    points: list[DataPoint] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)

    def add_line(self, line: str) -> DataPoint | None:
        line = line.strip()
        if not line:
            return None
        self.raw_lines.append(line)
        values = parse_numeric_values(line)
        if not values:
            return None
        point = DataPoint(timestamp=datetime.now(), raw_line=line, values=values)
        self.points.append(point)
        return point

    def clear(self) -> None:
        self.points.clear()
        self.raw_lines.clear()

    @property
    def sensor_names(self) -> list[str]:
        if not self.points:
            return []
        names: list[str] = []
        seen: set[str] = set()
        for point in self.points:
            for key in point.values:
                if key not in seen:
                    seen.add(key)
                    names.append(key)
        return names

    @property
    def latest_values(self) -> dict[str, float]:
        if not self.points:
            return {}
        return dict(self.points[-1].values)

    def to_dataframe(self):
        import pandas as pd

        rows = []
        for point in self.points:
            row = {"timestamp": point.timestamp, **point.values}
            rows.append(row)
        return pd.DataFrame(rows)

    def export_txt(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# Stormer — Export de session\n")
            f.write(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Lignes: {len(self.raw_lines)}\n\n")
            for line in self.raw_lines:
                f.write(line + "\n")


def parse_numeric_values(line: str) -> dict[str, float]:
    """Extrait les valeurs numériques d'une ligne Arduino."""
    line = line.strip()
    if not line or line.startswith("#"):
        return {}
    upper = line.upper()
    if "ERREUR" in upper or "ERROR" in upper or "WARN" in upper:
        return {}

    values: dict[str, float] = {}

    # Format clé:valeur ou clé=valeur
    for match in re.finditer(r"([a-zA-Z_][\w]*)\s*[:=]\s*(-?\d+(?:\.\d+)?)", line):
        values[match.group(1).lower()] = float(match.group(2))

    if values:
        return values

    # Nombres séparés par virgules ou espaces
    numbers = re.findall(r"-?\d+(?:\.\d+)?", line)
    if numbers:
        if len(numbers) == 1:
            values["valeur"] = float(numbers[0])
        else:
            for i, num in enumerate(numbers):
                values[f"capteur_{i + 1}"] = float(num)

    return values
