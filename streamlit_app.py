"""Publica a dashboard HTML do Vila Nova dentro do Streamlit."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parent


def read_text(filename: str) -> str:
    return (ROOT / filename).read_text(encoding="utf-8")


def build_dashboard() -> str:
    html = read_text("index.html")
    css = read_text("styles.css")
    javascript = read_text("app.js")
    csv_text = read_text("vila_nova_serie_b_2026_todos_jogos.csv")
    logo = base64.b64encode((ROOT / "vila-nova-logo.png").read_bytes()).decode("ascii")

    html = html.replace(
        '<link rel="stylesheet" href="styles.css">',
        f"<style>{css}</style>",
    )
    html = html.replace(
        'src="vila-nova-logo.png"',
        f'src="data:image/png;base64,{logo}"',
    )

    embedded_data = json.dumps(csv_text, ensure_ascii=False).replace("</", "<\\/")
    embedded_script = f"""
      <script>window.__VILANOVA_CSV__ = {embedded_data};</script>
      <script>{javascript}</script>
      <script>
        (() => {{
          let lastHeight = 0;
          const syncHeight = () => {{
            const height = Math.max(
              document.body.scrollHeight,
              document.documentElement.scrollHeight
            );
            if (height === lastHeight) return;
            lastHeight = height;
            window.parent.postMessage({{
              isStreamlitMessage: true,
              type: "streamlit:setFrameHeight",
              height
            }}, "*");
          }};
          window.addEventListener("load", syncHeight);
          window.addEventListener("resize", syncHeight);
          new ResizeObserver(syncHeight).observe(document.body);
          setTimeout(syncHeight, 200);
          setTimeout(syncHeight, 900);
        }})();
      </script>
    """
    return html.replace('<script src="app.js"></script>', embedded_script)


st.set_page_config(
    page_title="Vila Nova | Painel de desempenho",
    page_icon="🐯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .stApp { background: #f5f5f3; }
      .block-container { max-width: 1536px; padding: 0 !important; }
      [data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
      iframe { display: block; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.iframe(build_dashboard(), width='stretch', height='content')
