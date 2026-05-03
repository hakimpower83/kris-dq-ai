import streamlit as st
import streamlit.components.v1 as components
import fitz  # PyMuPDF
from openai import OpenAI
import pandas as pd
import json
import os
import base64
import html
import hashlib
from io import BytesIO


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="KRIS-DQ.ai",
    page_icon="Logo.png",
    layout="wide"
)


# ============================================================
# OPENAI API KEY
# ============================================================

def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        return api_key

    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return None


api_key = get_openai_api_key()
client = OpenAI(api_key=api_key) if api_key else None


# ============================================================
# APP SETTINGS
# ============================================================

PROMPT_VERSION = "kris-dq-published-framework-v4-ui-fixed"
MAX_ANALYSIS_CHARS = 60000
ARTICLE_URL = "https://gaexcellence.com/ijemp/article/view/7031"


# ============================================================
# KRIS-DQ PUBLISHED RISK CATEGORIES AND DEFINITIONS
# ============================================================

KRIS_RISK_DEFINITIONS = [
    {
        "category": "Business Resilience",
        "definition": "The risk of failing to adapt to disruptions, maintain critical operations, and recover effectively from crises such as pandemics, economic shocks, natural disasters, or geopolitical events. Includes governance integration and long-term preparedness."
    },
    {
        "category": "Talent Pipeline and Retention",
        "definition": "The risk of not ensuring the availability of skilled employees through recruitment, retention, and development strategies. Includes challenges from hybrid work, succession planning, and aligning workforce needs with business goals."
    },
    {
        "category": "Fraud Risk",
        "definition": "The risk of unethical or fraudulent activities due to weak controls, governance lapses, or external threats. Includes heightened risks during economic stress and evaluating fraud detection systems."
    },
    {
        "category": "Organizational Culture and Behavior",
        "definition": "The risk of poor values or ethical standards impacting decision-making, compliance, and control effectiveness. Includes challenges in hybrid work environments and use of soft control audits."
    },
    {
        "category": "Climate Change",
        "definition": "The risk of environmental impacts and sustainability challenges disrupting operations or harming reputations. Includes preparedness for climate-related risks and ESG integration."
    },
    {
        "category": "Third-Party Relationships and Supply Chain",
        "definition": "The risk of disruptions or failures in vendor relationships and supply chains. Includes vendor insolvency, geopolitical impacts, ESG considerations, and governance weaknesses."
    },
    {
        "category": "Cybersecurity and Data Privacy",
        "definition": "The risk of data breaches, cyberattacks, and privacy violations, particularly in remote or hybrid environments. Includes third-party risks and adherence to cybersecurity frameworks."
    },
    {
        "category": "Regulatory-Driven Risk",
        "definition": "The risk of non-compliance with evolving regulations at various levels, potentially leading to fines or operational disruptions. Includes proactive compliance and governance, risk, and compliance system integration."
    },
    {
        "category": "Data Management and Analytics",
        "definition": "The risk of poor data management or analysis, affecting data integrity, privacy, and decision-making. Includes ethical use of data and embedding analytics in audit or governance processes."
    },
    {
        "category": "Digital Disruption and Emerging Technologies",
        "definition": "The risk associated with adopting technologies such as artificial intelligence, robotics, automation, and digital systems. Includes governance, integration, cybersecurity risks, and long-term monitoring frameworks."
    },
    {
        "category": "Changes in Tax Landscape",
        "definition": "The risk of failing to adapt to tax changes, leading to penalties, inefficiencies, or compliance weaknesses. Includes building robust tax compliance frameworks."
    },
    {
        "category": "Evolving Compliance and Regulation",
        "definition": "The risk of inadequate systems to manage regulatory complexity. Includes legal, operational, and reputational risks, and the use of automation in compliance monitoring."
    },
    {
        "category": "ESG Reporting",
        "definition": "The risk of failing to meet ESG disclosure expectations or regulations. Includes alignment with international standards and maintaining ESG governance and metrics."
    },
    {
        "category": "Liquidity and Cash Flow Management",
        "definition": "The risk of poor cash flow or funding management, particularly during economic stress. Includes use of analytics to optimise cash and working capital."
    },
    {
        "category": "Economic and Geopolitical Uncertainty",
        "definition": "The risk of macroeconomic or geopolitical instability affecting business operations. Includes inflation, sanctions, trade tension, economic uncertainty, and capital planning implications."
    },
    {
        "category": "Mergers and Acquisitions",
        "definition": "The risk of governance, integration, or due diligence failures during corporate transactions. Includes synergy realisation and cultural integration challenges."
    },
    {
        "category": "Business Continuity and Crisis Response",
        "definition": "The risk of inadequate preparation or response to crises such as cyberattacks, pandemics, operational breakdowns, or disasters. Includes scenario planning, crisis simulation, and governance oversight."
    },
    {
        "category": "Ethical Concerns and Soft Controls",
        "definition": "The risk of weak ethical oversight affecting behaviour and decisions. Includes use of surveys, audits, reporting channels, governance mechanisms, or other tools to evaluate cultural alignment and governance gaps."
    }
]

KRIS_CATEGORIES = [item["category"] for item in KRIS_RISK_DEFINITIONS]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


def get_file_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


def normalise_bool(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in ["true", "yes", "1"]

    return bool(value)


def fix_categories(api_categories):
    fixed_results = []
    api_lookup = {}

    for item in api_categories:
        name = item.get("risk_category", "").strip()
        if name:
            api_lookup[name] = item

    for category in KRIS_CATEGORIES:
        if category in api_lookup:
            item = api_lookup[category]

            try:
                score = int(item.get("score", 0))
            except Exception:
                score = 0

            score = max(0, min(score, 4))

            evidence_found = normalise_bool(item.get("evidence_found", False))
            evidence_summary = item.get("evidence_summary", "").strip()
            summary = item.get("summary", "").strip()

            if not evidence_found or score == 0:
                evidence_found = False
                score = 0
                evidence_summary = "No clear evidence found."
                summary = "No relevant disclosure identified."

            if score > 0 and not evidence_summary:
                evidence_found = False
                score = 0
                evidence_summary = "No clear evidence found."
                summary = "No relevant disclosure identified."

            if not summary:
                summary = "No relevant disclosure identified." if score == 0 else evidence_summary

            fixed_results.append({
                "risk_category": category,
                "evidence_found": evidence_found,
                "evidence_summary": evidence_summary,
                "score": score,
                "summary": summary
            })
        else:
            fixed_results.append({
                "risk_category": category,
                "evidence_found": False,
                "evidence_summary": "No clear evidence found.",
                "score": 0,
                "summary": "No relevant disclosure identified."
            })

    return fixed_results


def score_label(score):
    labels = {
        0: "No disclosure",
        1: "Minimal",
        2: "Descriptive",
        3: "Mitigation",
        4: "Quantitative"
    }
    return labels.get(score, str(score))


def convert_df_to_excel(
    df,
    company_name,
    uploaded_file_name,
    pages_reviewed,
    total_score,
    maximum_score,
    normalized_score,
    percentage_score
):
    output = BytesIO()

    summary_df = pd.DataFrame({
        "Metric": [
            "Company Name",
            "Uploaded File",
            "Pages Reviewed",
            "Total KRIS-DQ Score",
            "Maximum Score",
            "Normalized Score",
            "Percentage Score",
            "Prompt Version",
            "Human Review Note"
        ],
        "Value": [
            company_name,
            uploaded_file_name,
            pages_reviewed,
            total_score,
            maximum_score,
            normalized_score,
            f"{percentage_score}%",
            PROMPT_VERSION,
            "KRIS-DQ.ai provides AI-assisted preliminary scoring. Final scores should be reviewed by a trained human coder, especially for academic research, regulatory use, or paid professional reports."
        ]
    })

    excel_df = df.copy()
    excel_df["Review Note"] = ""

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Score Summary")
        excel_df.to_excel(writer, index=False, sheet_name="Category Results")

    return output.getvalue()


def build_results_table(df):
    rows = ""

    for _, row in df.iterrows():
        score = int(row["KRIS-DQ Score"])

        rows += f"""
        <tr>
            <td class="col-no">{html.escape(str(row['No.']))}</td>
            <td class="col-category">{html.escape(str(row['Risk Category']))}</td>
            <td class="col-score score-{score}">{html.escape(str(row['KRIS-DQ Score']))}</td>
            <td class="col-summary">{html.escape(str(row['Summary of Disclosure']))}</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}

        .table-container {{
            width: 100%;
            overflow: auto;
            border-radius: 14px;
            border: 1px solid #334155;
            max-height: 690px;
            background: #0f172a;
        }}

        .table-container::-webkit-scrollbar {{
            height: 12px;
            width: 12px;
        }}

        .table-container::-webkit-scrollbar-thumb {{
            background: #64748b;
            border-radius: 10px;
        }}

        .table-container::-webkit-scrollbar-track {{
            background: #0b1220;
        }}

        table {{
            width: 100%;
            min-width: 1080px;
            border-collapse: collapse;
            table-layout: fixed;
            font-size: 14px;
            background: #0f172a;
            color: #e5e7eb;
        }}

        th {{
            position: sticky;
            top: 0;
            z-index: 1;
            background: #1e2a3d;
            color: #ffffff;
            padding: 13px 10px;
            text-align: left;
            border: 1px solid #334155;
            font-weight: 800;
        }}

        td {{
            padding: 13px 10px;
            border: 1px solid #334155;
            vertical-align: top;
            line-height: 1.5;
            word-wrap: break-word;
            overflow-wrap: break-word;
            white-space: normal;
            color: #cbd5e1;
        }}

        .col-no {{
            width: 50px;
            text-align: center;
        }}

        .col-category {{
            width: 235px;
            font-weight: 700;
            color: #ffffff;
        }}

        .col-score {{
            width: 56px;
            text-align: center;
            font-weight: 900;
            color: #ffffff !important;
            padding-left: 6px !important;
            padding-right: 6px !important;
        }}

        .col-summary {{
            width: 739px;
        }}

        .score-0 {{ background: #6b7280; }}
        .score-1 {{ background: #b91c1c; }}
        .score-2 {{ background: #b45309; }}
        .score-3 {{ background: #1d4ed8; }}
        .score-4 {{ background: #15803d; }}

        @media (max-width: 768px) {{
            table {{
                font-size: 13px;
                min-width: 920px;
            }}

            th, td {{
                padding: 9px 7px;
            }}

            .col-no {{ width: 44px; }}
            .col-category {{ width: 210px; }}
            .col-score {{ width: 52px; }}
            .col-summary {{ width: 614px; }}
        }}
    </style>
</head>
<body>
    <div class="table-container">
        <table>
            <colgroup>
                <col class="col-no">
                <col class="col-category">
                <col class="col-score">
                <col class="col-summary">
            </colgroup>
            <thead>
                <tr>
                    <th class="col-no">No.</th>
                    <th class="col-category">Risk Category</th>
                    <th class="col-score">Score</th>
                    <th class="col-summary">Summary of Disclosure</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
</body>
</html>
    """

def build_highlight_card(title, items, empty_message):
    if not items:
        list_items = f"<li><span class='highlight-category'>{html.escape(empty_message)}</span></li>"
    else:
        list_items = ""
        for item in items:
            category = html.escape(str(item["Risk Category"]))
            score = html.escape(str(item["KRIS-DQ Score"]))
            meaning = html.escape(str(item["Score Meaning"]))

            list_items += (
                f"<li>"
                f"<span class='highlight-category'>{category}</span>"
                f"<span class='highlight-score'>Score {score} | {meaning}</span>"
                f"</li>"
            )

    return (
        f"<div class='highlight-card'>"
        f"<div class='highlight-title'>{html.escape(title)}</div>"
        f"<ol>{list_items}</ol>"
        f"</div>"
    )

def run_openai_analysis(prompt, schema):
    try:
        response = client.responses.create(
            model="gpt-5",
            input=prompt,
            temperature=0,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "kris_dq_result",
                    "strict": True,
                    "schema": schema
                }
            }
        )
        return response

    except Exception as first_error:
        error_message = str(first_error).lower()

        if "temperature" in error_message:
            response = client.responses.create(
                model="gpt-5",
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "kris_dq_result",
                        "strict": True,
                        "schema": schema
                    }
                }
            )
            return response

        raise first_error


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --kris-page-bg: var(--background-color, #0b1220);
        --kris-page-text: var(--text-color, #f8fafc);
        --kris-muted: color-mix(in srgb, var(--text-color, #f8fafc) 68%, transparent);

        --kris-card-bg: color-mix(in srgb, var(--secondary-background-color, #111827) 92%, var(--background-color, #0b1220));
        --kris-card-border: color-mix(in srgb, var(--text-color, #f8fafc) 18%, transparent);
        --kris-card-text: var(--text-color, #f8fafc);
        --kris-card-muted: color-mix(in srgb, var(--text-color, #f8fafc) 70%, transparent);

        --kris-badge-bg: #374151;
        --kris-badge-border: #4b5563;
        --kris-badge-text: #ffffff;

        --kris-research-bg: color-mix(in srgb, #1d4ed8 18%, var(--secondary-background-color, #111827));
        --kris-research-border: color-mix(in srgb, #1d4ed8 46%, transparent);
        --kris-research-label: #60a5fa;

        --kris-step-bg: #25489f;
        --kris-step-border: #6687e8;
        --kris-step-number: #c7d7ff;
        --kris-step-title: #ffffff;
        --kris-step-text: #e5ecff;

        --kris-fixed-light-bg: #e9edf5;
        --kris-fixed-light-inner: #f7f9fc;
        --kris-fixed-light-border: #97a8c3;
        --kris-fixed-light-text: #111827;
        --kris-fixed-light-muted: #64748b;

        --kris-blue: #1d4ed8;
        --kris-blue-dark: #1e40af;
        --kris-red: #c81e1e;
        --kris-red-dark: #a4161a;
        --kris-green: #15803d;
        --kris-green-dark: #166534;
    }

    html,
    body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppMain"],
    section[data-testid="stMain"] {
        background-color: var(--kris-page-bg) !important;
        color: var(--kris-page-text) !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    .block-container {
        padding-top: 1.35rem;
        padding-bottom: 1.6rem;
        max-width: 1280px;
    }

    .logo-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 0.1rem;
        margin-bottom: 1.5rem;
    }

    .logo-banner {
        width: min(49vw, 470px);
        height: auto;
        border-radius: 14px;
    }

    .hero-main {
        padding: 26px 28px;
        border-radius: 22px;
        background: var(--kris-card-bg);
        border: 1px solid var(--kris-card-border);
        min-height: 230px;
    }

    .hero-subtitle {
        font-size: 32px;
        font-weight: 900;
        letter-spacing: -0.03em;
        margin-bottom: 0.55rem;
        color: var(--kris-card-text);
    }

    .hero-description {
        font-size: 18px;
        line-height: 1.55;
        color: var(--kris-card-muted);
        max-width: 780px;
    }

    .hero-note {
        margin-top: 0.7rem;
        font-size: 14px;
        color: var(--kris-card-muted);
    }

    .badge-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 1.15rem;
    }

    .badge {
        padding: 9px 15px;
        border-radius: 999px;
        background: var(--kris-badge-bg);
        border: 1px solid var(--kris-badge-border);
        font-size: 14px;
        font-weight: 750;
        color: var(--kris-badge-text);
    }

    .research-card {
        padding: 26px 24px;
        border-radius: 22px;
        background: var(--kris-research-bg);
        border: 1px solid var(--kris-research-border);
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 230px;
    }

    .research-label {
        font-size: 13px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--kris-research-label);
        margin-bottom: 8px;
    }

    .research-title {
        font-size: 22px;
        font-weight: 900;
        margin-bottom: 8px;
        color: var(--kris-card-text);
    }

    .research-text {
        font-size: 14px;
        line-height: 1.45;
        color: var(--kris-card-muted);
        margin-bottom: 16px;
    }

    .research-button {
        display: inline-block;
        text-align: center;
        text-decoration: none;
        padding: 11px 16px;
        border-radius: 999px;
        background: var(--kris-blue);
        border: 1px solid var(--kris-blue);
        color: #ffffff !important;
        font-size: 14px;
        font-weight: 850;
        box-shadow: none;
    }

    .research-button:hover {
        background: var(--kris-blue-dark);
        border-color: var(--kris-blue-dark);
        color: #ffffff !important;
    }

    .step-card {
        padding: 19px 24px;
        border-radius: 18px;
        background: var(--kris-step-bg);
        border: 1.5px solid var(--kris-step-border);
        min-height: 150px;
        margin-top: 34px;
    }

    .step-number {
        font-size: 13px;
        font-weight: 900;
        letter-spacing: 0.04em;
        color: var(--kris-step-number);
        margin-bottom: 5px;
    }

    .step-title {
        font-size: 22px;
        font-weight: 900;
        color: var(--kris-step-title);
        margin-bottom: 6px;
        line-height: 1.2;
    }

    .step-text {
        font-size: 15px;
        line-height: 1.42;
        color: var(--kris-step-text);
        max-width: 420px;
    }

    .upload-heading {
        text-align: center;
        font-size: 30px;
        font-weight: 900;
        margin-top: 1.45rem;
        margin-bottom: 0.2rem;
        color: var(--kris-page-text);
    }

    .upload-subheading {
        text-align: center;
        font-size: 15px;
        color: var(--kris-muted);
        margin-bottom: 1.1rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--kris-fixed-light-bg) !important;
        border: 2px solid var(--kris-fixed-light-border) !important;
        border-radius: 20px !important;
    }

    [data-testid="stFileUploader"] {
        background: var(--kris-fixed-light-inner) !important;
        border: 2px solid var(--kris-fixed-light-border) !important;
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 0.9rem;
        box-shadow: none;
    }

    [data-testid="stFileUploader"] section {
        border-radius: 13px;
        border: 1.5px dashed #4d6dd3 !important;
        background: #eef3fb !important;
        padding: 18px;
    }

[data-testid="stFileUploader"] * {
    color: #111827 !important;
}

[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] button *,
[data-testid="stFileUploader"] [role="button"],
[data-testid="stFileUploader"] [role="button"] * {
    background: #111827 !important;
    color: #ffffff !important;
    border-color: #374151 !important;
    font-weight: 800 !important;
}

[data-testid="stFileUploader"] button {
    border: 1px solid #374151 !important;
    border-radius: 12px !important;
}
/* Fix Tips expander title, arrow, hover, and opened content */
[data-testid="stExpander"] {
    background: #111827 !important;
    border: 1px solid #374151 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary {
    background: #111827 !important;
    color: #ffffff !important;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] svg {
    color: #ffffff !important;
    fill: #ffffff !important;
    font-weight: 900 !important;
    opacity: 1 !important;
}

[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:hover *,
[data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:focus * {
    color: #ffffff !important;
    background: #1f2937 !important;
    opacity: 1 !important;
}

/* Fix blue text inside Tips/info box */
[data-testid="stAlert"] {
    background: #0f2a4a !important;
    border: 1px solid #1e4f8f !important;
    border-radius: 10px !important;
}

[data-testid="stAlert"] *,
[data-testid="stAlert"] p,
[data-testid="stAlert"] div,
[data-testid="stAlert"] span {
    color: #ffffff !important;
    font-weight: 500 !important;
    opacity: 1 !important;
}
    .preview-card {
        padding: 24px;
        border-radius: 20px;
        background: var(--kris-fixed-light-bg);
        border: 2px solid var(--kris-fixed-light-border);
        min-height: 370px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
    }

    .preview-title {
        font-size: 24px;
        font-weight: 900;
        margin-bottom: 6px;
        text-align: center;
        color: var(--kris-fixed-light-text);
    }

    .preview-caption {
        font-size: 14px;
        color: var(--kris-fixed-light-muted);
        text-align: center;
        margin-bottom: 18px;
    }

    .preview-placeholder {
        width: 100%;
        padding: 54px 18px;
        border-radius: 16px;
        border: 1.5px dashed #b2bccf;
        text-align: center;
        font-size: 15px;
        color: var(--kris-fixed-light-muted);
        box-sizing: border-box;
        background: #f8fafc;
    }

    .preview-image {
        width: 100%;
        max-height: 320px;
        object-fit: contain;
        border-radius: 14px;
        background: white;
        border: 1px solid #cbd5e1;
    }

    .file-info-card {
        padding: 16px 18px;
        border-radius: 16px;
        background: var(--kris-fixed-light-inner);
        border: 1.5px solid #b3bfd1;
        margin-top: 8px;
    }

    .file-info-label {
        font-size: 13px;
        font-weight: 800;
        color: var(--kris-fixed-light-muted);
        margin-bottom: 7px;
    }

    .file-info-value {
        font-size: 16px;
        font-weight: 900;
        color: var(--kris-fixed-light-text);
        line-height: 1.35;
    }

    .stButton button,
.stButton button *,
div.stButton > button,
div.stButton > button *,
div[data-testid="stButton"] button,
div[data-testid="stButton"] button * {
    color: #ffffff !important;
    font-size: 24px !important;
    font-weight: 900 !important;
    opacity: 1 !important;
}

.stButton button,
div.stButton > button,
div[data-testid="stButton"] button {
    background: #dc1f1f !important;
    border: 1px solid #991b1b !important;
    border-radius: 18px !important;
    padding: 1.2rem 1.4rem !important;
    min-height: 68px !important;
    line-height: 1.2 !important;
    letter-spacing: 0.01em !important;
    box-shadow: none !important;
    margin-top: 12px !important;
}

.stButton button:hover,
div.stButton > button:hover,
div[data-testid="stButton"] button:hover {
    background: #c81e1e !important;
    border-color: #991b1b !important;
    color: #ffffff !important;
    transform: none !important;
    box-shadow: none !important;
}

.stButton button:hover *,
div.stButton > button:hover *,
div[data-testid="stButton"] button:hover * {
    color: #ffffff !important;
}

[data-testid="stDownloadButton"] button {
        background: var(--kris-green) !important;
        color: #ffffff !important;
        border: 1px solid var(--kris-green-dark) !important;
        border-radius: 14px !important;
        padding: 0.9rem 1.1rem !important;
        font-size: 17px !important;
        font-weight: 850 !important;
    }

    [data-testid="stDownloadButton"] button:hover {
        background: var(--kris-green-dark) !important;
        color: #ffffff !important;
    }

    .section-heading {
        font-size: 32px;
        font-weight: 900;
        margin-top: 12px;
        margin-bottom: 18px;
        color: var(--kris-page-text);
    }

    .context-card,
    .result-card,
    .highlight-card,
    .detail-note,
    .human-review-note,
    .score-guide-card {
        background: var(--kris-card-bg);
        border: 1px solid var(--kris-card-border);
        color: var(--kris-card-text);
    }

    .context-card {
        padding: 20px 22px;
        border-radius: 16px;
        min-height: 105px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin-bottom: 12px;
    }

    .context-label {
        font-size: 14px;
        font-weight: 700;
        color: var(--kris-card-muted);
        margin-bottom: 8px;
    }

    .context-value {
        font-size: 20px;
        font-weight: 750;
        line-height: 1.3;
        color: var(--kris-card-text);
    }

    .result-card {
        padding: 24px 22px;
        border-radius: 18px;
        min-height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .result-card.primary {
        background: #25489f;
        border: 1px solid #6687e8;
        color: #ffffff;
    }

    .result-label {
        font-size: 15px;
        font-weight: 700;
        color: var(--kris-card-muted);
        margin-bottom: 10px;
    }

    .result-card.primary .result-label,
    .result-card.primary .result-note {
        color: #dbeafe;
    }

    .result-value {
        font-size: 42px;
        font-weight: 900;
        line-height: 1.1;
        margin-bottom: 10px;
        color: var(--kris-card-text);
    }

    .result-card.primary .result-value {
        color: #ffffff;
    }

    .result-note {
        font-size: 14px;
        color: var(--kris-card-muted);
        line-height: 1.4;
    }

    .human-review-note {
        padding: 14px 18px;
        border-radius: 12px;
        font-size: 15px;
        line-height: 1.45;
        margin-top: 8px;
        margin-bottom: 18px;
    }

    .detail-note {
        padding: 14px 18px;
        border-radius: 12px;
        color: var(--kris-card-muted);
        font-size: 15px;
        line-height: 1.45;
        margin-top: 4px;
        margin-bottom: 18px;
    }

    .highlight-card {
        padding: 22px 24px;
        border-radius: 18px;
        min-height: 210px;
        margin-bottom: 18px;
    }

    .highlight-title {
        font-size: 20px;
        font-weight: 900;
        margin-bottom: 13px;
        color: var(--kris-card-text);
    }

    .highlight-card ol {
        margin: 0;
        padding-left: 22px;
    }

    .highlight-card li {
        margin-bottom: 12px;
        line-height: 1.35;
        color: var(--kris-card-text);
    }

    .highlight-category {
        display: block;
        font-size: 16px;
        font-weight: 750;
        color: var(--kris-card-text);
    }

    .highlight-score {
        display: block;
        margin-top: 3px;
        font-size: 13px;
        color: var(--kris-card-muted);
    }

    .score-guide-card {
        padding: 18px 20px;
        border-radius: 16px;
        margin-top: 10px;
    }

    .score-guide-card table {
        width: 100%;
        border-collapse: collapse;
    }

    .score-guide-card th,
    .score-guide-card td {
        padding: 11px 10px;
        border-bottom: 1px solid var(--kris-card-border);
        text-align: left;
    }

    .score-guide-card th {
        color: var(--kris-card-text);
        font-weight: 850;
    }

    .score-guide-card td {
        color: var(--kris-card-muted);
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 1.2rem;
        }

        .logo-banner {
            width: 88vw;
            border-radius: 12px;
        }

        .hero-subtitle {
            font-size: 25px;
        }

        .hero-description {
            font-size: 16px;
            line-height: 1.5;
        }

        .step-card {
            margin-top: 14px;
            min-height: auto;
            padding: 20px 20px;
        }

        .step-title {
            font-size: 20px;
        }

        .upload-heading {
            font-size: 24px;
        }

        .section-heading {
            font-size: 27px;
        }

        .context-card {
            min-height: 90px;
            padding: 18px;
        }

        .context-value {
            font-size: 17px;
        }

        .result-card {
            min-height: 120px;
            padding: 20px;
        }

        .result-value {
            font-size: 36px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER AND LANDING PAGE
# ============================================================

logo_path = "new_logo.png"

if os.path.exists(logo_path):
    logo_base64 = get_base64_image(logo_path)

    st.markdown(
        f'<div class="logo-wrapper">'
        f'<img class="logo-banner" src="data:image/png;base64,{logo_base64}">'
        f'</div>',
        unsafe_allow_html=True
    )
else:
    st.title("KRIS-DQ.ai")
    st.warning("new_logo.png not found. Please place new_logo.png in the same folder as app.py.")

hero_col, research_col = st.columns([1.65, 0.75])

with hero_col:
    st.markdown(
        '<div class="hero-main">'
        '<div class="hero-subtitle">AI Risk Disclosure Analyzer</div>'
        '<div class="hero-description">'
        'Upload an annual report or selected risk-related sections to generate KRIS-DQ scores, evidence summaries, and disclosure insights.'
        '</div>'
        '<div class="hero-note">'
        'Built on the published KRIS-DQ framework for structured risk disclosure assessment.'
        '</div>'
        '<div class="badge-row">'
        '<div class="badge">Research-Based Framework</div>'
        '<div class="badge">18 Risk Categories</div>'
        '<div class="badge">AI-Assisted Evidence Review</div>'
        '<div class="badge">Excel Output</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

with research_col:
    st.markdown(
        f'<div class="research-card">'
        f'<div class="research-label">Research Foundation</div>'
        f'<div class="research-title">Published KRIS-DQ Framework</div>'
        f'<div class="research-text">'
        f'Read the article behind the KRIS-DQ Index and its 18 risk disclosure categories.'
        f'</div>'
        f'<a class="research-button" href="{ARTICLE_URL}" target="_blank">'
        f'Read KRIS-DQ Article'
        f'</a>'
        f'</div>',
        unsafe_allow_html=True
    )

if client is None:
    st.warning(
        "OpenAI API key not found. Please set your API key as an environment variable named OPENAI_API_KEY "
        "or add it to Streamlit secrets."
    )


# ============================================================
# HOW IT WORKS
# ============================================================

how_col1, how_col2, how_col3 = st.columns(3)

with how_col1:
    st.markdown(
        '<div class="step-card">'
        '<div class="step-number">STEP 1</div>'
        '<div class="step-title">Upload report</div>'
        '<div class="step-text">Upload an annual report or selected risk-related sections in PDF format.</div>'
        '</div>',
        unsafe_allow_html=True
    )

with how_col2:
    st.markdown(
        '<div class="step-card">'
        '<div class="step-number">STEP 2</div>'
        '<div class="step-title">Detect evidence</div>'
        '<div class="step-text">The system reviews the text using the fixed KRIS-DQ risk categories and scoring rules.</div>'
        '</div>',
        unsafe_allow_html=True
    )

with how_col3:
    st.markdown(
        '<div class="step-card">'
        '<div class="step-number">STEP 3</div>'
        '<div class="step-title">Get scores</div>'
        '<div class="step-text">Generate category-level scores, evidence summaries, disclosure insights, and Excel output.</div>'
        '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# FILE UPLOAD
# ============================================================

st.markdown(
    """
    <div class="upload-heading">Upload Your Report</div>
    <div class="upload-subheading">PDF only. Selected risk-related sections are recommended for better focus and accuracy.</div>
    """,
    unsafe_allow_html=True
)

upload_col, preview_col = st.columns([1.45, 0.75])

analyze = False
analysis_status_area = None

pdf = None
pdf_bytes = None
file_hash = None

with upload_col:
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Upload Annual Report or Selected Risk-Related Sections",
            type="pdf",
            label_visibility="collapsed"
        )

        with st.expander("Tips for better results"):
            st.info(
                "For best results, it is highly recommended to upload selected risk-related sections "
                "rather than a full annual report. Suitable sections include SORMIC, MD&A, "
                "Sustainability Statement, CG Report, AC Report, RMC Report, Directors' Report, "
                "and other risk management or governance-related sections. Full annual reports are accepted, "
                "but they may contain substantial non-risk content such as financial statements, notes, "
                "corporate information, repeated headers, and administrative pages, which can reduce focus "
                "and affect scoring accuracy."
            )

        if uploaded_file is not None:
            pdf_bytes = uploaded_file.getvalue()
            file_hash = get_file_hash(pdf_bytes)
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

            st.success("PDF uploaded successfully.")

            info_col1, info_col2 = st.columns(2)

            with info_col1:
                st.markdown(
                    f'<div class="file-info-card">'
                    f'<div class="file-info-label">File Name</div>'
                    f'<div class="file-info-value">{html.escape(uploaded_file.name)}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            with info_col2:
                st.markdown(
                    f'<div class="file-info-card">'
                    f'<div class="file-info-label">Total Pages</div>'
                    f'<div class="file-info-value">{len(pdf)}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            analyze = st.button("Generate KRIS-DQ Analysis", use_container_width=True)
            analysis_status_area = st.empty()

with preview_col:
    if uploaded_file is not None and pdf is not None:
        page = pdf[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(0.48, 0.48))
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode()

        st.markdown(
            f'<div class="preview-card">'
            f'<div class="preview-title">First Page Preview</div>'
            f'<div class="preview-caption">For upload confirmation only.</div>'
            f'<img class="preview-image" src="data:image/png;base64,{img_base64}">'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="preview-card">'
            '<div class="preview-title">First Page Preview</div>'
            '<div class="preview-caption">Your uploaded PDF will appear here.</div>'
            '<div class="preview-placeholder">No PDF uploaded yet.</div>'
            '</div>',
            unsafe_allow_html=True
        )


# ============================================================
# MAIN APP LOGIC
# ============================================================

if uploaded_file is not None and analyze:
    if client is None:
        st.error(
            "Analysis cannot run because the OpenAI API key is missing. "
            "Please set OPENAI_API_KEY before running the app."
        )
        st.stop()

    try:
        status_container = analysis_status_area if analysis_status_area is not None else st

        with status_container.status("Generating KRIS-DQ analysis...", expanded=True) as status:
            st.write("Extracting PDF text...")

            full_text = ""

            for i in range(len(pdf)):
                full_text += pdf[i].get_text() + "\n\n"

            text_sample = full_text[:MAX_ANALYSIS_CHARS]

            st.write("Preparing KRIS-DQ risk definitions...")

            risk_definitions_text = "\n\n".join(
                [
                    f"{i + 1}. {item['category']}\nDefinition: {item['definition']}"
                    for i, item in enumerate(KRIS_RISK_DEFINITIONS)
                ]
            )

            schema = {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "company_name": {
                        "type": "string"
                    },
                    "categories": {
                        "type": "array",
                        "minItems": 18,
                        "maxItems": 18,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "risk_category": {
                                    "type": "string",
                                    "enum": KRIS_CATEGORIES
                                },
                                "evidence_found": {
                                    "type": "boolean"
                                },
                                "evidence_summary": {
                                    "type": "string"
                                },
                                "score": {
                                    "type": "integer",
                                    "enum": [0, 1, 2, 3, 4]
                                },
                                "summary": {
                                    "type": "string"
                                }
                            },
                            "required": [
                                "risk_category",
                                "evidence_found",
                                "evidence_summary",
                                "score",
                                "summary"
                            ]
                        }
                    }
                },
                "required": ["company_name", "categories"]
            }

            prompt = f"""
You are an expert analyst in corporate risk disclosure, corporate governance, annual report analysis, content analysis, and KRIS-DQ Index scoring.

Analyze the following annual report text using the published KRIS-DQ Index framework developed for Malaysian public-listed companies.

Your task is to assess the presence and quality of risk-related disclosures across the 18 fixed KRIS-DQ key risk areas.

Use the KRIS-DQ Index exactly as defined below. Do not use alternative risk categories, alternative labels, alternative spellings, or broader generic ESG or risk taxonomies.

KRIS-DQ definition of risk disclosure:
Risk disclosure refers to the communication of threats, uncertainties, and exposures that may negatively impact a company's financial position, operations, or sustainability, together with the measures taken to mitigate, control, monitor, or manage these risks.

Scoring philosophy:
Use a conservative medium-moderate scoring approach. Risk disclosure must be clearly stated in the annual report text before it can be scored. Do not infer, assume, or over-interpret vague language. If the evidence is unclear, indirect, weak, or only implied, choose the lower score.

Company identification:
First, identify the main reporting company or group name from the annual report text.
Return the official reporting company or group name as "company_name".
If the company name cannot be identified, return "Not identified".
Do not use the name of subsidiaries, auditors, banks, customers, suppliers, projects, hotels, directors, shareholders, or unrelated companies as the company_name.

KRIS-DQ key risk areas and definitions:
{risk_definitions_text}

Scoring guide:
0 = No disclosure
1 = Minimal coverage, vague or generic references to risk with little detail
2 = Descriptive disclosure, where the impact of the risk is evident
3 = Explanation of mitigation strategies, plans, controls, or strategies to mitigate or eliminate the risk
4 = Inclusion of quantitative information, either in monetary terms or actual physical quantities

Apply this exact evidence-first scoring process for every category:

Step 1: Identify evidence.
For each risk category, first look for explicit annual report evidence that matches the risk definition.
Evidence may appear in sections such as MD&A, SORMIC, CG Report, Sustainability Statement, AC Report, RMC Report, Directors' Report, Notes to the Financial Statements, or any risk-related section.

Step 2: Determine availability.
If no clear evidence is found, set evidence_found to false, assign score 0, write evidence_summary as "No clear evidence found.", and write summary as "No relevant disclosure identified."

Step 3: Apply score 1.
Assign score 1 only when the risk is mentioned briefly, generally, symbolically, or in boilerplate form, with little or no company-specific explanation.

Step 4: Apply score 2.
Assign score 2 when the disclosure explains the risk, exposure, consequence, or impact on the company's business, operations, financial performance, compliance position, sustainability, reputation, or stakeholders.

Step 5: Apply score 3.
Assign score 3 when the disclosure explains plans, controls, policies, governance actions, monitoring activities, response mechanisms, or strategies used to manage, mitigate, reduce, control, or eliminate the risk.
Generic statements about having a board, committee, policy, internal control system, risk management framework, or governance structure should not automatically receive score 3 unless they are clearly linked to the specific KRIS-DQ risk category being assessed.

Step 6: Apply score 4.
Assign score 4 only when the disclosure includes quantitative information directly related to the risk category.
Quantitative information may include monetary amounts, percentages, ratios, physical quantities, counts, volumes, timelines, targets, incident numbers, training hours, emission data, liquidity figures, compliance statistics, or other measurable indicators.
Do not assign score 4 merely because the annual report contains general financial numbers.
General revenue, profit, assets, liabilities, employee count, ESG performance numbers, or operational statistics should not qualify for score 4 unless they directly explain the risk exposure, impact, mitigation, target, trend, or outcome for the specific risk category.
The quantitative information must directly improve the quality of the specific risk disclosure.

Consistency and tie-breaking rules:
- Apply the same scoring standard to all 18 categories.
- If a disclosure sits between two scores, choose the lower score.
- If a disclosure is vague, implied, indirect, or not clearly linked to the risk category, choose the lower score.
- Do not score based on the severity or importance of the risk. Score only the quality of disclosure.
- Do not reward repeated headings, contents pages, repeated phrases, or generic claims.
- Do not repeat the same evidence across many categories unless the annual report clearly links that evidence to multiple distinct risks.
- If one disclosure could fit several categories, assign it to the most relevant category and avoid double counting.
- Do not invent information not found in the annual report text.
- Do not use external knowledge about the company.
- Do not assume that a company faces a risk merely because of its industry.
- Do not treat normal business descriptions as risk disclosure unless the negative exposure, uncertainty, threat, or mitigation is clearly stated.
- Do not treat generic sustainability, governance, or financial statements as risk disclosure unless they are clearly linked to one of the 18 KRIS-DQ risk areas.

Evidence summary requirement:
For each category, evidence_summary must briefly explain the actual evidence found in the report that supports the score.
If possible, mention the type of section where the evidence appears, but do not guess the section if it is not clear.
Do not provide long quotations.
If no evidence is found, write exactly "No clear evidence found."

Summary requirement:
For each category, provide a concise but useful summary that:
- identifies the risk disclosed;
- explains the disclosed impact, exposure, or relevance to the company;
- mentions mitigation, response, governance action, control, monitoring activity, or management strategy where available;
- includes quantitative information only where disclosed;
- supports the score assigned;
- uses "No relevant disclosure identified." if the category is not discussed.

Before finalising the output, internally check that:
- all 18 KRIS-DQ categories are included exactly once;
- each category name is exactly the same as the KRIS-DQ category list above;
- each score follows the 0 to 4 criteria;
- evidence_summary supports the assigned score;
- score 3 is not assigned based only on generic governance or internal control statements;
- score 4 is only used where specific quantitative information is present and directly linked to the specific risk category;
- unclear cases are scored conservatively;
- the total scoring approach is consistent across all categories.

Important output rules:
- Return valid JSON only.
- Do not include markdown.
- Do not include explanations outside the JSON.
- Do not include comments before or after the JSON.
- Return exactly one JSON object.
- Return the company_name and exactly 18 category objects.
- Use each KRIS-DQ category exactly once.
- Use the exact category names provided.
- Do not combine categories.
- Do not rename categories.
- Do not create new categories.
- Score must be an integer from 0 to 4.
- evidence_found must be true or false.

The JSON must follow this exact structure:

{{
  "company_name": "Company name here",
  "categories": [
    {{
      "risk_category": "Business Resilience",
      "evidence_found": true,
      "evidence_summary": "Brief evidence from the report that supports the score.",
      "score": 3,
      "summary": "Brief user-facing summary here."
    }}
  ]
}}

Annual report text:
{text_sample}
"""

            st.write("Applying KRIS-DQ scoring framework...")

            if "analysis_cache" not in st.session_state:
                st.session_state["analysis_cache"] = {}

            cache_key = f"{PROMPT_VERSION}_{file_hash}_{MAX_ANALYSIS_CHARS}"

            if cache_key in st.session_state["analysis_cache"]:
                data = st.session_state["analysis_cache"][cache_key]
                used_cached_result = True
            else:
                response = run_openai_analysis(prompt, schema)
                data = json.loads(response.output_text)

                st.session_state["analysis_cache"][cache_key] = data
                used_cached_result = False

            st.write("Preparing dashboard and Excel output...")

            company_name = data.get("company_name", "Not identified").strip()
            if not company_name:
                company_name = "Not identified"

            fixed_categories = fix_categories(data.get("categories", []))

            total_score = sum(item["score"] for item in fixed_categories)
            maximum_score = 72
            normalized_score = round(total_score / maximum_score, 2)
            percentage_score = round((total_score / maximum_score) * 100, 1)

            status.update(
                label="KRIS-DQ analysis complete.",
                state="complete",
                expanded=False
            )

        if used_cached_result:
            st.caption(
                "Consistency note: this result was reused from the same uploaded PDF during the current session."
            )

        st.markdown(
            """
            <div class="human-review-note">
            KRIS-DQ.ai provides AI-assisted preliminary scoring. Results should be reviewed by a trained user before being used for academic, regulatory, or professional purposes.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="section-heading">
            Analysis Context
            </div>
            """,
            unsafe_allow_html=True
        )

        context_col1, context_col2, context_col3 = st.columns(3)

        with context_col1:
            st.markdown(
                f"""
                <div class="context-card">
                    <div class="context-label">Company Analysed</div>
                    <div class="context-value">{html.escape(company_name)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with context_col2:
            st.markdown(
                f"""
                <div class="context-card">
                    <div class="context-label">Uploaded File</div>
                    <div class="context-value">{html.escape(uploaded_file.name)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with context_col3:
            st.markdown(
                f"""
                <div class="context-card">
                    <div class="context-label">Pages Reviewed</div>
                    <div class="context-value">{len(pdf)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            """
            <div class="section-heading">
            KRIS-DQ Score Summary
            </div>
            """,
            unsafe_allow_html=True
        )

        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

        with summary_col1:
            st.markdown(
                f"""
                <div class="result-card primary">
                    <div class="result-label">Overall KRIS-DQ Percentage</div>
                    <div class="result-value">{percentage_score}%</div>
                    <div class="result-note">Normalized score: {normalized_score}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with summary_col2:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">Total Score</div>
                    <div class="result-value">{total_score}</div>
                    <div class="result-note">Raw score out of 72</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with summary_col3:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">Maximum Score</div>
                    <div class="result-value">{maximum_score}</div>
                    <div class="result-note">18 categories x 4 points</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with summary_col4:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">Categories Checked</div>
                    <div class="result-value">18 / 18</div>
                    <div class="result-note">Published KRIS-DQ categories reviewed</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("---")

        df = pd.DataFrame(fixed_categories)

        df.insert(0, "No.", range(1, len(df) + 1))
        df["evidence_found_display"] = df["evidence_found"].apply(
            lambda x: "Yes" if x else "No"
        )
        df["score_meaning"] = df["score"].apply(score_label)

        df = df[
            [
                "No.",
                "risk_category",
                "evidence_found_display",
                "score",
                "score_meaning",
                "evidence_summary",
                "summary"
            ]
        ]

        df.columns = [
            "No.",
            "Risk Category",
            "Evidence Found",
            "KRIS-DQ Score",
            "Score Meaning",
            "Evidence Summary",
            "Summary of Disclosure"
        ]

        st.markdown(
            """
            <div class="section-heading">
            Disclosure Highlights
            </div>
            """,
            unsafe_allow_html=True
        )

        top_df = df[df["KRIS-DQ Score"] > 0].sort_values(
            by=["KRIS-DQ Score", "Risk Category"],
            ascending=[False, True]
        ).head(3)

        weakest_df = df.sort_values(
            by=["KRIS-DQ Score", "Risk Category"],
            ascending=[True, True]
        ).head(3)

        highlight_col1, highlight_col2 = st.columns(2)

        with highlight_col1:
            st.markdown(
                build_highlight_card(
                    "Top Disclosed Risk Areas",
                    top_df.to_dict("records"),
                    "No disclosed risk area identified."
                ),
                unsafe_allow_html=True
            )

        with highlight_col2:
            st.markdown(
                build_highlight_card(
                    "Weakest Disclosed Risk Areas",
                    weakest_df.to_dict("records"),
                    "No weak category identified."
                ),
                unsafe_allow_html=True
            )

        st.markdown("---")

        st.subheader("Category-Level KRIS-DQ Results")

        st.markdown(
            """
            <div class="detail-note">
            A simplified summary is shown below for easier review. Download the full Excel file for evidence found, score meaning, evidence summary, detailed category results, and review notes.
            </div>
            """,
            unsafe_allow_html=True
        )

        results_table = build_results_table(df)

        components.html(
            results_table,
            height=720,
            scrolling=True
        )

        excel_file = convert_df_to_excel(
            df,
            company_name,
            uploaded_file.name,
            len(pdf),
            total_score,
            maximum_score,
            normalized_score,
            percentage_score
        )

        st.download_button(
            label="Download Full KRIS-DQ Results as Excel",
            data=excel_file,
            file_name="KRIS_DQ_Results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.caption(
            "Validation check: 18 out of 18 published KRIS-DQ categories displayed. "
            "Scores are AI-assisted preliminary estimates and should be reviewed by the user. "
            "Detailed evidence is available in the downloaded Excel file."
        )

        st.markdown("---")

        st.subheader("Scoring Interpretation")

        st.markdown(
            """
            <div class="score-guide-card">
            <table>
                <thead>
                    <tr>
                        <th>Score</th>
                        <th>Interpretation</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>0</td><td>No disclosure</td></tr>
                    <tr><td>1</td><td>Minimal coverage, vague or generic references to risk with little detail</td></tr>
                    <tr><td>2</td><td>Descriptive disclosure, where the impact of the risk is evident</td></tr>
                    <tr><td>3</td><td>Explanation of mitigation strategies, plans, controls, or strategies to mitigate or eliminate the risk</td></tr>
                    <tr><td>4</td><td>Inclusion of quantitative information, either in monetary terms or actual physical quantities</td></tr>
                </tbody>
            </table>
            </div>
            """,
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error("Something went wrong during analysis.")
        st.write(e)
