import streamlit as st
import json
import os
import datetime
from typing import List, Dict, Any
import google.generativeai as genai

# ==========================================
# 1. 기본 설정 및 Gemini AI 초기화
# ==========================================
st.set_page_config(
    page_title="AI 성경 관주 & 통독 연구소",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 키 가져오기 (Secrets 또는 환경변수 우선, 없으면 사이드바 입력)
api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

with st.sidebar:
    st.header("⚙️ 환경 설정")
    if not api_key:
        api_key = st.text_input("Gemini API Key 입력", type="password", help="Google AI Studio에서 발급받은 API 키를 입력하세요.")
    
    if api_key:
        genai.configure(api_key=api_key)
    else:
        st.warning("⚠️ Gemini API Key를 입력해야 AI 분석을 사용할 수 있습니다.")

# ==========================================
# 2. 세션 상태 (Session State) 초기화
# ==========================================
if "verse_chats" not in st.session_state:
    st.session_state.verse_chats = {}

if "general_chats" not in st.session_state:
    st.session_state.general_chats = []

if "active_verse" not in st.session_state:
    st.session_state.active_verse = None

# ==========================================
# 3. 유연한 성경 데이터 파서 (Multi-Format & Auto Path)
# ==========================================
def parse_raw_json(raw_data: Any) -> List[Dict[str, Any]]:
    normalized = []
    if not raw_data:
        return normalized

    try:
        # Case A: 리스트 구조 [{ "book": ..., "chapter": ..., ... }]
        if isinstance(raw_data, list):
            for item in raw_data:
                if not isinstance(item, dict):
                    continue
                book = item.get("book") or item.get("book_name") or item.get("name") or item.get("b", "미분류")
                chap = int(item.get("chapter") or item.get("chap") or item.get("c", 1))
                verse = int(item.get("verse") or item.get("ver") or item.get("v", 1))
                text = item.get("text") or item.get("content") or item.get("t") or item.get("message", "")
                cross = item.get("cross_references") or item.get("cross_refs") or item.get("references") or []
                
                normalized.append({
                    "book": str(book).strip(),
                    "chapter": chap,
                    "verse": verse,
                    "text": str(text).strip(),
                    "cross_refs": cross if isinstance(cross, list) else []
                })

        # Case B: 딕셔너리 구조 ({ "창세기": { "1": { "1": "..." } } } 등)
        elif isinstance(raw_data, dict):
            # 혹시 상위 키에 "bible"이나 "verses" 같은 래퍼가 있는 경우 대응
            if "bible" in raw_data and isinstance(raw_data["bible"], (list, dict)):
                return parse_raw_json(raw_data["bible"])
            if "verses" in raw_data and isinstance(raw_data["verses"], list):
                return parse_raw_json(raw_data["verses"])

            for b_name, b_val in raw_data.items():
                if isinstance(b_val, dict):
                    for c_num, c_val in b_val.items():
                        try:
                            c_int = int(c_num)
                        except ValueError:
                            continue
                        if isinstance(c_val, dict):
                            for v_num, v_val in c_val.items():
                                try:
                                    v_int = int(v_num)
                                except ValueError:
                                    continue
                                v_text = v_val if isinstance(v_val, str) else v_val.get("text", "")
                                cross = v_val.get("cross_refs", []) if isinstance(v_val, dict) else []
                                normalized.append({
                                    "book": str(b_name).strip(),
                                    "chapter": c_int,
                                    "verse": v_int,
                                    "text": str(v_text).strip(),
                                    "cross_refs": cross
                                })
                        elif isinstance(c_val, list):
                            for idx, v_text in enumerate(c_val, start=1):
                                normalized.append({
                                    "book": str(b_name).strip(),
                                    "chapter": c_int,
                                    "verse": idx,
                                    "text": str(v_text).strip() if isinstance(v_text, str) else str(v_text.get("text", "")),
                                    "cross_refs": []
                                })
    except Exception as e:
        st.sidebar.error(f"데이터 정규화 중 오류: {e}")
    
    return normalized

def load_bible_from_disk() -> List[Dict[str, Any]]:
    # 다양한 가능 경로 탐색
    candidate_paths = [
        "bible.json",
        "Bible.json",
        "data/bible.json",
        "data/Bible.json",
        "src/bible.json",
        "assets/bible.json"
    ]
    encodings = ["utf-8-sig", "utf-8", "cp949"]
    
    for path in candidate_paths:
        if os.path.exists(path):
            for enc in encodings:
                try:
                    with open(path, "r", encoding=enc) as f:
                        raw = json.load(f)
                        parsed = parse_raw_json(raw)
                        if parsed:
                            return parsed
                except Exception:
                    continue
    return []

# 사이드바 성경 파일 업로드 옵션 제공
with st.sidebar:
    st.markdown("---")
    st.subheader("📁 성경 데이터")
    uploaded_file = st.file_uploader("bible.json 직접 업로드 (선택)", type=["json"])

# 데이터 로드 로직
if uploaded_file is not None:
    try:
        raw_uploaded = json.load(uploaded_file)
        bible_data = parse_raw_json(raw_uploaded)
        st.sidebar.success(f"✅ 업로드 파일 로드 완료 ({len(bible_data):,} 구절)")
    except Exception as e:
        st.sidebar.error(f"업로드 파일 파싱 실패: {e}")
        bible_data = []
else:
    bible_data = load_bible_from_disk()
    if bible_data:
        st.sidebar.success(f"📖 bible.json 연동 성공 ({len(bible_data):,} 구절)")

# 파일이 전혀 없거나 로드 실패 시 테스트용 기본 샘플 로드
if not bible_data:
    st.sidebar.info("💡 성경 파일 로드 실패/부재로 샘플 데이터가 작동합니다.")
    bible_data = [
        {"book": "창세기", "chapter": 1, "verse": 1, "text": "태초에 하나님이 천지를 창조하시니라.", "cross_refs": ["요한복음 1:1-3", "히브리서 11:3", "시편 33:6"]},
        {"book": "창세기", "chapter": 1, "verse": 2, "text": "땅이 혼돈하고 공허하며 흑암이 깊음 위에 있고 하나님의 영은 수면 위에 운행하시니라.", "cross_refs": ["예레미야 4:23", "시편 104:30"]},
        {"book": "창세기", "chapter": 1, "verse": 3, "text": "하나님이 이르시되 빛이 있으라 하시니 빛이 있었고", "cross_refs": ["고린도후서 4:6", "시편 33:9"]},
        {"book": "창세기", "chapter": 2, "verse": 1, "text": "천지와 만물이 다 이루어지니라.", "cross_refs": ["출애굽기 20:11"]},
        {"book": "요한복음", "chapter": 1, "verse": 1, "text": "태초에 말씀이 계시니라 이 말씀이 하나님과 함께 계셨으니 이 말씀은 곧 하나님이시니라.", "cross_refs": ["창세기 1:1", "요한일서 1:1"]}
    ]

# ==========================================
# 4. 버그 수정된 통독 스케줄 알고리즘
# ==========================================
def get_chapters_list(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chapters = []
    seen = set()
    for row in data:
        key = (row["book"], row["chapter"])
        if key not in seen:
            seen.add(key)
            chapters.append({"book": row["book"], "chapter": row["chapter"]})
    return chapters

all_chapters = get_chapters_list(bible_data)
total_chapters = len(all_chapters)

with st.sidebar:
    st.markdown("---")
    st.subheader("📅 통독 스케줄러")
    target_days = st.number_input("목표 통독 일수", min_value=1, max_value=365, value=90, step=5)
    start_date = st.date_input("통독 시작일", value=datetime.date.today())
    
    # 일차 계산
    days_passed = (datetime.date.today() - start_date).days + 1
    current_day = max(1, min(days_passed, target_days))
    
    selected_day = st.slider("읽을 일차 선택", min_value=1, max_value=target_days, value=current_day)
    st.caption(f"📌 오늘은 시작일로부터 **{days_passed}일차**입니다.")

# ⚠️ 버그 수정: 장 수가 목표 일수보다 적더라도 최소 1장 이상 배정되도록 개선
def get_day_chapters(target_day: int, total_d: int, chaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not chaps:
        return []
    total_ch = len(chaps)
    
    # 장 수가 목표 일수 이하일 경우 (샘플 모드 등): 하루 1장씩 보여주고, 초과 시 전체 순환
    if total_ch <= total_d:
        idx = (target_day - 1) % total_ch
        return [chaps[idx]]
    
    # 일반적인 통독 분할 로직 (총 장 수가 더 많을 때)
    start_idx = int((target_day - 1) * total_ch / total_d)
    end_idx = int(target_day * total_ch / total_d)
    
    if target_day == total_d:
        end_idx = total_ch
        
    # start와 end가 같아져 빈 리스트가 되는 현상 방지
    if start_idx >= end_idx and start_idx < total_ch:
        end_idx = start_idx + 1
        
    return chaps[start_idx:end_idx]

today_chapters = get_day_chapters(selected_day, target_days, all_chapters)

# ==========================================
# 5. Gemini API 질의 헬퍼 함수
# ==========================================
def query_gemini(prompt: str, history: List[Dict[str, Any]] = None) -> str:
    if not api_key:
        return "⚠️ 좌측 사이드바에 Gemini API Key를 입력해주세요."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        messages = []
        if history:
            for h in history:
                role = "user" if h["role"] == "user" else "model"
                messages.append({"role": role, "parts": [h["content"]]})
        
        messages.append({"role": "user", "parts": [prompt]})
        response = model.generate_content(messages)
        return response.text
    except Exception as e:
        return f"❌ Gemini API 오류: {str(e)}"

# ==========================================
# 6. 메인 화면 UI
# ==========================================
st.title("🕊️ AI 성경 관주 & 통독 연구소")

tab_reading, tab_general_chat, tab_history = st.tabs([
    "📖 성경 통독 & 구절 연구",
    "💬 자유 성경 AI Q&A",
    "📜 AI 질의응답 기록 보관소"
])

# ------------------------------------------
# TAB 1: 통독 본문 & 구절 AI 대화
# ------------------------------------------
with tab_reading:
    if st.session_state.active_verse is not None:
        v = st.session_state.active_verse
        v_key = f"{v['book']} {v['chapter']}:{v['verse']}"
        
        c
