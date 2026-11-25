
import html
import streamlit as st


def apply_custom_css():
    """Apply styling that follows Streamlit's selected theme."""

    st.markdown(
        """
        <style>

        :root {
            --app-bg: var(--background-color);
            --sidebar-bg: var(--secondary-background-color);
            --card-bg: var(--secondary-background-color);
            --text-color: var(--text-color);
            --secondary-color: var(--text-color);
            --border-color: var(--border-color, rgba(128, 128, 128, 0.25));
            --accent-color: var(--primary-color);
            --accent-hover: var(--primary-color);
            --input-bg: var(--secondary-background-color);
        }

        .stApp {
            background: var(--background-color);
            color: var(--text-color);
        }

        [data-testid="stSidebar"] {
            background: var(--secondary-background-color);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stMain"] {
            background: var(--background-color);
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--text-color) !important;
            font-weight: 700;
        }

        p, label, .stMarkdown,
        [data-testid="stCaptionContainer"] {
            color: var(--text-color);
        }

        .section-subtitle,
        .custom-card-title {
            color: var(--text-color) !important;
            opacity: 0.75;
        }

        [data-testid="stSidebar"] div.stButton > button {
            background: transparent;
            color: var(--text-color) !important;
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 0.55rem 1rem;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        [data-testid="stSidebar"] div.stButton > button p {
            color: var(--text-color) !important;
        }

        [data-testid="stSidebar"] div.stButton > button:hover {
            background: var(--primary-color);
            color: white !important;
            border-color: var(--primary-color);
        }

        [data-testid="stSidebar"] div.stButton > button:hover p {
            color: white !important;
        }

        div.stButton > button:hover {
            filter: brightness(1.1);
            color: white;
            transform: translateY(-1px);
        }

        [data-testid="stMetric"] {
            background: var(--secondary-background-color);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px;
        }

        [data-testid="stMetricValue"] {
            color: var(--text-color);
        }

        [data-testid="stProgressBar"] > div > div {
            background: var(--primary-color);
        }

        .custom-card {
            background: var(--secondary-background-color);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 22px;
            margin-bottom: 14px;
            transition: all 0.2s ease;
        }

        .custom-card:hover {
            border-color: var(--primary-color);
            transform: translateY(-2px);
        }

        .custom-card-title {
            font-size: 14px;
            margin-bottom: 8px;
        }

        .custom-card-value {
            color: var(--text-color);
            font-size: 28px;
            font-weight: 700;
        }

        .section-subtitle {
            font-size: 14px;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="select"] > div {
            background: var(--secondary-background-color);
            border-radius: 10px;
        }

        [data-testid="stExpander"] {
            background: var(--secondary-background-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
        }

        hr {
            border-color: var(--border-color);
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title, subtitle=None):
    """Display a reusable section heading."""

    st.subheader(title)

    if subtitle:
        st.markdown(
            f'<p class="section-subtitle">{html.escape(str(subtitle))}</p>',
            unsafe_allow_html=True,
        )


def render_metric_card(label, value):
    """Display a reusable dashboard metric card."""

    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))

    st.markdown(
        f"""
        <div class="custom-card">
            <div class="custom-card-title">{safe_label}</div>
            <div class="custom-card-value">{safe_value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_score_card(label, score):
    """Display an individual evaluation score."""

    if score is None:
        display_score = "N/A"
    else:
        display_score = f"{score:.1f}/10"

    render_metric_card(label, display_score)


def render_progress(current, total):
    """Display interview progress safely."""

    if total <= 0:
        progress = 0.0
    else:
        progress = min(max(current / total, 0.0), 1.0)

    st.progress(progress)
    st.caption(f"{current} of {total} questions completed")


def render_empty_state(title, message):
    """Display a friendly empty-state message."""

    st.info(f"**{title}**\n\n{message}")
