import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import pandas as pd
import json
import os
from io import BytesIO

st.set_page_config(
    page_title="KRIS-DQ.ai",
    page_icon="Logo.png",
    layout="wide"
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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


def highlight_scores(value):
    if value == 0:
        return "background-color: #374151; color: white;"
    elif value == 1:
        return "background-color: #7f1d1d; color: white;"
    elif value == 2:
        return "background-color: #92400e; color: white;"
    elif value == 3:
        return "background-color: #1e3a8a; color: white;"
    elif value == 4:
        return "background-color: #14532d; color: white;"
    return ""


def convert_df_to_excel(df, total_score, maximum_score, normalized_score, percentage_score):
    output = BytesIO()

    summary_df = pd.DataFrame({
        "Metric": [
            "Total KRIS-DQ Score",
            "Maximum Score",
            "Normalized Score",
            "Percentage Score"
        ],
        "Value": [
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


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 3rem;
        padding-bottom: 1.5rem;
    }

    .logo-box {
        display: flex;
        align-items: center;
        gap: 20px;
        margin-bottom: 12px;
    }

    .logo-img {
        width: 95px;
        height: 95px;
        object-fit: contain;
    }

    .app-title {
        font-size: 58px;
        font-weight: 800;
        margin: 0;
        line-height: 1.1;
        margin-bottom: 6px
    }

    .app-subtitle {
        font-size: 19px;
        font-weight: 600;
        margin-top: 2px;
        margin-bottom: 0.9px;
    }

    .app-description {
        font-size: 18px;
        line-height: 1.6;
        max-width: 1200px;
        margin-top: 12px;
    }

    .score-card {
        padding: 28px;
        border-radius: 18px;
        background: rgba(31, 41, 55, 0.55);
        border: 1px solid rgba(255,255,255,0.08);
        text-align: center;
    }

    .score-main {
        font-size: 58px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .score-label {
        font-size: 18px;
        opacity: 0.85;
    }
    </style>
    """,
    unsafe_allow_html=True
)

logo_path = "Logo.png"

if os.path.exists(logo_path):
    col_logo, col_title = st.columns([1, 10])

    with col_logo:
        st.image(logo_path, use_container_width=True)

    with col_title:
        st.markdown(
            """
            <div>
                <div class="app-title">KRIS-DQ.ai</div>
                <div class="app-subtitle">AI-powered Key Risk Disclosure Quality analysis</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.caption("Built on the KRIS-DQ framework developed through academic research.")
else:
    st.title("KRIS-DQ.ai")
    st.warning("Logo.png not found. Please place Logo.png in the same folder as app.py.")

st.markdown(
    """
    <div class="app-description">
    KRIS-DQ.ai evaluates annual report disclosures using the KRIS-DQ framework, transforming unstructured narratives into structured, comparable risk disclosure scores. It generates category-level insights, concise summaries, and an overall disclosure quality score to support research, governance, and decision-making.
    </div>
    """,
    unsafe_allow_html=True
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
        pix = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7))
        img_bytes = pix.tobytes("png")

        with preview_cols[i]:
            st.image(img_bytes, caption=f"Page {i + 1}")

    st.markdown("---")

    analyze = st.button("Generate KRIS-DQ Analysis", use_container_width=True)

    if analyze:
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
                "required": ["categories"]
            }

            try:
                response = client.responses.create(
                    model="gpt-5",
                    input=f"""
You are an expert in corporate risk disclosure and KRIS-DQ scoring.

Analyze the following annual report text using the KRIS-DQ framework.

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
- Return exactly 18 category objects.
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
                fixed_categories = fix_categories(data.get("categories", []))

                total_score = sum(item["score"] for item in fixed_categories)
                maximum_score = 72
                normalized_score = round(total_score / maximum_score, 2)
                percentage_score = round(normalized_score * 100, 1)

                st.success("Analysis complete.")

                st.markdown("## KRIS-DQ Score Summary")

                score_col, total_col, max_col, checked_col = st.columns(4)

                with score_col:
                    st.markdown(
                        f"""
                        <div class="score-card">
                            <div class="score-main">{percentage_score}%</div>
                            <div class="score-label">Overall KRIS-DQ Percentage</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with total_col:
                    st.metric("Total Score", total_score)

                with max_col:
                    st.metric("Maximum Score", maximum_score)

                with checked_col:
                    st.metric("Categories Checked", "18 / 18")

                st.caption(
                    f"Normalized score: {normalized_score} | Raw score: {total_score} out of {maximum_score}"
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

                styled_df = df.style.map(
                    highlight_scores,
                    subset=["KRIS-DQ Score"]
                )

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    height=520
                )

                excel_file = convert_df_to_excel(
                    df,
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