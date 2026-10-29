
import os
import streamlit as st
from pypdf import PdfReader
from docx import Document
from dotenv import load_dotenv
from google import genai


# ---------- CONFIGURATION ----------
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

client = genai.Client(api_key=API_KEY) if API_KEY else None

st.set_page_config(
    page_title="DocuMind AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- SESSION STATE ----------
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = {}

if "generated_summary" not in st.session_state:
    st.session_state.generated_summary = ""

if "generated_mcqs" not in st.session_state:
    st.session_state.generated_mcqs = ""


# ---------- DARK PURPLE THEME ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

.stApp {
    background: radial-gradient(circle at 80% 0%, #241747 0%, #0b1020 40%);
    color: #f5f3ff;
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stSidebar"] {
    background: #101629;
    border-right: 1px solid #292644;
}

.block-container {
    padding-top: 2rem;
    max-width: 1450px;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    color: #ffffff !important;
}

p, label {
    color: #d6d3e8;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 8px 0 30px 0;
}

.brand-icon {
    background: linear-gradient(135deg, #a78bfa, #6d28d9);
    padding: 12px;
    border-radius: 14px;
    font-size: 25px;
}

.brand-name {
    font-size: 23px;
    font-weight: 700;
    color: white;
}

.brand-sub {
    color: #9695b5;
    font-size: 10px;
    letter-spacing: 1.5px;
}

.eyebrow {
    color: #c4b5fd;
    letter-spacing: 2px;
    font-size: 11px;
    font-weight: 700;
}

.hero-title {
    font-size: 38px;
    font-weight: 700;
    margin: 12px 0;
    color: #ffffff;
}

.hero-desc {
    color: #b9b5d2;
    font-size: 15px;
    line-height: 1.8;
}

.metric-card {
    background: #151d31;
    border: 1px solid #303751;
    border-radius: 17px;
    padding: 22px;
    min-height: 145px;
}

.metric-label {
    color: #a4abc2;
    font-size: 12px;
    font-weight: 600;
}

.metric-number {
    color: #ffffff;
    font-size: 31px;
    font-weight: 700;
    margin-top: 10px;
}

.metric-icon {
    font-size: 25px;
    margin-bottom: 10px;
}

.section-heading {
    font-size: 22px;
    font-weight: 700;
    margin-top: 30px;
    margin-bottom: 5px;
    color: #ffffff;
}

.section-desc {
    color: #9ba5bd;
    font-size: 13px;
    margin-bottom: 18px;
}

.feature-card {
    background: linear-gradient(145deg, #171f35, #12192b);
    border: 1px solid #303751;
    border-radius: 17px;
    padding: 22px;
    min-height: 185px;
    margin-bottom: 12px;
}

.feature-icon {
    font-size: 28px;
    margin-bottom: 13px;
}

.feature-title {
    color: #ffffff;
    font-size: 17px;
    font-weight: 700;
    margin-bottom: 8px;
}

.feature-desc {
    color: #a5aec4;
    font-size: 13px;
    line-height: 1.7;
}

div.stButton > button {
    background: linear-gradient(135deg, #8b5cf6, #6d28d9);
    color: white;
    border: 1px solid #9876fa;
    border-radius: 10px;
    min-height: 42px;
    font-weight: 600;
}

div.stButton > button:hover {
    border-color: #c4b5fd;
    color: white;
}

div[data-testid="stFileUploader"] {
    background: #141b2d;
    border: 1px dashed #7760bd;
    border-radius: 14px;
    padding: 12px;
}

hr {
    border-color: #303751;
}
</style>
""", unsafe_allow_html=True)


# ---------- HELPER: EXTRACT DOCUMENT TEXT ----------
def extract_text(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif filename.endswith(".docx"):
        document = Document(uploaded_file)
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    elif filename.endswith(".txt"):
        return uploaded_file.getvalue().decode(
            "utf-8",
            errors="replace"
        )

    return ""


# ---------- HELPER: GEMINI AI ----------
def ask_gemini(prompt):
    if client is None:
        raise ValueError(
            "Gemini API key not found. Check your .env file."
        )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    result = response.text

    if not result or not result.strip():
        raise ValueError(
            "Gemini returned an empty response. Please try again."
        )

    return result


def show_ai_error(error):
    st.error(f"AI generation failed: {error}")
    st.info(
        "Check your API key, model availability and internet connection. "
        "A 503 error may mean the model is temporarily busy."
    )


# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("""
    <div class="brand">
        <div class="brand-icon">🧠</div>
        <div>
            <div class="brand-name">DocuMind AI</div>
            <div class="brand-sub">SMART DOCUMENT WORKSPACE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### WORKSPACE")

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "My Documents",
            "AI Chat",
            "AI Summary",
            "MCQ Generator"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("#### 📁 Supported files")
    st.caption("PDF · DOCX · TXT")

    st.markdown("---")
    st.caption("Final Year Project")
    st.caption("Powered by Gemini AI")


# ---------- MAIN HEADER ----------
st.markdown(
    '<div class="eyebrow">YOUR AI KNOWLEDGE WORKSPACE</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="hero-title">Your knowledge, simplified.</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="hero-desc">Upload your documents, explore important '
    'information, and turn lengthy files into useful knowledge — '
    'all in one place.</div>',
    unsafe_allow_html=True
)

st.write("")


# ---------- DASHBOARD ----------
if page == "Dashboard":
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📚</div>
            <div class="metric-label">TOTAL DOCUMENTS</div>
            <div class="metric-number">
                {len(st.session_state.uploaded_docs):02d}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-icon">💬</div>
            <div class="metric-label">AI CHAT</div>
            <div class="metric-number">01</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-icon">✨</div>
            <div class="metric-label">AI TOOLS</div>
            <div class="metric-number">02</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-heading">Get started</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-desc">Upload documents and use AI tools.</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📤</div>
            <div class="feature-title">Upload Documents</div>
            <div class="feature-desc">
                Add PDF, Word and text documents to your workspace.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💬</div>
            <div class="feature-title">Chat with Document</div>
            <div class="feature-desc">
                Ask questions about your uploaded document.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <div class="feature-title">MCQ Generator</div>
            <div class="feature-desc">
                Create multiple-choice questions for exam preparation.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-heading">Upload your document</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-desc">Select a PDF, DOCX or TXT file.</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Choose a document",
        type=["pdf", "docx", "txt"],
        help="PDF, DOCX and TXT files are supported.",
        key="dashboard_uploader"
    )

    if uploaded_file is not None:
        if uploaded_file.name not in st.session_state.uploaded_docs:
            try:
                with st.spinner("Reading your document..."):
                    text = extract_text(uploaded_file)

                st.session_state.uploaded_docs[
                    uploaded_file.name
                ] = text

                if text.strip():
                    st.success(
                        f"Successfully read: {uploaded_file.name}"
                    )
                else:
                    st.warning(
                        "File uploaded, but no readable text was found. "
                        "The PDF may contain scanned pages."
                    )

            except Exception as error:
                st.error(f"Document read error: {error}")

        extracted_text = st.session_state.uploaded_docs.get(
            uploaded_file.name, ""
        )

        if extracted_text.strip():
            st.markdown("### 📄 Extracted Text Preview")
            st.caption(f"File: {uploaded_file.name}")

            st.text_area(
                "Document content (first 5000 characters)",
                extracted_text[:5000],
                height=250,
                key="preview_" + uploaded_file.name
            )

            st.download_button(
                "⬇️ Download extracted text",
                data=extracted_text,
                file_name=uploaded_file.name.rsplit(".", 1)[0] + ".txt",
                mime="text/plain"
            )


# ---------- MY DOCUMENTS ----------
elif page == "My Documents":
    st.markdown("## 📚 My Documents")

    if st.session_state.uploaded_docs:
        st.success(
            f"{len(st.session_state.uploaded_docs)} document(s) "
            "loaded in this session."
        )

        for filename, text in list(
            st.session_state.uploaded_docs.items()
        ):
            with st.expander("📄 " + filename):
                st.write(f"Characters extracted: {len(text)}")

                if text.strip():
                    st.text_area(
                        "Text preview",
                        text[:3000],
                        height=180,
                        key="doc_" + filename
                    )
                else:
                    st.warning("No readable text was extracted.")

                if st.button(
                    "Remove document",
                    key="remove_" + filename
                ):
                    del st.session_state.uploaded_docs[filename]
                    st.rerun()

    else:
        st.info(
            "No documents uploaded yet. Go to Dashboard and upload a file."
        )


# ---------- AI CHAT ----------
elif page == "AI Chat":
    st.markdown("## 💬 Chat with your document")
    st.caption("Ask a question about your uploaded document.")

    if not st.session_state.uploaded_docs:
        st.info("First, upload a document from Dashboard.")

    else:
        selected_doc = st.selectbox(
            "Choose document",
            list(st.session_state.uploaded_docs.keys()),
            key="chat_doc"
        )

        question = st.text_input(
            "Ask a question",
            placeholder="What are the main topics in this document?"
        )

        if st.button("💬 Ask AI", key="ask_ai_button"):
            doc_text = st.session_state.uploaded_docs[selected_doc]

            if not doc_text.strip():
                st.warning("This document has no readable text.")

            elif not question.strip():
                st.warning("Please enter a question.")

            else:
                prompt = f"""
Answer the question using only the document below.
If the answer is not in the document, say that clearly.
Use simple English.

DOCUMENT:
{doc_text[:18000]}

QUESTION:
{question}
"""

                try:
                    with st.spinner("Finding the answer..."):
                        answer = ask_gemini(prompt)

                    st.markdown("### 💡 Answer")
                    st.write(answer)

                except Exception as error:
                    show_ai_error(error)


# ---------- AI SUMMARY ----------
elif page == "AI Summary":
    st.markdown("## ✨ AI Summary")
    st.caption(
        "Generate a summary of your uploaded document using Gemini AI."
    )

    if not st.session_state.uploaded_docs:
        st.info("First, upload a PDF, DOCX or TXT file from Dashboard.")

    else:
        selected_doc = st.selectbox(
            "Choose document to summarize",
            list(st.session_state.uploaded_docs.keys()),
            key="summary_doc"
        )

        doc_text = st.session_state.uploaded_docs[selected_doc]

        if not doc_text.strip():
            st.warning("No readable text was found in this document.")

        elif st.button("✨ Generate AI Summary", key="summary_button"):
            prompt = f"""
Summarize the document in clear, simple English.

Include:
1. A short overview
2. Important points
3. Key findings
4. A conclusion

Do not invent information. Use only the document below.

DOCUMENT:
{doc_text[:30000]}
"""

            try:
                with st.spinner("Gemini is summarizing your document..."):
                    summary = ask_gemini(prompt)

                st.session_state.generated_summary = summary

            except Exception as error:
                show_ai_error(error)

        if st.session_state.generated_summary:
            st.markdown("### 📝 Generated Summary")
            st.write(st.session_state.generated_summary)

            st.download_button(
                "⬇️ Download Summary",
                data=st.session_state.generated_summary,
                file_name="document_summary.txt",
                mime="text/plain",
                key="download_summary"
            )


# ---------- MCQ GENERATOR ----------
elif page == "MCQ Generator":
    st.markdown("## 🧠 MCQ Generator")
    st.caption(
        "Generate multiple-choice questions from your uploaded document."
    )

    if not st.session_state.uploaded_docs:
        st.info(
            "MCQ तयार करण्यापूर्वी Dashboard वरून document upload करा."
        )

    else:
        selected_doc = st.selectbox(
            "Choose document",
            list(st.session_state.uploaded_docs.keys()),
            key="mcq_doc"
        )

        doc_text = st.session_state.uploaded_docs[selected_doc]

        number_of_questions = st.selectbox(
            "Number of questions",
            [5, 10, 15, 20],
            index=0,
            key="mcq_number"
        )

        difficulty = st.selectbox(
            "Difficulty level",
            ["Easy", "Medium", "Hard"],
            index=1,
            key="mcq_difficulty"
        )

        if not doc_text.strip():
            st.warning("No readable text was found in this document.")

        elif st.button(
            "🧠 Generate MCQs",
            key="generate_mcqs_button"
        ):
            prompt = f"""
You are an educational quiz generator.

Create exactly {number_of_questions} multiple-choice questions
at {difficulty} difficulty level using ONLY the document below.

Rules:
1. Every question must have four options: A, B, C and D.
2. Only one option must be correct.
3. Clearly show the correct answer.
4. Give a short explanation for each answer.
5. Do not use facts that are not present in the document.
6. Number every question.
7. Write in simple English.

Use this format:

Q1. Question text
A. Option A
B. Option B
C. Option C
D. Option D
Correct Answer: B
Explanation: Short explanation

DOCUMENT:
{doc_text[:18000]}
"""

            try:
                with st.spinner(
                    "Generating MCQs... Please wait."
                ):
                    mcqs = ask_gemini(prompt)

                st.session_state.generated_mcqs = mcqs
                st.success("MCQs generated successfully!")

            except Exception as error:
                show_ai_error(error)

        if st.session_state.generated_mcqs:
            st.markdown("### 📝 Generated MCQs")
            st.markdown(st.session_state.generated_mcqs)

            st.download_button(
                "⬇️ Download MCQs",
                data=st.session_state.generated_mcqs,
                file_name="documind_mcqs.txt",
                mime="text/plain",
                key="download_mcqs_button"
            )
