"""Analyse et previsions horaires — tendance + cycle jour/nuit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score

from stormer.config import MEASURE_INTERVAL_SEC, PREDICTION_HOURS
from stormer.data_parser import SessionData
from stormer.sensors import meta, prediction_kind

MIN_POINTS = 5

# Amplitude typique du cycle jour/nuit (interieur / local)
_DIURNAL_CFG: dict[str, dict[str, float]] = {
    "temp": {"amp": 2.8, "peak": 15.0},
    "probe": {"amp": 2.5, "peak": 15.0},
    "hum": {"amp": 12.0, "peak": 5.0},   # plus humide la nuit
    "soil": {"amp": 4.0, "peak": 6.0},
    "press": {"amp": 2.0, "peak": 10.0},
}


@dataclass
class HourlyForecast:
    hour_label: str
    value: float
    hours_ahead: int


@dataclass
class SensorAnalysis:
    name: str
    display_name: str
    unit: str
    count: int
    current: float
    mean: float
    trend: str
    trend_icon: str
    hourly: list[HourlyForecast]
    history: list[float]
    confidence_pct: int


@dataclass
class AnalysisResult:
    summary: str
    sensors: list[SensorAnalysis]
    alerts: list[str]
    ok: bool = True


_KIND_LIMITS = {
    "temp": (-10.0, 55.0, 1.2),
    "percent": (0.0, 100.0, 6.0),
    "generic": (None, None, 15.0),
}


def _sensor_meta(name: str) -> tuple[str, str]:
    info = meta(name)
    return info["display"], info["unit"]


def _trend_icon(trend: str) -> str:
    return {"croissante": "↗", "decroissante": "↘", "stable": "→"}[trend]


def _median_interval_sec(timestamps: pd.Series) -> float:
    if len(timestamps) < 2:
        return float(MEASURE_INTERVAL_SEC)
    deltas = timestamps.diff().dropna().dt.total_seconds()
    if deltas.empty:
        return float(MEASURE_INTERVAL_SEC)
    return float(max(deltas.median(), 1.0))


def _denoise(values: np.ndarray) -> np.ndarray:
    if len(values) < 5:
        return values.astype(float)
    return pd.Series(values.astype(float)).rolling(3, center=True, min_periods=1).median().to_numpy()


def _hour_decimal(ts: datetime | pd.Timestamp) -> float:
    return ts.hour + ts.minute / 60.0 + ts.second / 3600.0


def _diurnal_factor(hour: float, peak: float) -> float:
    """+1 au pic, -1 environ 12 h plus tard."""
    return float(np.cos(2 * np.pi * (hour - peak) / 24.0))


def _diurnal_amplitude(sensor: str, values: np.ndarray) -> float:
    cfg = _DIURNAL_CFG.get(sensor.lower())
    if not cfg:
        return 0.0
    base = float(cfg["amp"])
    std = float(np.std(values))
    if std < 0.15:
        return base
    return float(np.clip(max(base, std * 1.8), base * 0.6, base * 1.8))


def _diurnal_hourly(
    current: float,
    now: datetime,
    hours: int,
    sensor: str,
    values: np.ndarray,
) -> list[float] | None:
    cfg = _DIURNAL_CFG.get(sensor.lower())
    if not cfg:
        return None

    amp = _diurnal_amplitude(sensor, values)
    peak = float(cfg["peak"])
    cur_h = _hour_decimal(now)
    factor_now = _diurnal_factor(cur_h, peak)

    preds: list[float] = []
    for h in range(1, hours + 1):
        fut_h = cur_h + h
        factor_fut = _diurnal_factor(fut_h, peak)
        preds.append(current + amp * (factor_fut - factor_now))
    return preds


def _build_features(
    t_hours: np.ndarray,
    timestamps: pd.Series,
) -> np.ndarray:
    clock = np.array([_hour_decimal(ts) for ts in timestamps], dtype=float)
    angle = 2 * np.pi * clock / 24.0
    return np.column_stack([
        t_hours,
        np.sin(angle),
        np.cos(angle),
    ])


def _ridge_with_time(
    t_hours: np.ndarray,
    timestamps: pd.Series,
    values: np.ndarray,
    hours: int,
) -> list[float]:
    x = _build_features(t_hours, timestamps)
    y = values.astype(float)
    model = Ridge(alpha=max(0.4, 1.5 / len(y)))
    model.fit(x, y)

    last_t = float(t_hours[-1])
    last_clock = _hour_decimal(timestamps.iloc[-1])
    preds: list[float] = []
    for h in range(1, hours + 1):
        fut_t = last_t + h
        fut_clock = last_clock + h
        angle = 2 * np.pi * fut_clock / 24.0
        row = np.array([[fut_t, np.sin(angle), np.cos(angle)]])
        preds.append(float(model.predict(row)[0]))
    return preds


def _trend_hourly(
    values: np.ndarray,
    timestamps: pd.Series,
    hours: int,
    interval_sec: float,
) -> list[float]:
    y = values.astype(float)
    current = float(y[-1])
    w = min(len(y), 20)
    elapsed_h = max((w - 1) * interval_sec / 3600.0, interval_sec / 3600.0)
    slope = (float(y[-1]) - float(y[-w])) / elapsed_h

    preds: list[float] = []
    for h in range(1, hours + 1):
        damp = 0.88 ** h
        preds.append(current + slope * h * damp)
    return preds


def _blend_three(a: list[float], b: list[float], c: list[float], wa: float, wb: float) -> list[float]:
    wc = max(0.0, 1.0 - wa - wb)
    return [wa * x + wb * y + wc * z for x, y, z in zip(a, b, c, strict=True)]


def _clip_kind(values: list[float], kind: str) -> list[float]:
    lo, hi, _ = _KIND_LIMITS.get(kind, _KIND_LIMITS["generic"])
    out: list[float] = []
    for v in values:
        val = v
        if lo is not None:
            val = max(lo, val)
        if hi is not None:
            val = min(hi, val)
        out.append(round(val, 1))
    return out


def _confidence(values: np.ndarray, t_hours: np.ndarray, timestamps: pd.Series, preds: list[float]) -> int:
    n = len(values)
    if n < 3:
        return 35
    x = _build_features(t_hours, timestamps)
    model = Ridge(alpha=1.0)
    model.fit(x, values)
    try:
        r2 = max(0.0, float(r2_score(values, model.predict(x))))
    except ValueError:
        r2 = 0.0
    variation = float(np.std(preds)) if len(preds) > 1 else 0.0
    has_curve = 1.0 if variation > 0.25 else 0.4
    score = 32 + n * 2.0 + r2 * 30 + has_curve * 15
    return int(np.clip(score, 32, 92))


def _trend_from_preds(current: float, preds: list[float], kind: str) -> str:
    if not preds:
        return "stable"
    delta = preds[-1] - current
    threshold = 0.4 if kind == "temp" else 2.0 if kind == "percent" else 1.0
    if abs(delta) < threshold:
        return "stable"
    return "croissante" if delta > 0 else "decroissante"


def _predict_hourly(
    values: np.ndarray,
    timestamps: pd.Series,
    hours: int,
    kind: str = "temp",
    sensor: str = "temp",
    now: datetime | None = None,
) -> tuple[list[float], str, int]:
    now = now or datetime.now()
    y = _denoise(values)
    n = len(y)
    current = float(y[-1])

    interval = _median_interval_sec(timestamps)
    t_hours = (timestamps - timestamps.iloc[0]).dt.total_seconds().to_numpy(dtype=float) / 3600.0
    data_span_h = max(float(t_hours[-1]), interval / 3600.0)

    trend = _trend_hourly(y, timestamps.reset_index(drop=True), hours, interval)
    diurnal = _diurnal_hourly(current, now, hours, sensor, y)

    if n >= 8:
        ridge = _ridge_with_time(t_hours, timestamps.reset_index(drop=True), y, hours)
        if diurnal:
            w_diur = 0.45 if data_span_h < 0.25 else 0.35
            w_ridge = 0.35 if data_span_h < 0.25 else 0.45
            merged = _blend_three(ridge, diurnal, trend, w_ridge, w_diur)
        else:
            merged = _blend_three(ridge, trend, trend, 0.65, 0.35)
    elif diurnal:
        merged = _blend_three(diurnal, trend, trend, 0.55, 0.30)
    else:
        merged = trend

    # Ancrage : la 1re heure reste proche de la mesure actuelle + tendance immediate
    if merged:
        merged[0] = current + (merged[0] - current) * 0.85
        step_max = _KIND_LIMITS.get(kind, _KIND_LIMITS["generic"])[2]
        for i in range(1, len(merged)):
            merged[i] = float(np.clip(merged[i], merged[i - 1] - step_max, merged[i - 1] + step_max))

    preds = _clip_kind(merged, kind)
    trend_label = _trend_from_preds(current, preds, kind)
    score = _confidence(y, t_hours, timestamps.reset_index(drop=True), preds)
    return preds, trend_label, score


def analyze_session(session: SessionData, hours: int = PREDICTION_HOURS) -> AnalysisResult:
    n = len(session.points)
    if n < MIN_POINTS:
        return AnalysisResult(
            summary=f"{n}/{MIN_POINTS} mesures",
            sensors=[],
            alerts=[f"Attendez encore {MIN_POINTS - n} mesure(s) (~{(MIN_POINTS - n) * 2}s)."],
            ok=False,
        )

    df = session.to_dataframe()
    sensors: list[SensorAnalysis] = []
    alerts: list[str] = []
    ref_time = pd.Timestamp(df["timestamp"].iloc[-1]).to_pydatetime() if not df.empty else datetime.now()

    for col in session.sensor_names:
        if col not in df.columns:
            continue
        mask = df[col].notna()
        series = df.loc[mask, col].astype(float)
        timestamps = df.loc[mask, "timestamp"]
        if len(series) >= MIN_POINTS:
            sensors.append(_analyze_sensor(col, series, timestamps, hours, ref_time))
            alerts.extend(_generate_alerts(sensors[-1]))

    if not sensors:
        return AnalysisResult(
            summary="Aucune donnee",
            sensors=[],
            alerts=["Format attendu : temp:23.5,hum:45.0,soil:62,rain:0"],
            ok=False,
        )

    temp = next((s for s in sensors if s.name.lower() == "temp"), None)
    rain = next((s for s in sensors if s.name.lower() == "rain"), None)
    if rain and rain.current >= 35:
        summary = f"Pluie detectee ({rain.current:.0f}%)"
    elif temp and temp.hourly:
        nxt = temp.hourly[0].value
        delta = nxt - temp.current
        if abs(delta) < 0.3:
            summary = f"{temp.current:.0f}{temp.unit} · cycle jour/nuit estime"
        else:
            arrow = "↗" if delta > 0 else "↘"
            summary = f"{temp.current:.0f}{temp.unit} · {arrow} ~{nxt:.0f}{temp.unit} a {temp.hourly[0].hour_label}"
    else:
        s0 = sensors[0]
        summary = f"{s0.current:.0f}{s0.unit}" if s0.unit else f"{s0.display_name} : {s0.current:.0f}"

    return AnalysisResult(summary=summary, sensors=sensors, alerts=alerts, ok=True)


def _analyze_sensor(
    name: str,
    series: pd.Series,
    timestamps: pd.Series,
    hours: int,
    now: datetime,
) -> SensorAnalysis:
    raw = series.values.astype(float)
    n = len(raw)
    ts = timestamps.reset_index(drop=True)

    preds, trend, score = _predict_hourly(
        raw, ts, hours,
        kind=prediction_kind(name),
        sensor=name.lower(),
        now=now,
    )
    display_name, unit = _sensor_meta(name)

    hourly: list[HourlyForecast] = []
    for h, val in enumerate(preds, 1):
        t = now + timedelta(hours=h)
        hourly.append(HourlyForecast(
            hour_label=t.strftime("%Hh"),
            value=val,
            hours_ahead=h,
        ))

    return SensorAnalysis(
        name=name,
        display_name=display_name,
        unit=unit,
        count=n,
        current=round(float(raw[-1]), 1),
        mean=round(float(np.mean(raw)), 1),
        trend=trend,
        trend_icon=_trend_icon(trend),
        hourly=hourly,
        history=[round(float(v), 1) for v in raw.tolist()],
        confidence_pct=score,
    )


def _generate_alerts(analysis: SensorAnalysis) -> list[str]:
    alerts: list[str] = []
    name = analysis.name.lower()
    if name == "temp" and analysis.current > 35:
        alerts.append("Temperature elevee.")
    if name == "hum" and analysis.current > 80:
        alerts.append("Humidite air elevee.")
    if name == "soil" and analysis.current < 20:
        alerts.append("Sol sec — arrosage conseille.")
    if name == "soil" and analysis.current > 85:
        alerts.append("Sol tres humide.")
    if name == "rain" and analysis.current >= 35:
        alerts.append("Pluie detectee sur le capteur.")
    if name == "rain" and analysis.current >= 70:
        alerts.append("Forte pluie — proteger le materiel.")
    return alerts
