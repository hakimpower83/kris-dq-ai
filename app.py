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

PROMPT_VERSION = "kris-dq-published-framework-v3"
MAX_ANALYSIS_CHARS = 60000


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
    table_rows = ""

    for _, row in df.iterrows():
        score = int(row["KRIS-DQ Score"])

        no_value = html.escape(str(row["No."]))
        category_value = html.escape(str(row["Risk Category"]))
        evidence_value = html.escape(str(row["Evidence Found"]))
        score_value = html.escape(str(row["KRIS-DQ Score"]))
        meaning_value = html.escape(str(row["Score Meaning"]))
        evidence_summary_value = html.escape(str(row["Evidence Summary"]))
        summary_value = html.escape(str(row["Summary of Disclosure"]))

        evidence_class = "evidence-yes" if evidence_value == "Yes" else "evidence-no"

        table_rows += f"""
        <tr>
            <td class="col-no">{no_value}</td>
            <td class="col-category">{category_value}</td>
            <td class="col-evidence {evidence_class}">{evidence_value}</td>
            <td class="col-score score-{score}">{score_value}</td>
            <td class="col-meaning">{meaning_value}</td>
            <td class="col-evidence-summary">{evidence_summary_value}</td>
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
                overflow-x: auto;
                padding: 0;
                box-sizing: border-box;
            }}

            table {{
                width: 100%;
                min-width: 1450px;
                border-collapse: collapse;
                table-layout: fixed;
                font-size: 14px;
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

            .col-evidence {{
                width: 75px;
                text-align: center;
                font-weight: 800;
            }}

            .col-score {{
                width: 70px;
                text-align: center;
                font-weight: 800;
            }}

            .col-meaning {{
                width: 110px;
            }}

            .col-evidence-summary {{
                width: 410px;
            }}

            .col-summary {{
                width: 510px;
            }}

            .evidence-yes {{
                background-color: #14532d;
                color: white;
            }}

            .evidence-no {{
                background-color: #374151;
                color: white;
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
                    min-width: 1350px;
                }}

                th, td {{
                    padding: 9px 7px;
                }}

                .col-no {{
                    width: 38px;
                }}

                .col-category {{
                    width: 180px;
                }}

                .col-evidence {{
                    width: 65px;
                }}

                .col-score {{
                    width: 55px;
                }}

                .col-meaning {{
                    width: 90px;
                }}

                .col-evidence-summary {{
                    width: 390px;
                }}

                .col-summary {{
                    width: 470px;
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
                        <th class="col-evidence">Evidence</th>
                        <th class="col-score">Score</th>
                        <th class="col-meaning">Meaning</th>
                        <th class="col-evidence-summary">Evidence Summary</th>
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

    .human-review-note {
        padding: 14px 18px;
        border-radius: 12px;
        background: rgba(30, 58, 138, 0.22);
        border: 1px solid rgba(96, 165, 250, 0.35);
        color: #bfdbfe;
        font-size: 15px;
        line-height: 1.45;
        margin-top: 8px;
        margin-bottom: 18px;
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


# ============================================================
# HEADER AND LANDING PAGE
# ============================================================

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
    KRIS-DQ.ai evaluates annual report disclosures using the published KRIS-DQ Index framework, transforming unstructured narratives into structured, comparable risk disclosure scores. Built on the KRIS-DQ framework developed through academic research, it generates category-level evidence, concise summaries, and an overall disclosure quality score to support research, governance, and decision-making.
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
    "For best results, it is highly recommended to upload selected risk-related sections "
    "rather than a full annual report. Suitable sections include SORMIC, MD&A, "
    "Sustainability Statement, CG Report, AC Report, RMC Report, Directors' Report, "
    "and other risk management or governance-related sections. Full annual reports are accepted, "
    "but they may contain substantial non-risk content such as financial statements, notes, "
    "corporate information, repeated headers, and administrative pages, which can reduce focus "
    "and affect scoring accuracy."
)


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "Upload Annual Report or Selected Risk-Related Sections (PDF)",
    type="pdf"
)


# ============================================================
# MAIN APP LOGIC
# ============================================================

if uploaded_file is not None:
    st.success("PDF uploaded successfully.")

    pdf_bytes = uploaded_file.getvalue()
    file_hash = get_file_hash(pdf_bytes)

    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    col_a, col_b = st.columns(2)

    with col_a:
        st.write("**File name:**", uploaded_file.name)

    with col_b:
        st.write("**Total pages:**", len(pdf))

    st.markdown("---")

    st.subheader("PDF Preview")
    st.caption(
        "First three pages are shown for confirmation. "
        "For best accuracy, selected risk-related sections are recommended."
    )

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
            full_text = ""

            for i in range(len(pdf)):
                full_text += pdf[i].get_text() + "\n\n"

            text_sample = full_text[:MAX_ANALYSIS_CHARS]

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

            try:
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

                company_name = data.get("company_name", "Not identified").strip()
                if not company_name:
                    company_name = "Not identified"

                fixed_categories = fix_categories(data.get("categories", []))

                total_score = sum(item["score"] for item in fixed_categories)
                maximum_score = 72
                normalized_score = round(total_score / maximum_score, 2)
                percentage_score = round((total_score / maximum_score) * 100, 1)

                st.markdown(
                    """
                    <div class="analysis-complete">
                    Analysis complete. Please review the AI-assisted results below.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if used_cached_result:
                    st.caption(
                        "Consistency note: this result was reused from the same uploaded PDF during the current session."
                    )

                st.markdown(
                    """
                    <div class="human-review-note">
                    KRIS-DQ.ai provides AI-assisted preliminary scoring. Final scores should be reviewed by a trained human coder, especially for academic research, regulatory use, or paid professional reports.
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

                st.subheader("Category-Level KRIS-DQ Results")

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
                    "Validation check: 18 out of 18 published KRIS-DQ categories displayed. "
                    "Scores are AI-assisted preliminary estimates and should be reviewed by the user."
                )

                st.markdown("---")

                st.subheader("Scoring Interpretation")

                st.markdown(
                    """
                    | Score | Interpretation |
                    |---|---|
                    | 0 | No disclosure |
                    | 1 | Minimal coverage, vague or generic references to risk with little detail |
                    | 2 | Descriptive disclosure, where the impact of the risk is evident |
                    | 3 | Explanation of mitigation strategies, plans, controls, or strategies to mitigate or eliminate the risk |
                    | 4 | Inclusion of quantitative information, either in monetary terms or actual physical quantities |
                    """
                )

            except Exception as e:
                st.error("Something went wrong during analysis.")
                st.write(e)
