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
        st.warning("⚠️ Gemini API Key를 등록해야 AI 분석 기능을 사용할 수 있습니다.")

# ==========================================
# 2. 세션 상태 (Session State) 초기화
# ==========================================
if "verse_chats" not in st.session_state:
    # 구조: { "verse_key": [{"role": "user"|"assistant", "content": str, "timestamp": datetime}] }
    # verse_key 형식: "창세기 1:1"
    st.session_state.verse_chats = {}

if "general_chats" not in st.session_state:
    # 구조: [{"role": "user"|"assistant", "content": str, "timestamp": datetime}]
    st.session_state.general_chats = []

if "active_verse" not in st.session_state:
    # 현재 AI 대화 중인 구절 객체 (None이면 통독 본문 표시)
    st.session_state.active_verse = None

# ==========================================
# 3. 성경 데이터 파서 (Multi-Format & Encoding)
# ==========================================
@st.cache_data
def load_bible() -> List[Dict[str, Any]]:
    file_path = "bible.json"
    encodings = ["utf-8-sig", "utf-8", "cp949"]
    raw_data = None

    if os.path.exists(file_path):
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    raw_data = json.load(f)
                    break
            except Exception:
                continue

    normalized = []
    
    if raw_data:
        try:
            # Case A: 리스트 구조
            if isinstance(raw_data, list):
                for item in raw_data:
                    book = item.get("book") or item.get("book_name") or item.get("name", "알 수 없음")
                    chap = int(item.get("chapter") or item.get("chap") or item.get("c", 1))
                    verse = int(item.get("verse") or item.get("ver") or item.get("v", 1))
                    text = item.get("text") or item.get("content") or item.get("t", "")
                    cross = item.get("cross_references") or item.get("cross_refs") or item.get("references") or []
                    normalized.append({
                        "book": str(book).strip(),
                        "chapter": chap,
                        "verse": verse,
                        "text": str(text).strip(),
                        "cross_refs": cross
                    })
            # Case B: 딕셔너리 구조 ({ "창세기": { "1": { "1": "태초에..." } } } 등)
            elif isinstance(raw_data, dict):
                for b_name, b_val in raw_data.items():
                    if isinstance(b_val, dict):
                        for c_num, c_val in b_val.items():
                            if isinstance(c_val, dict):
                                for v_num, v_val in c_val.items():
                                    v_text = v_val if isinstance(v_val, str) else v_val.get("text", "")
                                    cross = v_val.get("cross_refs", []) if isinstance(v_val, dict) else []
                                    normalized.append({
                                        "book": str(b_name).strip(),
                                        "chapter": int(c_num),
                                        "verse": int(v_num),
                                        "text": str(v_text).strip(),
                                        "cross_refs": cross
                                    })
                            elif isinstance(c_val, list):
                                for idx, v_text in enumerate(c_val, start=1):
                                    normalized.append({
                                        "book": str(b_name).strip(),
                                        "chapter": int(c_num),
                                        "verse": idx,
                                        "text": str(v_text).strip(),
                                        "cross_refs": []
                                    })
        except Exception as e:
            st.sidebar.error(f"파싱 중 오류 발생: {e}")

    # 데이터가 비어있을 경우 시뮬레이션용 폴백 데이터 탑재
    if not normalized:
        normalized = [
            {"book": "창세기", "chapter": 1, "verse": 1, "text": "태초에 하나님이 천지를 창조하시니라.", "cross_refs": ["요한복음 1:1-3", "히브리서 11:3", "시편 33:6"]},
            {"book": "창세기", "chapter": 1, "verse": 2, "text": "땅이 혼돈하고 공허하며 흑암이 깊음 위에 있고 하나님의 영은 수면 위에 운행하시니라.", "cross_refs": ["예레미야 4:23", "시편 104:30"]},
            {"book": "창세기", "chapter": 1, "verse": 3, "text": "하나님이 이르시되 빛이 있으라 하시니 빛이 있었고", "cross_refs": ["고린도후서 4:6", "시편 33:9"]},
            {"book": "창세기", "chapter": 2, "verse": 1, "text": "천지와 만물이 다 이루어지니라.", "cross_refs": ["출애굽기 20:11"]},
            {"book": "요한복음", "chapter": 1, "verse": 1, "text": "태초에 말씀이 계시니라 이 말씀이 하나님과 함께 계셨으니 이 말씀은 곧 하나님이시니라.", "cross_refs": ["창세기 1:1", "요한일서 1:1"]}
        ]
        st.sidebar.info("💡 bible.json 로드 실패 또는 파일 부재로 샘플 데이터가 동작합니다.")
    else:
        st.sidebar.success(f"📖 성경 데이터 로드 완료 ({len(normalized):,} 구절)")

    return normalized

bible_data = load_bible()

# ==========================================
# 4. 통독 스케줄 알고리즘 (장 단위 분할)
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

# 사이드바 통독 플랜 설정
with st.sidebar:
    st.markdown("---")
    st.subheader("📅 통독 스케줄러")
    target_days = st.number_input("목표 통독 일수", min_value=1, max_value=365, value=90, step=5)
    start_date = st.date_input("통독 시작일", value=datetime.date.today())
    
    # 오늘 일차 계산
    days_passed = (datetime.date.today() - start_date).days + 1
    current_day = max(1, min(days_passed, target_days))
    
    selected_day = st.slider("읽을 일차 선택", min_value=1, max_value=target_days, value=current_day)
    st.caption(f"📌 오늘은 시작일로부터 **{days_passed}일차**입니다.")

# 일자별 장 배분 계산
def get_day_chapters(target_day: int, total_d: int, chaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not chaps:
        return []
    total_ch = len(chaps)
    ch_per_day = total_ch / total_d
    start_idx = int((target_day - 1) * ch_per_day)
    end_idx = int(target_day * ch_per_day) if target_day < total_d else total_ch
    return chaps[start_idx:end_idx]

today_chapters = get_day_chapters(selected_day, target_days, all_chapters)

# ==========================================
# 5. Gemini API 질의 헬퍼 함수
# ==========================================
def query_gemini(prompt: str, history: List[Dict[str, Any]] = None) -> str:
    if not api_key:
        return "⚠️ 사이드바에 Gemini API Key를 입력해야 AI 답변을 받을 수 있습니다."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # 이전 멀티턴 대화 컨텍스트 구성
        messages = []
        if history:
            for h in history:
                role = "user" if h["role"] == "user" else "model"
                messages.append({"role": role, "parts": [h["content"]]})
        
        messages.append({"role": "user", "parts": [prompt]})
        
        response = model.generate_content(messages)
        return response.text
    except Exception as e:
        return f"❌ Gemini API 요청 오류: {str(e)}"

# ==========================================
# 6. 메인 UI 및 탭 구성
# ==========================================
st.title("🕊️ AI 성경 관주 & 통독 연구소")

tab_reading, tab_general_chat, tab_history = st.tabs([
    "📖 성경 통독 & 구절 연구",
    "💬 자유 성경 AI Q&A",
    "📜 AI 질의응답 기록 보관소"
])

# ------------------------------------------
# TAB 1: 성경 통독 본문 및 구절별 AI 대화
# ------------------------------------------
with tab_reading:
    # 1) 특정 구절 AI 심층 대화 모드 활성화 시
    if st.session_state.active_verse is not None:
        v = st.session_state.active_verse
        v_key = f"{v['book']} {v['chapter']}:{v['verse']}"
        
        col_back, col_title = st.columns([1, 6])
        with col_back:
            if st.button("⬅️ 본문으로 돌아가기"):
                st.session_state.active_verse = None
                st.rerun()
        with col_title:
            st.subheader(f"🔍 구절 집중 연구 & AI 대화: {v_key}")

        # 본문 및 관주 박스
        st.info(f"**[{v_key}]** {v['text']}")
        if v.get("cross_refs"):
            st.caption(f"🔗 **관련 관주 구절:** {', '.join(v['cross_refs'])}")

        st.markdown("---")

        # 해당 구절의 대화 히스토리 초기화 (최초 1회 자동 생성)
        if v_key not in st.session_state.verse_chats or len(st.session_state.verse_chats[v_key]) == 0:
            with st.spinner("AI가 본문과 관주를 종합 분석하여 신학적 의미를 도출하는 중입니다..."):
                initial_prompt = (
                    f"너는 복음주의적 관점과 학문적 깊이를 지닌 성경 주석가이자 신학자야.\n"
                    f"아래의 성경 구절과 관련 관주를 종합적으로 분석해서, 이 구절의 깊은 문맥적 의미와 신학적 핵심, "
                    f"그리고 성도들에게 주는 실제적인 적용점을 3~4개의 명확한 단락으로 설명해 줘.\n\n"
                    f"구절: {v_key} \"{v['text']}\"\n"
                    f"관련 관주: {', '.join(v['cross_refs']) if v.get('cross_refs') else '관주 없음'}"
                )
                first_answer = query_gemini(initial_prompt)
                
                st.session_state.verse_chats[v_key] = [
                    {"role": "user", "content": "이 구절과 관주를 종합해 어떤 의미인지 설명해 줘.", "timestamp": datetime.datetime.now()},
                    {"role": "assistant", "content": first_answer, "timestamp": datetime.datetime.now()}
                ]

        # 이전 대화 렌더링
        for msg in st.session_state.verse_chats[v_key]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                st.caption(msg["timestamp"].strftime("%H:%M:%S"))

        # 후속 대화 입력창 (계속 이어나가면서 질문 가능)
        user_followup = st.chat_input(f"[{v_key}]에 대해 추가로 궁금한 점을 질문하세요...")
        if user_followup:
            # 유저 질문 기록
            st.session_state.verse_chats[v_key].append({
                "role": "user",
                "content": user_followup,
                "timestamp": datetime.datetime.now()
            })
            with st.spinner("답변을 생성하고 있습니다..."):
                reply = query_gemini(user_followup, history=st.session_state.verse_chats[v_key][:-1])
                st.session_state.verse_chats[v_key].append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.datetime.now()
                })
            st.rerun()

    # 2) 기본 통독 모드
    else:
        st.markdown(f"### 🗓️ Day {selected_day} 통독 본문")
        if not today_chapters:
            st.write("해당 일차에 배정된 본문이 없습니다.")
        else:
            chap_summary = ", ".join([f"{c['book']} {c['chapter']}장" for c in today_chapters])
            st.caption(f"📖 오늘의 분량: **{chap_summary}**")

            # 선택된 일차의 본문 구절 필터링
            for c_info in today_chapters:
                b_name = c_info["book"]
                c_num = c_info["chapter"]
                
                with st.expander(f"📕 {b_name} 제 {c_num} 장", expanded=True):
                    chapter_verses = [
                        row for row in bible_data 
                        if row["book"] == b_name and row["chapter"] == c_num
                    ]
                    
                    for row in chapter_verses:
                        col_text, col_btn = st.columns([4, 1.2])
                        with col_text:
                            st.markdown(f"**{row['verse']}절.** {row['text']}")
                            if row.get("cross_refs"):
                                st.caption(f"🔗 관주: {', '.join(row['cross_refs'])}")
                        
                        with col_btn:
                            btn_key = f"btn_{row['book']}_{row['chapter']}_{row['verse']}"
                            if st.button("🤖 AI 해석 & 대화", key=btn_key):
                                st.session_state.active_verse = row
                                st.rerun()
                        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed #e0e0e0;'>", unsafe_allow_html=True)

# ------------------------------------------
# TAB 2: 자유 성경 AI Q&A 창
# ------------------------------------------
with tab_general_chat:
    st.subheader("💬 자유 성경 AI 질의응답")
    st.caption("특정 구절에 국한되지 않고 성경 전체 역사, 신학 교리, 신앙 고민 등을 자유롭게 질문하세요.")

    # 대화 히스토리 출력
    for msg in st.session_state.general_chats:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            st.caption(msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S"))

    # 질문 입력
    general_prompt = st.chat_input("성경과 신앙에 관한 질문을 입력하세요...")
    if general_prompt:
        st.session_state.general_chats.append({
            "role": "user",
            "content": general_prompt,
            "timestamp": datetime.datetime.now()
        })
        with st.spinner("AI 신학자가 답변을 작성 중입니다..."):
            sys_prompt = "너는 성경 전체와 기독교 신학에 정통한 성경 교사야. 성도들의 질문에 성경적 근거를 바탕으로 친절하고 깊이 있게 답변해 줘."
            full_context = [{"role": "user", "content": sys_prompt}, {"role": "assistant", "content": "네, 성경에 근거하여 성실히 답변드리겠습니다."}]
            full_context.extend(st.session_state.general_chats[:-1])
            
            ans = query_gemini(general_prompt, history=full_context)
            st.session_state.general_chats.append({
                "role": "assistant",
                "content": ans,
                "timestamp": datetime.datetime.now()
            })
        st.rerun()

# ------------------------------------------
# TAB 3: 질문 & 답변 기록 보관소 (구절별/전체)
# ------------------------------------------
with tab_history:
    st.subheader("📜 AI 질의응답 기록 보관소")
    
    subtab_general, subtab_verses = st.tabs(["🌐 전체 질문 기록", "📖 구절별 질문 기록"])

    # 1) 전체 자유 질문 기록
    with subtab_general:
        st.markdown("#### 💬 자유 AI Q&A 내역")
        if not st.session_state.general_chats:
            st.info("아직 자유 질문 기록이 없습니다.")
        else:
            for idx, chat in enumerate(st.session_state.general_chats):
                role_icon = "👤 질문" if chat["role"] == "user" else "🤖 AI 답변"
                with st.expander(f"{role_icon} | {chat['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {chat['content'][:40]}..."):
                    st.write(chat["content"])

    # 2) 구절별 질문 기록 (책별 그룹화 -> 구절 번호순 -> 시간순 정렬)
    with subtab_verses:
        st.markdown("#### 📖 성경 구절별 질문 & 답변 내역")
        if not st.session_state.verse_chats:
            st.info("아직 구절별 AI 질의응답 기록이 없습니다. 본문에서 [🤖 AI 해석 & 대화] 버튼을 눌러보세요.")
        else:
            # 데이터 구조 분해 및 정렬을 위한 임베딩
            # key: "창세기 1:1"
            parsed_records = []
            for v_key, msgs in st.session_state.verse_chats.items():
                if not msgs:
                    continue
                try:
                    parts = v_key.split(" ")
                    b_name = parts[0]
                    c_num, v_num = map(int, parts[1].split(":"))
                except Exception:
                    b_name, c_num, v_num = v_key, 0, 0
                
                parsed_records.append({
                    "key": v_key,
                    "book": b_name,
                    "chapter": c_num,
                    "verse": v_num,
                    "messages": msgs
                })

            # 책(권) 단위 그룹화
            books_in_records = sorted(list(set(r["book"] for r in parsed_records)))
            
            selected_book_filter = st.selectbox("조회할 성경 책(권)을 선택하세요:", books_in_records)
            
            # 선택한 책에 해당하는 구절 필터링 및 장/절 번호순 정렬
            book_records = [r for r in parsed_records if r["book"] == selected_book_filter]
            book_records.sort(key=lambda x: (x["chapter"], x["verse"]))

            st.caption(f"총 **{len(book_records)}개**의 구절에 질의응답 기록이 있습니다. (장/절 번호순 정렬됨)")

            for rec in book_records:
                chap_verse_label = f"{rec['book']} {rec['chapter']}:{rec['verse']}"
                first_q = rec['messages'][0]['content'] if rec['messages'] else "대화"
                
                with st.expander(f"📍 [{chap_verse_label}] 대화 기록 ({len(rec['messages'])}개 메시지)"):
                    # 구절 내부에서는 시간순(Timestamp)으로 정렬하여 출력
                    sorted_msgs = sorted(rec["messages"], key=lambda m: m["timestamp"])
                    for msg in sorted_msgs:
                        role_label = "👤 사용자 질문" if msg["role"] == "user" else "🤖 AI 신학 답변"
                        st.markdown(f"**{role_label}** <span style='font-size:0.8em; color:gray;'>({msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')})</span>", unsafe_allow_html=True)
                        st.write(msg["content"])
                        st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px dotted #ccc;'>", unsafe_allow_html=True)
