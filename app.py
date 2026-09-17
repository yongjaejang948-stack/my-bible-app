import streamlit as st
import json
import datetime
import re
from typing import List, Dict, Any, Optional
import google.generativeai as genai

# ====================== 페이지 설정 ======================
st.set_page_config(
    page_title="AI 성경 관주 & 통독 연구소",
    page_icon="🕊️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== Gemini API 설정 ======================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Gemini API 키가 설정되지 않았습니다. .streamlit/secrets.toml에 GEMINI_API_KEY를 추가하세요.")

# ====================== 세션 상태 초기화 ======================
if "bible_data" not in st.session_state:
    st.session_state.bible_data = []
if "reading_plan" not in st.session_state:
    st.session_state.reading_plan = []
if "current_day" not in st.session_state:
    st.session_state.current_day = 1
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "read"
if "selected_verse" not in st.session_state:
    st.session_state.selected_verse = None
if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = []          # 구절별 대화
if "global_chat_history" not in st.session_state:
    st.session_state.global_chat_history = []      # 전체 질문 기록
if "verse_chat_history" not in st.session_state:
    st.session_state.verse_chat_history = {}       # { "창1:1": [{"role":.., "content":..}, ...] }
if "current_verse_key" not in st.session_state:
    st.session_state.current_verse_key = None

# ====================== JSON 파서 (강화판) ======================
def load_bible(file) -> List[Dict]:
    """bible.json을 다양한 형태로 파싱하여 표준 리스트로 반환"""
    try:
        content = file.read()
        if isinstance(content, bytes):
            for encoding in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
                try:
                    text = content.decode(encoding)
                    break
                except:
                    continue
            else:
                text = content.decode('utf-8', errors='ignore')
        else:
            text = content

        data = json.loads(text)

        # 1. 리스트 형태
        if isinstance(data, list):
            formatted = []
            for item in data:
                if isinstance(item, dict):
                    book = item.get('book') or item.get('book_name') or item.get('name') or ''
                    chapter = item.get('chapter') or item.get('chap') or item.get('c') or 0
                    verse = item.get('verse') or item.get('ver') or item.get('v') or 0
                    text_val = item.get('text') or item.get('content') or item.get('verse_text') or ''
                    if book and chapter and verse:
                        formatted.append({
                            "book": str(book).strip(),
                            "chapter": int(chapter),
                            "verse": int(verse),
                            "text": str(text_val).strip()
                        })
            return formatted

        # 2. 딕셔너리 형태 (책 → 장 → 절)
        elif isinstance(data, dict):
            formatted = []
            for book, chapters in data.items():
                if isinstance(chapters, dict):
                    for ch_str, verses in chapters.items():
                        try:
                            ch = int(ch_str)
                        except:
                            continue
                        if isinstance(verses, dict):
                            for v_str, txt in verses.items():
                                try:
                                    v = int(v_str)
                                except:
                                    continue
                                formatted.append({
                                    "book": str(book).strip(),
                                    "chapter": ch,
                                    "verse": v,
                                    "text": str(txt).strip()
                                })
            return formatted

        return []
    except Exception as e:
        st.error(f"파일 파싱 오류: {str(e)}")
        return []

# ====================== 통독 계획 생성 (장 단위) ======================
def build_reading_plan_by_chapter(bible_data: List[Dict], target_days: int = 90, start_date=None) -> List[Dict]:
    if not bible_data:
        return []

    # 장별로 그룹핑
    chapters = {}
    for item in bible_data:
        key = (item["book"], item["chapter"])
        if key not in chapters:
            chapters[key] = []
        chapters[key].append(item)

    sorted_chapters = sorted(chapters.items(), key=lambda x: (x[0][0], x[0][1]))
    total_chapters = len(sorted_chapters)
    chapters_per_day = max(1, total_chapters // target_days)

    plan = []
    day = 1
    idx = 0
    while idx < total_chapters:
        day_chapters = sorted_chapters[idx:idx + chapters_per_day]
        verses = []
        for (book, ch), ch_verses in day_chapters:
            verses.extend(ch_verses)
        plan.append({
            "day": day,
            "chapters": [f"{book} {ch}" for (book, ch), _ in day_chapters],
            "verses": verses
        })
        idx += chapters_per_day
        day += 1

    # 날짜 계산
    if start_date is None:
        start_date = datetime.date.today()
    for i, p in enumerate(plan):
        p["date"] = start_date + datetime.timedelta(days=i)

    return plan

# ====================== Gemini 호출 함수 ======================
def call_gemini(prompt: str, max_tokens: int = 2048) -> str:
    if "GEMINI_API_KEY" not in st.secrets:
        return "API 키가 설정되지 않았습니다."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 호출 오류: {str(e)}"

# ====================== 사이드바 ======================
with st.sidebar:
    st.title("⚙️ 환경 설정")
    
    uploaded_file = st.file_uploader("bible.json 업로드", type=["json"])
    if uploaded_file is not None:
        st.session_state.bible_data = load_bible(uploaded_file)
        if st.session_state.bible_data:
            st.success(f"✅ {len(st.session_state.bible_data)}구절 로드 완료")
        else:
            st.error("파일을 읽을 수 없습니다.")

    target_days = st.number_input("목표 통독 일수", min_value=30, max_value=365, value=90, step=1)
    start_date = st.date_input("통독 시작일", value=datetime.date.today())

    if st.button("통독 계획 생성"):
        if st.session_state.bible_data:
            st.session_state.reading_plan = build_reading_plan_by_chapter(
                st.session_state.bible_data, target_days, start_date
            )
            st.session_state.current_day = 1
            st.success("통독 계획 생성 완료!")
        else:
            st.warning("bible.json을 먼저 업로드하세요.")

    if st.session_state.reading_plan:
        today = datetime.date.today()
        current_day = 1
        for p in st.session_state.reading_plan:
            if p["date"] <= today:
                current_day = p["day"]
        st.session_state.current_day = current_day

        st.info(f"오늘은 **{current_day}일차** 입니다.")

    st.divider()

    # ==================== 전체 질문창 ====================
    st.subheader("💬 전체 AI 질문")
    global_question = st.text_area("성경 전체에 대해 질문하세요", key="global_q")
    if st.button("전체 질문하기", key="global_btn"):
        if global_question.strip():
            with st.spinner("AI가 답변 중..."):
                prompt = f"""당신은 성경 전문가입니다. 다음 질문에 대해 성경적으로 깊이 있게 답변해 주세요.

질문: {global_question}

답변:"""
                answer = call_gemini(prompt)
                st.session_state.global_chat_history.append({
                    "question": global_question,
                    "answer": answer,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("답변 저장 완료!")

    # 전체 질문 기록 표시
    if st.session_state.global_chat_history:
        with st.expander("📜 전체 질문 기록", expanded=False):
            for i, chat in enumerate(st.session_state.global_chat_history):
                st.markdown(f"**Q{i+1}.** {chat['question']}")
                st.markdown(f"**A:** {chat['answer']}")
                st.caption(chat['timestamp'])
                st.divider()

# ====================== 메인 화면 ======================
st.title("🕊️ AI 성경 관주 & 통독 연구소")

if not st.session_state.reading_plan:
    st.info("사이드바에서 bible.json을 업로드하고 통독 계획을 생성하세요.")
    st.stop()

plan = st.session_state.reading_plan
current_day = st.session_state.current_day

if current_day > len(plan):
    current_day = len(plan)
    st.session_state.current_day = current_day

today_plan = plan[current_day - 1]

st.subheader(f"📖 {current_day}일차 ({today_plan['date'].strftime('%Y-%m-%d')})")
st.caption(f"읽을 장: {', '.join(today_plan['chapters'])}")

# 구절 렌더링
for verse in today_plan["verses"]:
    verse_key = f"{verse['book']}{verse['chapter']}:{verse['verse']}"
    
    with st.container():
        st.markdown(f"**{verse_key}**  {verse['text']}")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("🤖 AI 해석", key=f"ai_{verse_key}"):
                st.session_state.selected_verse = verse
                st.session_state.current_verse_key = verse_key
                st.session_state.view_mode = "ai_result"
        
        with col2:
            # 구절별 채팅 기록 표시
            if verse_key in st.session_state.verse_chat_history:
                with st.expander(f"💬 이 구절에 대한 AI 대화 ({len(st.session_state.verse_chat_history[verse_key])})", expanded=False):
                    for msg in st.session_state.verse_chat_history[verse_key]:
                        if msg["role"] == "user":
                            st.markdown(f"**🙋‍♂️ 질문:** {msg['content']}")
                        else:
                            st.markdown(f"**🤖 답변:** {msg['content']}")
                    st.divider()

st.divider()

# ==================== 구절 질문창 (현재 구절에 특화) ====================
if st.session_state.current_verse_key:
    st.subheader(f"💬 현재 구절({st.session_state.current_verse_key})에 대한 질문")
    
    verse_q = st.text_area("이 구절에 대해 질문하세요", key="verse_q")
    
    if st.button("구절 질문하기", key="verse_btn"):
        if verse_q.strip() and st.session_state.current_verse_key:
            with st.spinner("AI가 답변 중..."):
                verse = st.session_state.selected_verse or {}
                prompt = f"""현재 읽고 있는 구절: {st.session_state.current_verse_key} - {verse.get('text', '')}

사용자 질문: {verse_q}

이 구절과 관련하여 성경적으로 깊이 있게 답변해 주세요. 이전 대화도 고려해서 자연스럽게 이어지게 해주세요."""
                
                answer = call_gemini(prompt)
                
                if st.session_state.current_verse_key not in st.session_state.verse_chat_history:
                    st.session_state.verse_chat_history[st.session_state.current_verse_key] = []
                
                st.session_state.verse_chat_history[st.session_state.current_verse_key].append({
                    "role": "user",
                    "content": verse_q,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.session_state.verse_chat_history[st.session_state.current_verse_key].append({
                    "role": "assistant",
                    "content": answer,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("답변 저장 완료!")
                st.rerun()

# 구절 질문 기록 (책별 → 구절번호순 → 시간순)
if st.session_state.verse_chat_history:
    st.subheader("📜 구절 질문 기록")
    
    # 책별로 그룹핑
    book_groups = {}
    for vkey, chats in st.session_state.verse_chat_history.items():
        book = re.match(r"([가-힣]+)", vkey)
        if book:
            book_name = book.group(1)
            if book_name not in book_groups:
                book_groups[book_name] = []
            book_groups[book_name].append((vkey, chats))
    
    for book_name in sorted(book_groups.keys()):
        with st.expander(f"📖 {book_name}", expanded=True):
            # 구절번호 순으로 정렬
            sorted_verses = sorted(book_groups[book_name], key=lambda x: (
                int(re.search(r":(\d+)", x[0]).group(1)) if re.search(r":(\d+)", x[0]) else 0
            ))
            
            for vkey, chats in sorted_verses:
                st.markdown(f"**{vkey}**")
                # 시간순 정렬 (이미 append 순서가 시간순)
                for msg in chats:
                    if msg["role"] == "user":
                        st.markdown(f"🙋‍♂️ {msg['content']}")
                    else:
                        st.markdown(f"🤖 {msg['content']}")
                st.divider()

# ==================== AI 결과 모드 ====================
if st.session_state.view_mode == "ai_result" and st.session_state.selected_verse:
    verse = st.session_state.selected_verse
    verse_key = st.session_state.current_verse_key
    
    st.header(f"🤖 AI 해석 - {verse_key}")
    st.markdown(f"**본문:** {verse['text']}")
    
    if st.button("← 읽기 화면으로 돌아가기"):
        st.session_state.view_mode = "read"
        st.rerun()
    
    # 초기 AI 해석
    if not st.session_state.ai_chat_history or st.session_state.ai_chat_history[0].get("verse_key") != verse_key:
        prompt = f"""성경 구절: {verse_key} - {verse['text']}

이 구절의 의미와 신학적 중요성, 연관된 다른 구절들을 종합하여 깊이 있게 설명해 주세요."""
        initial_answer = call_gemini(prompt)
        st.session_state.ai_chat_history = [{
            "verse_key": verse_key,
            "role": "assistant",
            "content": initial_answer,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]
    
    # AI 대화 표시
    for msg in st.session_state.ai_chat_history:
        if msg.get("verse_key") == verse_key:
            if msg["role"] == "user":
                st.markdown(f"**🙋‍♂️ 질문:** {msg['content']}")
            else:
                st.markdown(f"**🤖 답변:** {msg['content']}")
    
    # 추가 질문
    follow_up = st.text_input("추가로 질문할 내용이 있나요?", key="follow_up")
    if st.button("계속 질문하기"):
        if follow_up.strip():
            with st.spinner("AI가 답변 중..."):
                history_text = "\n".join([
                    f"{'사용자' if m['role']=='user' else 'AI'}: {m['content']}" 
                    for m in st.session_state.ai_chat_history 
                    if m.get("verse_key") == verse_key
                ])
                
                prompt = f"""현재 구절: {verse_key} - {verse['text']}

이전 대화:
{history_text}

새로운 질문: {follow_up}

자연스럽게 이어지는 답변을 해주세요."""
                
                answer = call_gemini(prompt)
                st.session_state.ai_chat_history.append({
                    "verse_key": verse_key,
                    "role": "user",
                    "content": follow_up,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.session_state.ai_chat_history.append({
                    "verse_key": verse_key,
                    "role": "assistant",
                    "content": answer,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.rerun()

st.caption("© 2026 AI 성경 관주 & 통독 연구소 | Streamlit Community Cloud")
