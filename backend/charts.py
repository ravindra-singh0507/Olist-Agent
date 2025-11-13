from __future__ import annotations
import plotly.express as px
import pandas as pd

NUM_LIKE = {"int64", "float64", "int32", "float32"}


def auto_chart(df: pd.DataFrame):
    if df is None or df.empty:
        return None
    if len(df.columns) < 2:
        return None
    # Prefer first non-numeric as x, first numeric as y
    x = None
    y = None
    for c in df.columns:
        if str(df[c].dtype) not in NUM_LIKE:
            x = c
            break
    for c in df.columns:
        if str(df[c].dtype) in NUM_LIKE:
            y = c
            break
    if x and y:
        # Choose bar if unique x small; else line
        if df[x].nunique() <= 24:
            return px.bar(df, x=x, y=y)
        else:
            return px.line(df, x=x, y=y)
    return None