import streamlit as st
import streamlit.components.v1 as components
import fitz  # PyMuPDF
from openai import OpenAI
import pandas as pd
import json
import os
import base64
import html
from io import BytesIO

st.set_page_config(
    page_title="KRIS-DQ.ai",
    page_icon="Logo.png",
    layout="wide"
)


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

KRIS_CATEGORIES = [
    "Business Resilience",
    "Liquidity and Cash Flow Management",
    "Business Continuity and Crisis Response",
    "Cybersecurity and Data Privacy",
    "Climate Change",
    "ESG Reporting",
    "Digital Disruption and Emerging Technologies",
    "Data Management and Analytics",
    "Organisational Culture and Behaviour",
    "Talent Management and Human Capital",
    "Regulatory and Compliance Change",
    "Changes in the Tax Landscape",
    "Geopolitical and Macroeconomic Uncertainty",
    "Supply Chain Disruption",
    "Third-Party and Outsourcing Dependency",
    "Fraud, Misconduct and Integrity Risk",
    "Mergers and Acquisitions",
    "Health, Safety and Operational Incidents"
]


def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


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
            except:
                score = 0

            score = max(0, min(score, 4))

            summary = item.get("summary", "").strip()
            if not summary:
                summary = "No relevant disclosure identified."

            fixed_results.append({
                "risk_category": category,
                "score": score,
                "summary": summary
            })
        else:
            fixed_results.append({
                "risk_category": category,
                "score": 0,
                "summary": "No relevant disclosure identified."
            })

    return fixed_results


def score_label(score):
    labels = {
        0: "No disclosure",
        1: "Generic",
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
            "Percentage Score"
        ],
        "Value": [
            company_name,
            uploaded_file_name,
            pages_reviewed,
            total_score,
            maximum_score,
            normalized_score,
            f"{percentage_score}%"
        ]
    })

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Score Summary")
        df.to_excel(writer, index=False, sheet_name="Category Results")

    return output.getvalue()


def build_results_table(df):
    table_rows = ""

    for _, row in df.iterrows():
        score = int(row["KRIS-DQ Score"])

        no_value = html.escape(str(row["No."]))
        category_value = html.escape(str(row["Risk Category"]))
        score_value = html.escape(str(row["KRIS-DQ Score"]))
        meaning_value = html.escape(str(row["Score Meaning"]))
        summary_value = html.escape(str(row["Summary of Disclosure"]))

        table_rows += f"""
        <tr>
            <td class="col-no">{no_value}</td>
            <td class="col-category">{category_value}</td>
            <td class="col-score score-{score}">{score_value}</td>
            <td class="col-meaning">{meaning_value}</td>
            <td class="col-summary">{summary_value}</td>
        </tr>
        """

    table_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color: #f9fafb;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }}

            .table-container {{
                width: 100%;
                overflow-x: hidden;
                padding: 0;
                box-sizing: border-box;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
                font-size: 15px;
                background: rgba(17, 24, 39, 0.35);
                border-radius: 10px;
                overflow: hidden;
            }}

            th {{
                background: rgba(31, 41, 55, 0.95);
                color: #d1d5db;
                padding: 12px 10px;
                text-align: left;
                border: 1px solid rgba(255, 255, 255, 0.08);
                font-weight: 700;
            }}

            td {{
                padding: 12px 10px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                vertical-align: top;
                line-height: 1.45;
                word-wrap: break-word;
                overflow-wrap: break-word;
                white-space: normal;
            }}

            .col-no {{
                width: 45px;
                text-align: center;
            }}

            .col-category {{
                width: 230px;
            }}

            .col-score {{
                width: 70px;
                text-align: center;
                font-weight: 800;
            }}

            .col-meaning {{
                width: 120px;
            }}

            .col-summary {{
                width: auto;
            }}

            .score-0 {{
                background-color: #374151;
                color: white;
            }}

            .score-1 {{
                background-color: #7f1d1d;
                color: white;
            }}

            .score-2 {{
                background-color: #92400e;
                color: white;
            }}

            .score-3 {{
                background-color: #1e3a8a;
                color: white;
            }}

            .score-4 {{
                background-color: #14532d;
                color: white;
            }}

            @media (max-width: 768px) {{
                table {{
                    font-size: 13px;
                }}

                th, td {{
                    padding: 9px 7px;
                }}

                .col-no {{
                    width: 38px;
                }}

                .col-category {{
                    width: 150px;
                }}

                .col-score {{
                    width: 55px;
                }}

                .col-meaning {{
                    width: 90px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th class="col-no">No.</th>
                        <th class="col-category">Risk Category</th>
                        <th class="col-score">Score</th>
                        <th class="col-meaning">Meaning</th>
                        <th class="col-summary">Summary of Disclosure</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    return table_html


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 1.5rem;
    }

    .logo-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 0.5rem;
        margin-bottom: 1.8rem;
    }

    .logo-banner {
        width: min(60vw, 560px);
        height: auto;
        border-radius: 14px;
    }

    .app-description {
        font-size: 18px;
        line-height: 1.6;
        max-width: 1200px;
        margin-top: 12px;
        margin-bottom: 18px;
    }

    .analysis-complete {
        padding: 14px 18px;
        border-radius: 12px;
        background: rgba(22, 101, 52, 0.22);
        border: 1px solid rgba(34, 197, 94, 0.35);
        color: #86efac;
        font-size: 17px;
        font-weight: 600;
        margin-top: 8px;
        margin-bottom: 24px;
    }

    .section-heading {
        font-size: 34px;
        font-weight: 800;
        margin-top: 12px;
        margin-bottom: 18px;
    }

    .context-card {
        padding: 20px 22px;
        border-radius: 16px;
        background: rgba(31, 41, 55, 0.42);
        border: 1px solid rgba(255, 255, 255, 0.08);
        min-height: 105px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin-bottom: 12px;
    }

    .context-label {
        font-size: 14px;
        font-weight: 700;
        opacity: 0.72;
        margin-bottom: 8px;
    }

    .context-value {
        font-size: 20px;
        font-weight: 750;
        line-height: 1.3;
    }

    .result-card {
        padding: 24px 22px;
        border-radius: 18px;
        background: rgba(31, 41, 55, 0.50);
        border: 1px solid rgba(255, 255, 255, 0.08);
        min-height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .result-card.primary {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.75), rgba(15, 23, 42, 0.85));
        border: 1px solid rgba(96, 165, 250, 0.35);
    }

    .result-label {
        font-size: 15px;
        font-weight: 700;
        opacity: 0.82;
        margin-bottom: 10px;
    }

    .result-value {
        font-size: 42px;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 10px;
    }

    .result-note {
        font-size: 14px;
        opacity: 0.70;
        line-height: 1.4;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 1.5rem;
        }

        .logo-banner {
            width: 92vw;
            border-radius: 12px;
        }

        .app-description {
            font-size: 16px;
            line-height: 1.55;
        }

        .section-heading {
            font-size: 28px;
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

logo_path = "new_logo.png"

if os.path.exists(logo_path):
    logo_base64 = get_base64_image(logo_path)

    st.markdown(
        f"""
        <div class="logo-wrapper">
            <img class="logo-banner" src="data:image/png;base64,{logo_base64}">
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.title("KRIS-DQ.ai")
    st.warning("new_logo.png not found. Please place new_logo.png in the same folder as app.py.")

st.markdown(
    """
    <div class="app-description">
    KRIS-DQ.ai evaluates annual report disclosures using the KRIS-DQ framework, transforming unstructured narratives into structured, comparable risk disclosure scores. Built on the KRIS-DQ framework developed through academic research, it generates category-level insights, concise summaries, and an overall disclosure quality score to support research, governance, and decision-making.
    </div>
    """,
    unsafe_allow_html=True
)

if client is None:
    st.warning(
        "OpenAI API key not found. Please set your API key as an environment variable named OPENAI_API_KEY "
        "or add it to Streamlit secrets."
    )

st.info(
    "Upload an annual report or selected risk-related sections to begin analysis. "
    "The system supports full reports, but filtered sections such as SORMIC, MD&A, Sustainability Statement, "
    "Governance Statement, AC Report, and RMC Report may improve accuracy and reduce processing time."
)

uploaded_file = st.file_uploader(
    "Upload Annual Report (PDF) to begin KRIS-DQ analysis",
    type="pdf"
)

if uploaded_file is not None:
    st.success("PDF uploaded successfully.")

    pdf_bytes = uploaded_file.read()
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    col_a, col_b = st.columns(2)

    with col_a:
        st.write("**File name:**", uploaded_file.name)

    with col_b:
        st.write("**Total pages:**", len(pdf))

    st.markdown("---")

    st.subheader("PDF Preview")
    st.caption("First three pages are shown for confirmation.")

    preview_cols = st.columns(3)

    for i in range(min(3, len(pdf))):
        page = pdf[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(0.45, 0.45))
        img_bytes = pix.tobytes("png")

        with preview_cols[i]:
            st.image(img_bytes, caption=f"Page {i + 1}", width=300)

    st.markdown("---")

    analyze = st.button("Generate KRIS-DQ Analysis", use_container_width=True)

    if analyze:
        if client is None:
            st.error(
                "Analysis cannot run because the OpenAI API key is missing. "
                "Please set OPENAI_API_KEY before running the app."
            )
            st.stop()

        with st.spinner("Generating KRIS-DQ analysis..."):
            text_sample = ""

            for i in range(len(pdf)):
                text_sample += pdf[i].get_text() + "\n\n"

            text_sample = text_sample[:30000]

            categories_text = "\n".join(
                [f"{i + 1}. {cat}" for i, cat in enumerate(KRIS_CATEGORIES)]
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
                                "score": {
                                    "type": "integer",
                                    "enum": [0, 1, 2, 3, 4]
                                },
                                "summary": {
                                    "type": "string"
                                }
                            },
                            "required": ["risk_category", "score", "summary"]
                        }
                    }
                },
                "required": ["company_name", "categories"]
            }

            try:
                response = client.responses.create(
                    model="gpt-5",
                    input=f"""
You are an expert in corporate risk disclosure and KRIS-DQ scoring.

Analyze the following annual report text using the KRIS-DQ framework.

First, identify the main reporting company or group name from the annual report text.
Return the official reporting company name as company_name.
If the company name cannot be identified, return "Not identified".
Do not use the name of subsidiaries, auditors, banks, customers, projects, hotels, or unrelated companies as the company_name.

You MUST evaluate all 18 KRIS-DQ categories below:
{categories_text}

Scoring guide:
0 = No disclosure
1 = Generic or minimal mention
2 = Descriptive explanation of risk or impact
3 = Includes mitigation strategies or management actions
4 = Includes quantitative or measurable information

Summary requirement:
For each category, provide a brief but complete summary that:
- identifies the risk discussed;
- explains the disclosed impact or exposure;
- mentions mitigation, response, governance action, or management strategy where available;
- includes quantitative information where disclosed;
- remains concise and useful for judging disclosure quality.

Important rules:
- Return the company_name and exactly 18 category objects.
- Use each category exactly once.
- Use the exact category names provided.
- Do not combine categories.
- Do not rename categories.
- Do not create new categories.
- If the category is not discussed, score it 0 and write "No relevant disclosure identified."
- Do not invent information not found in the report.
- Score must reflect the quality of disclosure, not the severity of the risk.

Annual report text:
{text_sample}
""",
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "kris_dq_result",
                            "strict": True,
                            "schema": schema
                        }
                    }
                )

                data = json.loads(response.output_text)

                company_name = data.get("company_name", "Not identified").strip()
                if not company_name:
                    company_name = "Not identified"

                fixed_categories = fix_categories(data.get("categories", []))

                total_score = sum(item["score"] for item in fixed_categories)
                maximum_score = 72
                normalized_score = round(total_score / maximum_score, 2)
                percentage_score = round(normalized_score * 100, 1)

                st.markdown(
                    """
                    <div class="analysis-complete">
                    Analysis complete. Please review the AI-assisted results below.
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
                    Key Risk Discloaure Quality Summary
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
                            <div class="result-note">All KRIS-DQ categories reviewed</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                st.markdown("---")

                st.subheader("Category-Level KRIS-DQ Results")

                df = pd.DataFrame(fixed_categories)

                df.insert(0, "No.", range(1, len(df) + 1))
                df["score_meaning"] = df["score"].apply(score_label)

                df = df[
                    ["No.", "risk_category", "score", "score_meaning", "summary"]
                ]

                df.columns = [
                    "No.",
                    "Risk Category",
                    "KRIS-DQ Score",
                    "Score Meaning",
                    "Summary of Disclosure"
                ]

                results_table = build_results_table(df)

                components.html(
                    results_table,
                    height=900,
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
                    label="Download KRIS-DQ Results as Excel",
                    data=excel_file,
                    file_name="KRIS_DQ_Results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

                st.caption(
                    "Validation check: 18 out of 18 KRIS-DQ categories displayed. "
                    "Scores are AI-assisted estimates and should be reviewed by the user."
                )

                st.markdown("---")

                st.subheader("Scoring Interpretation")

                st.markdown(
                    """
                    | Score | Interpretation |
                    |---|---|
                    | 0 | No disclosure |
                    | 1 | Generic or minimal mention |
                    | 2 | Descriptive explanation of risk or impact |
                    | 3 | Includes mitigation strategies or management actions |
                    | 4 | Includes quantitative or measurable information |
                    """
                )

            except Exception as e:
                st.error("Something went wrong during analysis.")
                st.write(e)
