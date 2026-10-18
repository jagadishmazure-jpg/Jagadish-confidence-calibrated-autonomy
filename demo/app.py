"""Thin Streamlit demo for confidence-calibrated autonomy.

All logic lives in ``calib.demo_helpers`` (stdlib, fully tested); this file
only renders. Run with ``pip install streamlit`` then
``streamlit run demo/app.py``.
"""

from __future__ import annotations


def main() -> None:
    import streamlit as st  # lazy: stdlib-only unless the demo runs

    from calib import demo_helpers
    from calib.tiers import TIERS

    st.title("Confidence-Calibrated Autonomy")
    st.caption("Meridian Mutual (fictional) — accuracy-tiered claim decisions with appeals")

    st.subheader("Accuracy tiers")
    st.table(
        [
            {"tier": t.name, "rule": t.rule_id, "amount band": f"${t.min_amount:,.0f}–${t.max_amount:,.0f}"
             if t.max_amount != float("inf") else f">${t.min_amount:,.0f}",
             "accuracy bar": t.accuracy_bar, "mode": t.mode}
            for t in TIERS
        ]
    )

    if st.button("Run scenario"):
        summary = demo_helpers.run_scenario()
        st.subheader("Scenario summary")
        st.text(demo_helpers.format_summary(summary))
        st.subheader("Calibration")
        st.table(summary["calibration"])


if __name__ == "__main__":
    main()
