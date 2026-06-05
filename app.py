import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import ollama
import os
import csv
from datetime import datetime

from src.multimodal_loader import extract_text_from_file
from src.chunking import chunk_text
from src.vector_db import create_vector_db, retrieve_chunks
from src.rag_pipeline import generate_answer
from src.evaluator import run_evaluation
from src.direct_answer import direct_answer_from_text
from src.config import (
    LLM_MODEL,
    EMBED_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    N_RESULTS,
    TEMPERATURE
)


# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Khánh AI",
    page_icon="🎋",
    layout="wide"
)


# =========================
# CONFIG
# =========================

DATA_DIR = "data"
AVATAR_DIR = os.path.join(DATA_DIR, "avatars")

USERS_CSV = os.path.join(DATA_DIR, "users.csv")
CHAT_LOG_CSV = os.path.join(DATA_DIR, "chat_logs.csv")
UPLOAD_LOG_CSV = os.path.join(DATA_DIR, "upload_logs.csv")

ADMIN_PASSWORD = "admin123"
BRAND_NAME = "Khánh AI"
HOTLINE = "0941761768"


# =========================
# DATA FUNCTIONS
# =========================

def ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(AVATAR_DIR, exist_ok=True)

    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time",
                "first_name",
                "last_name",
                "full_name",
                "email",
                "phone",
                "password",
                "profile_link",
                "avatar_path"
            ])

    if not os.path.exists(CHAT_LOG_CSV):
        with open(CHAT_LOG_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time",
                "name",
                "email",
                "phone",
                "question",
                "answer"
            ])

    if not os.path.exists(UPLOAD_LOG_CSV):
        with open(UPLOAD_LOG_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time",
                "name",
                "email",
                "phone",
                "file_name",
                "file_type",
                "chunk_count"
            ])


def read_csv_safe(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def save_avatar(uploaded_avatar, email):
    if uploaded_avatar is None:
        return ""

    safe_email = email.replace("@", "_").replace(".", "_").replace(" ", "_")
    ext = os.path.splitext(uploaded_avatar.name)[1] or ".png"
    avatar_name = f"{safe_email}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    avatar_path = os.path.join(AVATAR_DIR, avatar_name)

    with open(avatar_path, "wb") as f:
        f.write(uploaded_avatar.getbuffer())

    return avatar_path


def save_user_register(first_name, last_name, email, phone, password, profile_link, avatar_path):
    full_name = f"{first_name} {last_name}".strip()

    with open(USERS_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            first_name,
            last_name,
            full_name,
            email,
            phone,
            password,
            profile_link,
            avatar_path
        ])


def email_exists(email):
    users_df = read_csv_safe(USERS_CSV)

    if users_df.empty or "email" not in users_df.columns:
        return False

    return email.lower() in users_df["email"].astype(str).str.lower().values


def find_user_by_email_password(email, password):
    users_df = read_csv_safe(USERS_CSV)

    if users_df.empty:
        return None

    if "email" not in users_df.columns or "password" not in users_df.columns:
        return None

    matched = users_df[
        (users_df["email"].astype(str).str.lower() == email.lower())
        & (users_df["password"].astype(str) == str(password))
    ]

    if matched.empty:
        return None

    return matched.iloc[-1].to_dict()


def save_chat_log(question, answer):
    with open(CHAT_LOG_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            st.session_state.get("user_name", ""),
            st.session_state.get("user_email", ""),
            st.session_state.get("user_phone", ""),
            question,
            answer
        ])


def save_upload_log(file_name, file_type, chunk_count):
    with open(UPLOAD_LOG_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            st.session_state.get("user_name", ""),
            st.session_state.get("user_email", ""),
            st.session_state.get("user_phone", ""),
            file_name,
            file_type,
            chunk_count
        ])


ensure_data_files()


# =========================
# SESSION STATE
# =========================

defaults = {
    "messages": [],
    "collection": None,
    "file_name": "",
    "file_type": "",
    "extracted_text": "",
    "chunk_count": 0,
    "logged_in": False,
    "admin_logged_in": False,
    "user_name": "",
    "user_email": "",
    "user_phone": "",
    "profile_link": "",
    "avatar_path": "",
    "chat_image_name": "",
    "last_image_text": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


current_page = st.query_params.get("page", "home")

if isinstance(current_page, list):
    current_page = current_page[0]


# =========================
# CSS STREAMLIT
# =========================

st.markdown(
    """
    <style>
    .stApp {
        background: #fbfaf6;
        color: #102217;
    }

    header {
        visibility: hidden;
    }

    .main .block-container {
        max-width: 1260px;
        padding-top: 0rem;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] {
        background: #f7f3ea;
        border-right: 1px solid #e3dccd;
    }

    h1, h2, h3 {
        color: #102217 !important;
        font-weight: 900 !important;
    }

    [data-testid="stFileUploader"] {
        background: white;
        border: 2px dashed #367541;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 12px 26px rgba(37, 72, 45, 0.05);
    }

    [data-testid="stChatMessage"] {
        background: white;
        border: 1px solid #e7e2d7;
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 10px 24px rgba(37, 72, 45, 0.05);
        margin-bottom: 14px;
    }

    [data-testid="stChatInput"] {
        background: white;
        border-radius: 18px;
        border: 1px solid #d8d0c0;
        box-shadow: 0 14px 30px rgba(37, 72, 45, 0.08);
    }

    .stButton button {
        background: #367541;
        color: white;
        border-radius: 0px;
        border: none;
        min-height: 46px;
        font-weight: 800;
    }

    .stButton button:hover {
        background: #295d34;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# HTML COMPONENTS
# =========================

def render_header():
    report_nav = ""
    if st.session_state.admin_logged_in:
        report_nav = '<a target="_parent" href="#report-section">Report</a>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                background: #fbfaf6;
            }}

            a {{
                text-decoration: none;
            }}

            .top-green-bar {{
                width: 100%;
                height: 56px;
                background: #367541;
                color: white;
                padding: 0 12%;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}

            .top-left {{
                font-size: 16px;
                font-weight: 700;
                color: white;
            }}

            .top-right {{
                display: flex;
                align-items: center;
                gap: 28px;
            }}

            .top-item {{
                color: white;
                font-size: 16px;
                font-weight: 700;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                cursor: pointer;
            }}

            .search-pill {{
                width: 280px;
                height: 42px;
                background: white;
                color: #777;
                border-radius: 999px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 16px 0 22px;
                font-size: 15px;
            }}

            .search-icon {{
                color: #111;
                font-size: 20px;
                font-weight: 900;
            }}

            .account {{
                position: relative;
                padding: 18px 0;
            }}

            .account-menu {{
                display: none;
                position: absolute;
                top: 54px;
                right: -25px;
                background: white;
                min-width: 150px;
                padding: 10px 0;
                box-shadow: 0 12px 28px rgba(0,0,0,0.18);
                z-index: 9999;
            }}

            .account-menu:before {{
                content: "";
                position: absolute;
                top: -10px;
                right: 46px;
                border-left: 10px solid transparent;
                border-right: 10px solid transparent;
                border-bottom: 10px solid white;
            }}

            .account-menu a {{
                display: block;
                padding: 10px 18px;
                color: #222;
                font-size: 15px;
                font-weight: 500;
                white-space: nowrap;
            }}

            .account-menu a:hover {{
                background: #f5f5f5;
                color: #367541;
            }}

            .account:hover .account-menu {{
                display: block;
            }}

            .cart-count {{
                width: 20px;
                height: 20px;
                background: white;
                color: #367541;
                border-radius: 50%;
                font-size: 13px;
                font-weight: 900;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                margin-left: -8px;
                margin-right: -2px;
            }}

            .nav-wrap {{
                width: 100%;
                height: 160px;
                background: white;
                border-bottom: 1px solid #e7e2d7;
                padding: 0 12%;
                display: flex;
                align-items: center;
            }}

            .nav-row {{
                width: 100%;
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                align-items: center;
                gap: 20px;
            }}

            .nav-left,
            .nav-right {{
                display: flex;
                align-items: center;
                gap: 38px;
            }}

            .nav-left {{
                justify-content: flex-start;
            }}

            .nav-right {{
                justify-content: flex-end;
            }}

            .nav-row a,
            .dropdown-title {{
                color: #111;
                font-size: 18px;
                font-weight: 800;
                cursor: pointer;
            }}

            .nav-row a:hover,
            .dropdown-title:hover {{
                color: #367541;
            }}

            .logo {{
                width: 150px;
                height: 90px;
                border-radius: 20px;
                background: linear-gradient(135deg, #009846, #4fae54);
                border: 4px solid #e6f2df;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 25px;
                font-weight: 950;
                box-shadow: 0 8px 22px rgba(0, 121, 60, 0.25);
                text-align: center;
            }}

            .dropdown {{
                position: relative;
                padding: 24px 0;
            }}

            .dropdown-menu {{
                display: none;
                position: absolute;
                top: 72px;
                left: 0;
                background: white;
                min-width: 230px;
                box-shadow: 0 12px 26px rgba(0,0,0,0.12);
                z-index: 9999;
                border: 1px solid #eeeeee;
                padding: 10px 0;
            }}

            .dropdown-menu a {{
                display: block;
                padding: 13px 20px;
                color: #555;
                font-size: 15px;
                font-weight: 500;
                border-bottom: 1px solid #eee;
            }}

            .dropdown-menu a:hover {{
                background: #f8f8f8;
                color: #367541;
            }}

            .dropdown:hover .dropdown-menu {{
                display: block;
            }}
        </style>
    </head>

    <body>
        <div class="top-green-bar">
            <div class="top-left">
                ☎ Hotline: {HOTLINE}
            </div>

            <div class="top-right">
                <a class="search-pill" target="_parent" href="#search-section">
                    <span>Tìm kiếm...</span>
                    <span class="search-icon">🔍</span>
                </a>

                <div class="account">
                    <span class="top-item">👤 Tài khoản</span>
                    <div class="account-menu">
                        <a target="_parent" href="?page=login">Đăng nhập</a>
                        <a target="_parent" href="?page=register">Đăng ký</a>
                    </div>
                </div>

                <a class="top-item" target="_parent" href="#upload-section">
                    🛍️ <span class="cart-count">0</span> Giỏ hàng
                </a>
            </div>
        </div>

        <div class="nav-wrap">
            <div class="nav-row">
                <div class="nav-left">
                    <a target="_parent" href="?page=home">Trang chủ</a>

                    <div class="dropdown">
                        <span class="dropdown-title">Giới thiệu ▾</span>
                        <div class="dropdown-menu">
                            <a target="_parent" href="#about-section">Về hệ thống</a>
                            <a target="_parent" href="#about-section">Tính năng</a>
                            <a target="_parent" href="#footer-section">Liên hệ</a>
                        </div>
                    </div>

                    <div class="dropdown">
                        <span class="dropdown-title">Danh mục ▾</span>
                        <div class="dropdown-menu">
                            <a target="_parent" href="#upload-section">Upload file PDF/TXT</a>
                            <a target="_parent" href="#image-upload-section">Upload ảnh</a>
                            <a target="_parent" href="#chatbot-section">Hỏi đáp tài liệu</a>
                            <a target="_parent" href="#evaluation-section">Đánh giá nghiên cứu</a>
                        </div>
                    </div>
                </div>

                <div class="logo">🎋 Khánh AI</div>

                <div class="nav-right">
                    <div class="dropdown">
                        <span class="dropdown-title">Sản phẩm ▾</span>
                        <div class="dropdown-menu">
                            <a target="_parent" href="#upload-section">PDF RAG</a>
                            <a target="_parent" href="#image-upload-section">Image RAG</a>
                            <a target="_parent" href="#chatbot-section">Chatbot</a>
                            <a target="_parent" href="#evaluation-section">Research Mode</a>
                        </div>
                    </div>

                    <a target="_parent" href="#about-section">Tin tức</a>
                    <a target="_parent" href="#footer-section">Liên hệ</a>
                    {report_nav}
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(html, height=230, scrolling=False)


def render_hero():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #fbfaf6;
            }

            .hero {
                min-height: 490px;
                background:
                    radial-gradient(circle at 12% 25%, rgba(72, 143, 82, 0.14), transparent 28%),
                    radial-gradient(circle at 85% 20%, rgba(184, 143, 83, 0.18), transparent 24%),
                    linear-gradient(90deg, #f6f8f0, #ffffff);
                border-radius: 24px;
                border: 1px solid #e7e2d7;
                display: grid;
                grid-template-columns: 1.05fr 0.95fr;
                overflow: hidden;
                margin-bottom: 34px;
                box-shadow: 0 22px 46px rgba(37, 72, 45, 0.1);
            }

            .hero-left {
                padding: 66px 58px;
            }

            .hero-label {
                color: #367541;
                font-size: 14px;
                font-weight: 900;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-bottom: 18px;
            }

            .hero-title {
                font-size: 54px;
                line-height: 1.08;
                font-weight: 950;
                color: #17231c;
                margin-bottom: 22px;
            }

            .hero-title span {
                color: #367541;
            }

            .hero-desc {
                font-size: 18px;
                line-height: 1.85;
                color: #4c5a50;
                max-width: 640px;
                margin-bottom: 32px;
            }

            .hero-actions {
                display: flex;
                gap: 16px;
                flex-wrap: wrap;
            }

            .btn-primary {
                background: #367541;
                color: white;
                padding: 15px 28px;
                border-radius: 999px;
                font-weight: 900;
                box-shadow: 0 12px 24px rgba(54, 117, 65, 0.28);
                text-decoration: none;
            }

            .btn-secondary {
                background: white;
                color: #367541;
                padding: 15px 28px;
                border: 1px solid #367541;
                border-radius: 999px;
                font-weight: 900;
                text-decoration: none;
            }

            .hero-right {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 40px;
            }

            .visual-circle {
                width: 410px;
                height: 410px;
                border-radius: 50%;
                background:
                    repeating-linear-gradient(45deg, #d6b067 0px, #d6b067 12px, #c99d51 12px, #c99d51 24px);
                box-shadow: inset 0 0 0 18px rgba(255,255,255,0.28), 0 28px 60px rgba(83, 68, 39, 0.2);
                position: relative;
            }

            .visual-card {
                position: absolute;
                bottom: 74px;
                left: 25px;
                right: 25px;
                background: rgba(255,255,255,0.92);
                border-radius: 22px;
                padding: 24px;
                text-align: center;
            }

            .visual-card h3 {
                margin: 0;
                font-size: 30px;
                color: #1e2c22;
            }

            .visual-card p {
                margin: 8px 0 0;
                color: #5b665d;
                font-weight: 700;
            }
        </style>
    </head>

    <body>
        <div class="hero">
            <div class="hero-left">
                <div class="hero-label">Multi-Modal RAG Assistant</div>

                <div class="hero-title">
                    Khánh AI hỗ trợ <span>hỏi đáp tài liệu thông minh</span>
                </div>

                <div class="hero-desc">
                    Tải lên PDF, văn bản, hình ảnh, âm thanh hoặc video.
                    Hệ thống sẽ trích xuất nội dung, chia chunk, tạo embedding,
                    lưu vào vector database và dùng LLM để trả lời câu hỏi
                    dựa trên dữ liệu thật.
                </div>

                <div class="hero-actions">
                    <a class="btn-primary" target="_parent" href="#upload-section">Tải tài liệu lên</a>
                    <a class="btn-secondary" target="_parent" href="?page=register">Đăng ký tài khoản</a>
                </div>
            </div>

            <div class="hero-right">
                <div class="visual-circle">
                    <div class="visual-card">
                        <h3>Khánh AI</h3>
                        <p>PDF · Image · Audio · Video</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(html, height=530, scrolling=False)


def render_about():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #fbfaf6;
            }

            .section-card {
                background: white;
                border: 1px solid #e7e2d7;
                border-radius: 22px;
                padding: 32px;
                box-shadow: 0 18px 38px rgba(37, 72, 45, 0.08);
                margin-bottom: 28px;
            }

            h2 {
                color: #102217;
                font-weight: 900;
            }

            p {
                color: #4c5a50;
                line-height: 1.6;
            }

            .feature-list {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 22px;
                margin-top: 22px;
            }

            .feature-item {
                display: flex;
                gap: 16px;
                align-items: flex-start;
                padding: 20px;
                background: #f8fbf5;
                border: 1px solid #e1eadc;
                border-radius: 18px;
            }

            .feature-icon {
                width: 54px;
                height: 54px;
                border-radius: 50%;
                background: #4b8b55;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 26px;
                flex: 0 0 auto;
            }

            .feature-title {
                font-size: 19px;
                font-weight: 900;
                color: #17231c;
                margin-bottom: 6px;
            }

            .feature-desc {
                font-size: 15px;
                color: #5b665d;
                line-height: 1.55;
            }
        </style>
    </head>

    <body>
        <div class="section-card">
            <h2>Tại sao chọn Khánh AI?</h2>
            <p>
                Hệ thống được thiết kế để hỗ trợ hỏi đáp tài liệu, đọc dữ liệu đa phương thức
                và lưu lại lịch sử tương tác cho người quản trị.
            </p>

            <div class="feature-list">
                <div class="feature-item">
                    <div class="feature-icon">📄</div>
                    <div>
                        <div class="feature-title">Đọc nhiều loại dữ liệu</div>
                        <div class="feature-desc">Hỗ trợ PDF, TXT, ảnh, audio và video.</div>
                    </div>
                </div>

                <div class="feature-item">
                    <div class="feature-icon">🔎</div>
                    <div>
                        <div class="feature-title">Tìm kiếm theo ngữ cảnh</div>
                        <div class="feature-desc">Tìm đoạn liên quan trước khi trả lời.</div>
                    </div>
                </div>

                <div class="feature-item">
                    <div class="feature-icon">👤</div>
                    <div>
                        <div class="feature-title">Có tài khoản người dùng</div>
                        <div class="feature-desc">Đăng ký xong mới có thể đăng nhập vào hệ thống.</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(html, height=330, scrolling=False)


def render_footer():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #fbfaf6;
            }}

            .footer {{
                background: #050806;
                color: white;
                border-radius: 28px 28px 0 0;
                padding: 50px 46px;
                margin-top: 40px;
            }}

            .footer-grid {{
                display: grid;
                grid-template-columns: 1.2fr 1.4fr 1fr 1fr;
                gap: 36px;
            }}

            .footer-logo {{
                width: 150px;
                height: 84px;
                background: linear-gradient(135deg, #009846, #4fae54);
                border-radius: 22px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 950;
                font-size: 24px;
                margin-bottom: 20px;
            }}

            .footer-title {{
                color: #4b8b55;
                font-size: 21px;
                font-weight: 950;
                margin-bottom: 18px;
                letter-spacing: 1px;
            }}

            .footer-text {{
                color: #f1f5ef;
                font-size: 16px;
                line-height: 1.8;
            }}

            .social-dot {{
                width: 42px;
                height: 42px;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                margin-right: 12px;
                background: #367541;
                color: white;
                font-weight: 900;
            }}

            .floating-phone {{
                position: fixed;
                left: 18px;
                bottom: 28px;
                z-index: 9999;
                background: #ff1414;
                color: #fff200;
                padding: 16px 22px;
                border-radius: 999px;
                font-size: 22px;
                font-weight: 950;
                box-shadow: 0 10px 28px rgba(255, 0, 0, 0.28);
            }}
        </style>
    </head>

    <body>
        <div class="footer">
            <div class="footer-grid">
                <div>
                    <div class="footer-logo">🎋 Khánh AI</div>
                    <div class="footer-text">
                        Khánh AI Assistant hỗ trợ hỏi đáp tài liệu, đọc nội dung đa phương thức
                        và lưu dữ liệu tương tác để phục vụ quản trị hệ thống.
                    </div>
                    <br>
                    <span class="social-dot">f</span>
                    <span class="social-dot">G+</span>
                    <span class="social-dot">▶</span>
                </div>

                <div>
                    <div class="footer-title">LIÊN HỆ VỚI CHÚNG TÔI</div>
                    <div class="footer-text">
                        <b>Hệ thống RAG Assistant</b><br>
                        Địa chỉ: 102/114 Lê Văn Thọ, Phường 11, Quận Gò Vấp, Hồ Chí Minh<br><br>
                        Hotline: {HOTLINE}<br>
                        Email: admin@rag-assistant.local
                    </div>
                </div>

                <div>
                    <div class="footer-title">CHỨC NĂNG</div>
                    <div class="footer-text">
                        Upload tài liệu<br>
                        Upload ảnh<br>
                        Hỏi đáp dữ liệu<br>
                        Đánh giá nghiên cứu
                    </div>
                </div>

                <div>
                    <div class="footer-title">KẾT NỐI</div>
                    <div>
                        <span class="social-dot">AI</span>
                        <span class="social-dot">RAG</span>
                        <span class="social-dot">DB</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="floating-phone">☎ {HOTLINE}</div>
    </body>
    </html>
    """

    components.html(html, height=370, scrolling=False)


# =========================
# HELPERS
# =========================

def contains_chinese(text: str) -> bool:
    if not text:
        return False
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def force_vietnamese_text(text: str) -> str:
    if not text or not text.strip():
        return text

    if not contains_chinese(text):
        return text

    prompt = f"""
Bạn là hệ thống biên tập tiếng Việt.

Hãy viết lại nội dung sau HOÀN TOÀN bằng TIẾNG VIỆT.

YÊU CẦU:
- Không để lại chữ tiếng Trung.
- Dịch toàn bộ phần tiếng Trung sang tiếng Việt.
- Có thể giữ thuật ngữ kỹ thuật tiếng Anh như RAG, LLM, Vector Database, Retriever, Prompt.
- Không thêm thông tin mới.
- Không bịa thêm.
- Viết rõ ràng, dễ hiểu.

Nội dung:
{text}

Bản tiếng Việt:
"""

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0}
        )

        result = response.get("message", {}).get("content", "")
        return result.strip() if result and result.strip() else text

    except Exception:
        return text


def is_image_question(question: str) -> bool:
    if not question:
        return False

    q = question.lower()

    keywords = [
        "ảnh", "hình", "hình ảnh", "ảnh vừa tải", "hình vừa tải",
        "ảnh mới nhất", "hình mới nhất", "sơ đồ", "biểu đồ", "slide",
        "screenshot", "nội dung ảnh", "ảnh nói gì", "hình nói gì",
        "tóm tắt ảnh", "tóm tắt hình", "giải thích ảnh",
        "giải thích hình", "giải thích sơ đồ", "trong ảnh", "trong hình"
    ]

    return any(keyword in q for keyword in keywords)


def get_search_target(keyword: str):
    q = keyword.lower().strip()

    mapping = {
        "upload": "#upload-section",
        "tải file": "#upload-section",
        "file": "#upload-section",
        "pdf": "#upload-section",
        "ảnh": "#image-upload-section",
        "hình": "#image-upload-section",
        "chat": "#chatbot-section",
        "chatbot": "#chatbot-section",
        "hỏi đáp": "#chatbot-section",
        "tài khoản": "?page=login",
        "đăng nhập": "?page=login",
        "đăng ký": "?page=register",
        "gmail": "?page=register",
        "avatar": "?page=register",
        "ảnh đại diện": "?page=register",
        "đánh giá": "#evaluation-section",
        "evaluation": "#evaluation-section",
        "report": "#report-section",
        "báo cáo": "#report-section",
    }

    for key, target in mapping.items():
        if key in q:
            return target

    return ""


# =========================
# AUTH PAGES
# =========================

def render_login_page():
    render_header()

    st.markdown("### Trang chủ / Đăng nhập tài khoản")

    st.markdown("## Đăng nhập")
    st.info("Nếu bạn chưa có tài khoản, hãy đăng ký trước.")

    login_col1, login_col2, login_col3 = st.columns([1, 1.15, 1])

    with login_col2:
        with st.form("login_form"):
            login_email = st.text_input("Email")
            login_password = st.text_input("Mật khẩu", type="password")
            login_submit = st.form_submit_button("ĐĂNG NHẬP")

            if login_submit:
                user = find_user_by_email_password(login_email, login_password)

                if user is None:
                    st.error("Email hoặc mật khẩu không đúng. Nếu chưa có tài khoản, vui lòng đăng ký trước.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user_name = str(user.get("full_name", "")).strip()
                    st.session_state.user_email = str(user.get("email", "")).strip()
                    st.session_state.user_phone = str(user.get("phone", "")).strip()
                    st.session_state.profile_link = str(user.get("profile_link", "")).strip()
                    st.session_state.avatar_path = str(user.get("avatar_path", "")).strip()

                    st.success("Đăng nhập thành công.")
                    st.query_params["page"] = "home"
                    st.rerun()

        st.markdown("[Chưa có tài khoản? Đăng ký tại đây](?page=register)")


def render_register_page():
    render_header()

    st.markdown("### Trang chủ / Đăng ký tài khoản")

    st.markdown("## Đăng ký")
    st.info("Đăng ký tài khoản để có thể đăng nhập vào website.")

    reg_col1, reg_col2, reg_col3 = st.columns([1, 1.15, 1])

    with reg_col2:
        with st.form("register_form"):
            first_name = st.text_input("Họ")
            last_name = st.text_input("Tên")
            reg_email = st.text_input("Email")
            reg_phone = st.text_input("Số điện thoại")
            reg_profile_link = st.text_input("Link trang cá nhân")
            reg_password = st.text_input("Mật khẩu", type="password")
            reg_avatar = st.file_uploader(
                "Ảnh đại diện",
                type=["png", "jpg", "jpeg", "webp"],
                key="register_avatar"
            )

            register_submit = st.form_submit_button("ĐĂNG KÝ")

            if register_submit:
                if not first_name.strip():
                    st.warning("Vui lòng nhập họ.")
                elif not last_name.strip():
                    st.warning("Vui lòng nhập tên.")
                elif not reg_email.strip():
                    st.warning("Vui lòng nhập email.")
                elif not reg_password.strip():
                    st.warning("Vui lòng nhập mật khẩu.")
                elif email_exists(reg_email):
                    st.error("Email này đã được đăng ký. Vui lòng đăng nhập.")
                else:
                    avatar_path = save_avatar(reg_avatar, reg_email)

                    save_user_register(
                        first_name=first_name,
                        last_name=last_name,
                        email=reg_email,
                        phone=reg_phone,
                        password=reg_password,
                        profile_link=reg_profile_link,
                        avatar_path=avatar_path
                    )

                    st.success("Đăng ký thành công. Bây giờ bạn có thể đăng nhập.")
                    st.query_params["page"] = "login"
                    st.rerun()

        st.markdown("[Đã có tài khoản? Đăng nhập tại đây](?page=login)")


# =========================
# SIDEBAR
# =========================

with st.sidebar:
    st.markdown("### Tài khoản nhanh")

    if st.session_state.avatar_path and os.path.exists(st.session_state.avatar_path):
        st.image(st.session_state.avatar_path, width=120)

    if st.session_state.logged_in:
        st.success(f"Xin chào, {st.session_state.user_name}")
        st.write(f"Email: {st.session_state.user_email}")
        st.write(f"SĐT: {st.session_state.user_phone}")

        if st.session_state.profile_link:
            st.write(f"Link: {st.session_state.profile_link}")

        if st.button("Đăng xuất"):
            st.session_state.logged_in = False
            st.session_state.user_name = ""
            st.session_state.user_email = ""
            st.session_state.user_phone = ""
            st.session_state.profile_link = ""
            st.session_state.avatar_path = ""
            st.rerun()
    else:
        st.info("Bạn có thể đăng nhập hoặc đăng ký ở mục Tài khoản.")

    st.markdown("---")
    st.markdown("### Quản trị viên")

    admin_input = st.text_input(
        "Mật khẩu admin",
        type="password",
        key="admin_password_input"
    )

    if st.button("Đăng nhập admin"):
        if admin_input == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.success("Đã đăng nhập admin.")
            st.rerun()
        else:
            st.error("Sai mật khẩu admin.")

    if st.session_state.admin_logged_in:
        st.success("Admin đang hoạt động.")

        if st.button("Đăng xuất admin"):
            st.session_state.admin_logged_in = False
            st.rerun()

    st.markdown("---")
    st.markdown("### Cấu hình")
    st.write(f"LLM: `{LLM_MODEL}`")
    st.write(f"Embedding: `{EMBED_MODEL}`")
    st.write(f"Chunk size: `{CHUNK_SIZE}`")
    st.write(f"Overlap: `{CHUNK_OVERLAP}`")
    st.write(f"n_results: `{N_RESULTS}`")
    st.write(f"Temperature: `{TEMPERATURE}`")

    if st.button("Xóa lịch sử trò chuyện"):
        st.session_state.messages = []
        st.rerun()

    if st.button("Xóa dữ liệu phiên hiện tại"):
        st.session_state.messages = []
        st.session_state.collection = None
        st.session_state.file_name = ""
        st.session_state.file_type = ""
        st.session_state.extracted_text = ""
        st.session_state.chunk_count = 0
        st.session_state.chat_image_name = ""
        st.session_state.last_image_text = ""
        st.rerun()


# =========================
# ROUTE PAGE
# =========================

if current_page == "login":
    render_login_page()
    st.stop()

if current_page == "register":
    render_register_page()
    st.stop()


# =========================
# HOME PAGE
# =========================

render_header()


# SEARCH

st.markdown('<div id="search-section"></div>', unsafe_allow_html=True)

search_col1, search_col2 = st.columns([3, 1])

with search_col1:
    search_keyword = st.text_input(
        "Tìm kiếm nhanh chức năng",
        placeholder="Ví dụ: upload file, upload ảnh, chatbot, đăng nhập, đăng ký, đánh giá..."
    )

with search_col2:
    st.write("")
    st.write("")
    search_clicked = st.button("Tìm kiếm")

if search_clicked and search_keyword:
    target = get_search_target(search_keyword)

    if target:
        st.success("Đã tìm thấy chức năng phù hợp.")
        st.markdown(f"[Bấm vào đây để đi tới mục cần tìm]({target})")
    else:
        st.warning("Chưa tìm thấy mục phù hợp. Hãy thử: upload, ảnh, chatbot, đăng nhập, đăng ký, đánh giá.")


# HERO

st.markdown('<div id="home-section"></div>', unsafe_allow_html=True)
render_hero()


# ABOUT

st.markdown('<div id="about-section"></div>', unsafe_allow_html=True)
render_about()


# UPLOAD FILE

st.markdown('<div id="upload-section"></div>', unsafe_allow_html=True)
st.markdown("## 1. Tải file lên hệ thống")

uploaded_file = st.file_uploader(
    "Chọn file PDF, TXT, ảnh, audio hoặc video",
    type=[
        "pdf", "txt",
        "png", "jpg", "jpeg", "webp",
        "mp3", "wav", "m4a",
        "mp4", "mov", "avi", "mkv"
    ],
    key="main_file_uploader"
)

if uploaded_file is not None:
    if st.session_state.file_name != uploaded_file.name:
        st.session_state.collection = None
        st.session_state.messages = []
        st.session_state.file_name = uploaded_file.name
        st.session_state.file_type = ""
        st.session_state.extracted_text = ""
        st.session_state.chunk_count = 0
        st.session_state.last_image_text = ""
        st.session_state.chat_image_name = ""

    if st.session_state.collection is None:
        with st.spinner("Đang kiểm tra và xử lý file..."):
            file_type, text, status_message = extract_text_from_file(uploaded_file)

            st.session_state.file_type = file_type
            st.session_state.extracted_text = text

            if not text.strip():
                st.error(status_message)
            else:
                chunks = chunk_text(text)

                if not chunks:
                    st.error("Không tạo được chunk từ nội dung đã trích xuất.")
                else:
                    try:
                        collection = create_vector_db(chunks)

                        st.session_state.collection = collection
                        st.session_state.chunk_count = len(chunks)

                        st.success(status_message)
                        st.info(f"Loại dữ liệu: {file_type} | Số chunk đã tạo: {len(chunks)}")

                        save_upload_log(uploaded_file.name, file_type, len(chunks))

                    except Exception as e:
                        st.error(f"Lỗi khi tạo vector database: {e}")

if st.session_state.file_name:
    st.info(
        f"File đang sử dụng: {st.session_state.file_name} | "
        f"Loại: {st.session_state.file_type} | "
        f"Số chunk: {st.session_state.chunk_count}"
    )

    with st.expander("Xem nội dung đã trích xuất"):
        if st.session_state.extracted_text:
            st.text_area(
                "Nội dung trích xuất",
                value=st.session_state.extracted_text[:5000],
                height=300
            )

            if len(st.session_state.extracted_text) > 5000:
                st.info("Nội dung dài hơn 5000 ký tự, chỉ đang hiển thị phần đầu.")
        else:
            st.write("Chưa có nội dung được trích xuất.")


# CHATBOT

st.markdown('<div id="chatbot-section"></div>', unsafe_allow_html=True)
st.markdown("## 2. Hỏi đáp với dữ liệu")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

st.markdown('<div id="image-upload-section"></div>', unsafe_allow_html=True)
st.markdown("### Tải ảnh nhanh trong phần hỏi đáp")

chat_image = st.file_uploader(
    "Chọn ảnh để hỏi nhanh",
    type=["png", "jpg", "jpeg", "webp"],
    key="chat_image_uploader"
)

if chat_image is not None:
    if st.session_state.chat_image_name != chat_image.name:
        st.session_state.chat_image_name = chat_image.name

        with st.spinner("Đang đọc nội dung ảnh và thêm vào dữ liệu hiện tại..."):
            file_type, image_text, status_message = extract_text_from_file(chat_image)

            if not image_text.strip():
                st.error(status_message)

            elif image_text.startswith("[VISION ERROR]"):
                st.error(image_text)

            else:
                image_text = force_vietnamese_text(image_text)
                st.session_state.last_image_text = image_text

                if st.session_state.extracted_text.strip():
                    combined_text = (
                        st.session_state.extracted_text
                        + "\n\n==============================\n"
                        + "NGUỒN: ẢNH BỔ SUNG\n"
                        + "==============================\n"
                        + image_text
                    )
                else:
                    combined_text = (
                        "==============================\n"
                        + "NGUỒN: ẢNH BỔ SUNG\n"
                        + "==============================\n"
                        + image_text
                    )

                st.session_state.extracted_text = combined_text
                st.session_state.file_type = "Combined Data"

                if st.session_state.file_name:
                    st.session_state.file_name = (
                        st.session_state.file_name + " + " + chat_image.name
                    )
                else:
                    st.session_state.file_name = chat_image.name

                chunks = chunk_text(combined_text)

                if not chunks:
                    st.error("Không tạo được chunk từ nội dung ảnh.")
                else:
                    try:
                        collection = create_vector_db(chunks)

                        st.session_state.collection = collection
                        st.session_state.chunk_count = len(chunks)

                        st.success("Đã xử lý ảnh và thêm vào dữ liệu hiện tại.")
                        st.info(f"Đã cập nhật dữ liệu | Số chunk mới: {len(chunks)}")

                        save_upload_log(chat_image.name, "Image bổ sung", len(chunks))

                    except Exception as e:
                        st.error(f"Lỗi khi tạo vector database sau khi thêm ảnh: {e}")

if st.session_state.last_image_text:
    with st.expander("Xem nội dung ảnh mới nhất đã trích xuất"):
        fixed_image_text = force_vietnamese_text(st.session_state.last_image_text)
        st.session_state.last_image_text = fixed_image_text

        st.text_area(
            "Nội dung ảnh",
            value=fixed_image_text[:5000],
            height=260
        )

question = st.chat_input("Nhập câu hỏi của bạn về file hoặc ảnh đã tải lên...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.write(question)

    if st.session_state.collection is None:
        answer = "Bạn cần tải file hoặc ảnh lên và chờ hệ thống xử lý xong trước khi đặt câu hỏi."

    else:
        direct_answer = direct_answer_from_text(
            question=question,
            extracted_text=st.session_state.extracted_text
        )

        if direct_answer:
            answer = direct_answer

        elif is_image_question(question) and st.session_state.last_image_text.strip():
            image_context = force_vietnamese_text(st.session_state.last_image_text)
            st.session_state.last_image_text = image_context

            with st.expander("Xem nội dung ảnh đã trích xuất", expanded=True):
                st.text_area(
                    "Nội dung ảnh",
                    value=image_context,
                    height=260
                )

            if image_context.startswith("[VISION ERROR]"):
                answer = "Không thể phân tích ảnh vì model đọc ảnh đang lỗi:\n\n" + image_context

            else:
                image_question = f"""
Chỉ dựa trên nội dung ảnh đã trích xuất dưới đây để trả lời bằng tiếng Việt.

Câu hỏi: {question}

Nội dung ảnh:
{image_context}

Yêu cầu:
- Trả lời đúng trọng tâm câu hỏi.
- Nếu là sơ đồ thì giải thích theo luồng.
- Không bịa thêm thông tin ngoài nội dung ảnh.
"""
                answer = generate_answer(
                    image_question,
                    [image_context]
                )

        else:
            with st.spinner("Đang tìm thông tin liên quan và tạo câu trả lời..."):
                retrieved_chunks = retrieve_chunks(
                    collection=st.session_state.collection,
                    question=question,
                    n_results=N_RESULTS
                )

                if st.session_state.last_image_text.strip():
                    fixed_image_text = force_vietnamese_text(st.session_state.last_image_text)
                    st.session_state.last_image_text = fixed_image_text
                    retrieved_chunks = [fixed_image_text] + retrieved_chunks

                with st.expander("Xem các đoạn dữ liệu chatbot đã tìm thấy"):
                    for i, chunk in enumerate(retrieved_chunks, start=1):
                        st.markdown(f"**Chunk {i}:**")
                        st.text_area(
                            f"Nội dung chunk {i}",
                            value=chunk[:1200],
                            height=180
                        )
                        st.markdown("---")

                combined_question = f"""
Trả lời bằng tiếng Việt dựa trên dữ liệu đã truy xuất.
Nếu có nội dung ảnh thì hãy kết hợp cả nội dung ảnh và nội dung file.
Câu hỏi: {question}
"""

                answer = generate_answer(combined_question, retrieved_chunks)

    answer = force_vietnamese_text(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

    save_chat_log(question, answer)

    with st.chat_message("assistant"):
        st.write(answer)


# EVALUATION

st.markdown('<div id="evaluation-section"></div>', unsafe_allow_html=True)
st.markdown("## 3. Chế độ đánh giá nghiên cứu")

st.markdown(
    """
    Chế độ này dùng file `evaluation_questions.csv` để chạy một bộ câu hỏi test.
    Kết quả sẽ được lưu vào `evaluation_results.csv`.
    """
)

if st.button("Chạy đánh giá nghiên cứu"):
    if st.session_state.collection is None:
        st.warning("Bạn cần upload và xử lý file trước khi chạy đánh giá.")
    else:
        try:
            with st.spinner("Đang chạy bộ câu hỏi đánh giá..."):
                result_df = run_evaluation(
                    collection=st.session_state.collection,
                    questions_csv_path="evaluation_questions.csv"
                )

            st.success("Đã chạy đánh giá xong. Kết quả lưu tại evaluation_results.csv")
            st.dataframe(result_df)

        except FileNotFoundError:
            st.error("Chưa tìm thấy file evaluation_questions.csv.")
        except Exception as e:
            st.error(f"Lỗi khi chạy đánh giá: {e}")


# REPORT ADMIN

if st.session_state.admin_logged_in:
    st.markdown('<div id="report-section"></div>', unsafe_allow_html=True)
    st.markdown("## 4. Báo cáo dữ liệu người dùng")

    users_df = read_csv_safe(USERS_CSV)
    uploads_df = read_csv_safe(UPLOAD_LOG_CSV)
    chats_df = read_csv_safe(CHAT_LOG_CSV)

    tab1, tab2, tab3 = st.tabs([
        "Người dùng",
        "Upload",
        "Hỏi đáp"
    ])

    with tab1:
        st.dataframe(users_df, use_container_width=True)

        if not users_df.empty:
            st.download_button(
                "Tải users.csv",
                data=users_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="users.csv",
                mime="text/csv"
            )

    with tab2:
        st.dataframe(uploads_df, use_container_width=True)

        if not uploads_df.empty:
            st.download_button(
                "Tải upload_logs.csv",
                data=uploads_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="upload_logs.csv",
                mime="text/csv"
            )

    with tab3:
        st.dataframe(chats_df, use_container_width=True)

        if not chats_df.empty:
            st.download_button(
                "Tải chat_logs.csv",
                data=chats_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="chat_logs.csv",
                mime="text/csv"
            )


# FOOTER

st.markdown('<div id="footer-section"></div>', unsafe_allow_html=True)
render_footer()