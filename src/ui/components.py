import html
import streamlit as st


def apply_custom_css():
    """Apply the premium dark AI-studio visual theme."""

    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
            --studio-bg: #080B16;
            --studio-panel: #101629;
            --studio-panel-soft: #151D33;
            --studio-border: rgba(151, 165, 205, 0.16);
            --studio-text: #F4F6FF;
            --studio-muted: #9AA6C2;
            --studio-purple: #8B5CF6;
            --studio-blue: #4F8CFF;
        }

        .stApp {
            background:
                radial-gradient(ellipse at 12% 0%, rgba(91, 63, 180, .18), transparent 34%),
                radial-gradient(ellipse at 92% 12%, rgba(42, 105, 190, .12), transparent 30%),
                var(--studio-bg);
            color: var(--studio-text);
        }

        [data-testid="stHeader"] {
            background: rgba(8, 11, 22, .72);
        }

        [data-testid="stMain"] {
            background: transparent;
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 1440px;
            padding-top: 2.2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #10172B 0%, #0B1020 100%);
            border-right: 1px solid var(--studio-border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.5rem;
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--studio-text) !important;
            letter-spacing: -0.025em;
            font-weight: 700 !important;
        }

        h1 { font-size: clamp(2rem, 3vw, 2.7rem) !important; }
        h2 { font-size: 1.65rem !important; }
        h3 { font-size: 1.2rem !important; }

        p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
            color: var(--studio-muted);
        }

        [data-testid="stCaptionContainer"] p {
            color: var(--studio-muted) !important;
        }

        .section-subtitle,
        .custom-card-title {
            color: var(--studio-muted) !important;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #FFFFFF !important;
        }

        [data-testid="stSidebar"] div.stButton > button {
            background: transparent;
            color: #B9C4DF !important;
            border: 1px solid transparent;
            border-radius: 12px;
            padding: .68rem .9rem;
            min-height: 2.8rem;
            font-weight: 600;
            text-align: left;
            transition: background .18s ease, border-color .18s ease, transform .18s ease;
        }

        [data-testid="stSidebar"] div.stButton > button p {
            color: inherit !important;
        }

        [data-testid="stSidebar"] div.stButton > button:hover {
            background: rgba(139, 92, 246, .14);
            border-color: rgba(139, 92, 246, .3);
            color: #FFFFFF !important;
            transform: translateX(2px);
        }

        [data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: linear-gradient(105deg, #7047D8, #426FE0);
            border-color: transparent;
            color: #FFFFFF !important;
            box-shadow: 0 8px 24px rgba(93, 76, 210, .22);
        }

        div.stButton > button,
        div.stFormSubmitButton > button {
            border-radius: 11px;
            font-weight: 650;
            min-height: 2.75rem;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }

        div.stButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primary"] {
            background: linear-gradient(105deg, #7950E8 0%, #477DEB 100%);
            border: 0;
            color: #FFFFFF;
            box-shadow: 0 8px 22px rgba(91, 91, 220, .2);
        }

        div.stButton > button:hover,
        div.stFormSubmitButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 26px rgba(75, 95, 190, .2);
            border-color: rgba(139, 92, 246, .55);
        }

        [data-testid="stMetric"],
        .custom-card {
            background: linear-gradient(145deg, rgba(23, 32, 56, .96), rgba(15, 22, 40, .96));
            border: 1px solid var(--studio-border);
            border-radius: 17px;
            padding: 19px 21px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, .12);
            transition: border-color .2s ease, transform .2s ease;
        }

        .custom-card {
            margin-bottom: 14px;
        }

        [data-testid="stMetric"]:hover,
        .custom-card:hover {
            border-color: rgba(139, 92, 246, .42);
            transform: translateY(-2px);
        }

        [data-testid="stMetricLabel"],
        .custom-card-title {
            color: #AAB5D0 !important;
            font-size: .86rem;
            font-weight: 600;
        }

        [data-testid="stMetricValue"],
        .custom-card-value {
            color: #FFFFFF !important;
            font-size: 1.8rem;
            font-weight: 750;
            letter-spacing: -.035em;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="select"] > div {
            background: #111A30;
            border: 1px solid rgba(151, 165, 205, .2);
            border-radius: 11px;
            color: #F4F6FF;
        }

        input, textarea {
            color: #F4F6FF !important;
        }

        [data-testid="stFileUploader"] section {
            background: rgba(17, 26, 48, .72);
            border: 1px dashed rgba(139, 92, 246, .42);
            border-radius: 14px;
        }

        [data-testid="stTabs"] [role="tab"] {
            color: #AAB5D0;
            font-weight: 650;
        }

        [data-testid="stTabs"] [aria-selected="true"] {
            color: #FFFFFF !important;
        }

        [data-testid="stExpander"] {
            background: rgba(17, 26, 48, .78);
            border: 1px solid var(--studio-border);
            border-radius: 13px;
        }

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            border: 1px solid var(--studio-border);
            border-radius: 13px;
            overflow: hidden;
        }

        [data-testid="stProgressBar"] > div > div {
            background: linear-gradient(90deg, #8B5CF6, #4F8CFF);
        }

        [data-testid="stAlert"] {
            border-radius: 12px;
        }

        hr {
            border-color: var(--studio-border);
        }

        a {
            color: #A78BFA !important;
        }

        ::selection {
            background: rgba(139, 92, 246, .35);
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

    st.info(f"**{title}**\\n\\n{message}")
