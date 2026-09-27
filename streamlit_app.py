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
    finance_path = ROOT / "financas_2025.js"
    finance_js = finance_path.read_text(encoding="utf-8").replace("</", "<\\/") if finance_path.exists() else ""
    simulation_path = ROOT / "simulacao_2026.js"
    simulation_js = simulation_path.read_text(encoding="utf-8").replace("</", "<\\/") if simulation_path.exists() else ""
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
        // A medição automática do st.iframe só aumenta a altura: ela usa
        // documentElement.scrollHeight, que nunca fica abaixo da altura atual do iframe.
        // Aqui medimos o conteúdo e enviamos pelo mesmo canal do Streamlit, para o
        // iframe também encolher quando uma busca ou um filtro reduz a página.
        (() => {{
          const shell = document.querySelector(".page-shell");
          let lastHeight = 0;
          const syncHeight = () => {{
            const height = Math.ceil(shell.getBoundingClientRect().height);
            if (!height || height === lastHeight) return;
            lastHeight = height;
            window.parent.postMessage({{
              type: "streamlit:iframe:setSize",
              width: document.documentElement.clientWidth,
              height
            }}, "*");
          }};
          // Sem barra de rolagem interna: ela estreitaria a página e mudaria a altura medida.
          document.documentElement.style.overflowY = "hidden";
          new ResizeObserver(syncHeight).observe(shell);
          new MutationObserver(syncHeight).observe(document.body, {{
            childList: true, subtree: true, attributes: true, characterData: true
          }});
          window.addEventListener("load", syncHeight);
          window.addEventListener("resize", syncHeight);
          // Rede de segurança para abas em segundo plano, onde o ResizeObserver fica pausado.
          setInterval(syncHeight, 1000);
        }})();
      </script>
    """
    html = html.replace('<script src="simulacao_2026.js"></script>', f"<script>{simulation_js}</script>")
    html = html.replace('<script src="financas_2025.js"></script>', f"<script>{finance_js}</script>")
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
