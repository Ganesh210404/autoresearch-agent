import json
import streamlit as st
from main_langchain import run_agent

st.set_page_config(page_title="AutoResearch Agent", page_icon="🧠", layout="wide")

# ---------- Styles ----------
st.markdown("""
<style>
.block-container { padding-top: 1.2rem; }
.card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 16px;
}
.small { font-size: 13px; opacity: 0.85; }
hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 12px 0; }
</style>
""", unsafe_allow_html=True)

# ---------- Session State ----------
if "final_answer" not in st.session_state:
    st.session_state.final_answer = ""
if "thinking_log" not in st.session_state:
    st.session_state.thinking_log = []

# ---------- Header ----------
st.markdown(
    """
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
    <div>
      <div style="font-size:28px; font-weight:700;">🧠 AutoResearch Agent</div>
      <div class="small">LangChain (LCEL) + Groq + Tavily • Plan → Search → Evaluate → Refine → Synthesize</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")

# ---------- Two-panel layout ----------
left, right = st.columns([2, 1], gap="large")  # Left 2/3, Right 1/3

# =========================
# RIGHT: Thinking Log (1/3)
# =========================
with right:
    # Title row with Download button beside it
    title_col, btn_col = st.columns([2.2, 1])

    with title_col:
        st.markdown("### 🧾 Thinking Log")

    with btn_col:
        st.download_button(
            "⬇️ Download Tlog",
            data=json.dumps(st.session_state.thinking_log, indent=2),
            file_name="thinking_log.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='small'>Live internal events: plan, queries, tool calls, evaluation, synthesis</div>", unsafe_allow_html=True)
    st.markdown("<hr/>", unsafe_allow_html=True)

    logs = st.session_state.thinking_log
    if logs:
        # newest first
        for item in reversed(logs):
            t = item.get("time", "")
            step = item.get("step", "")
            data = item.get("data", None)

            with st.expander(f"{t} — {step}", expanded=False):
                if data is None:
                    st.write("—")
                elif isinstance(data, (dict, list)):
                    st.code(json.dumps(data, indent=2), language="json")
                else:
                    st.write(str(data))
    else:
        st.info("Run a question to see the thinking log.")

    st.markdown("</div>", unsafe_allow_html=True)

# ======================
# LEFT: Main UI (2/3)
# ======================
with left:
    # Question + Run controls
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Research Question")

    question = st.text_area(
        "",
        placeholder="e.g., What are the most significant quantum computing breakthroughs announced in 2025, and which companies or labs are leading them?",
        height=110,
        label_visibility="collapsed"
    )

    # Run Options neatly placed under question
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("### ⚙️ Run Options")

    opt1, opt2, opt3 = st.columns([1, 1, 1])

    with opt1:
        max_iters = st.slider("Max iterations", 1, 6, 3)
    with opt2:
        max_results = st.slider("Results per search", 1, 8, 3)
    with opt3:
        mode = st.selectbox("Mode", ["Fast", "Balanced", "Deep"], index=1)

    # Buttons row
    st.markdown("<hr/>", unsafe_allow_html=True)
    b1, b2 = st.columns([1, 1])
    run_btn = b1.button("🚀 Run Research", use_container_width=True)
    clear_btn = b2.button("🧹 Clear", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if clear_btn:
        st.session_state.final_answer = ""
        st.session_state.thinking_log = []

    # Run logic
    if run_btn:
        if not question.strip():
            st.error("Please enter a research question.")
        else:
            with st.spinner("Running agent…"):
                final_answer, thinking_log = run_agent(
                    question.strip(),
                    max_iterations=max_iters,
                    max_results=max_results,
                    mode=mode,
                )

            st.session_state.final_answer = final_answer
            st.session_state.thinking_log = thinking_log
            st.rerun()

    st.write("")

    # Final Answer panel
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### ✅ Final Answer")
    st.markdown("<hr/>", unsafe_allow_html=True)

    if st.session_state.final_answer:
        st.markdown(st.session_state.final_answer)
    else:
        st.info("Run a question to see the final answer here.")

    st.markdown("</div>", unsafe_allow_html=True)
