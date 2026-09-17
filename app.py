import streamlit as st
import json
import datetime
import re
import os
import google.generativeai as genai

st.set_page_config(page_title="AI 성경 관주 & 통독 연구소", page_icon="🕊️", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Gemini API 키가 설정되지 않았습니다.")

# 세션 상태 초기화 (생략 - 이전 코드와 동일하게 유지)

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
    st.session_state.ai_chat_history = []
if "global_chat_history" not in st.session_state:
    st.session_state.global_chat_history = []
if "verse_chat_history" not in st.session_state:
    st.session_state.verse_chat_history = {}
if "current_verse_key" not in st.session_state:
    st.session_state.current_verse_key = None

# ====================== GitHub bible.json 자동 로드 (수정된 버전) ======================
@st.cache_data
def load_bible_from_github():
    """GitHub 저장소에 있는 bible.json을 자동으로 로드"""
    
    # 실제 GitHub 구조에 맞춘 정확한 경로들
    possible_paths = [
        "bible.json",                           # 루트
        "my-bible-app/bible.json",              # ← 이 경로가 핵심!
        "data/bible.json",
        "assets/bible.json",
        "static/bible.json",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                formatted = parse_bible_data(data)
                if formatted:
                    st.success(f"✅ GitHub에서 {len(formatted)}구절 로드 완료 (경로: {path})")
                    return formatted
            except Exception as e:
                continue
    
    st.error("❌ GitHub 저장소에서 bible.json을 찾을 수 없습니다.")
    st.info("해결 방법: GitHub 저장소 루트 또는 my-bible-app/ 폴더에 bible.json을 두세요.")
    return []

def parse_bible_data(data):
    formatted = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict): continue
            book = item.get('book') or item.get('book_name') or item.get('name') or ''
            chapter = item.get('chapter') or item.get('chap') or item.get('c') or 0
            verse = item.get('verse') or item.get('ver') or item.get('v') or 0
            text_val = item.get('text') or item.get('content') or item.get('verse_text') or ''
            if book and chapter and verse:
                formatted.append({"book": str(book).strip(), "chapter": int(chapter), "verse": int(verse), "text": str(text_val).strip()})
    elif isinstance(data, dict):
        for book, chapters in data.items():
            if not isinstance(chapters, dict): continue
            for ch_str, verses in chapters.items():
                try: ch = int(ch_str)
                except: continue
                if isinstance(verses, dict):
                    for v_str, txt in verses.items():
                        try: v = int(v_str)
                        except: continue
                        formatted.append({"book": str(book).strip(), "chapter": ch, "verse": v, "text": str(txt).strip()})
    return formatted

# 자동 로드 실행
if not st.session_state.bible_data:
    st.session_state.bible_data = load_bible_from_github()

# (나머지 코드는 이전에 제공한 전체 코드와 동일하게 유지)
# build_reading_plan_by_chapter, call_gemini, 사이드바, 메인 화면 등

def build_reading_plan_by_chapter(bible_data, target_days=90, start_date=None):
    if not bible_data: return []
    chapters = {}
    for item in bible_data:
        key = (item["book"], item["chapter"])
        if key not in chapters: chapters[key] = []
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
            "verses": verses,
            "date": (start_date or datetime.date.today()) + datetime.timedelta(days=day-1)
        })
        idx += chapters_per_day
        day += 1
    return plan

def call_gemini(prompt):
    if "GEMINI_API_KEY" not in st.secrets:
        return "API 키가 설정되지 않았습니다."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 오류: {str(e)}"

# ====================== 사이드바 ======================
with st.sidebar:
    st.title("⚙️ 환경 설정")
    if st.session_state.bible_data:
        st.success(f"✅ {len(st.session_state.bible_data)}구절 자동 로드 완료")
    else:
        st.error("❌ bible.json을 찾을 수 없습니다")
    
    target_days = st.number_input("목표 통독 일수", min_value=30, max_value=365, value=90)
    start_date = st.date_input("통독 시작일", value=datetime.date(2026, 9, 17))
    
    if st.button("통독 계획 생성", type="primary"):
        if st.session_state.bible_data:
            st.session_state.reading_plan = build_reading_plan_by_chapter(st.session_state.bible_data, target_days, start_date)
            st.session_state.current_day = 1
            st.success("통독 계획 생성 완료!")
    
    if st.session_state.reading_plan:
        today = datetime.date.today()
        for p in st.session_state.reading_plan:
            if p["date"] <= today:
                st.session_state.current_day = p["day"]
        st.info(f"오늘은 **{st.session_state.current_day}일차**입니다.")
    
    st.divider()
    
    st.subheader("💬 전체 AI 질문")
    global_q = st.text_area("성경 전체에 대해 질문하세요", key="global_q")
    if st.button("전체 질문하기"):
        if global_q.strip():
            with st.spinner("AI 답변 생성 중..."):
                prompt = f"당신은 성경 전문가입니다. 다음 질문에 대해 성경적으로 깊이 있게 답변해 주세요.\n\n질문: {global_q}\n\n답변:"
                answer = call_gemini(prompt)
                st.session_state.global_chat_history.append({"question": global_q, "answer": answer, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                st.rerun()
    
    if st.session_state.global_chat_history:
        with st.expander("📜 전체 질문 기록"):
            for i, chat in enumerate(st.session_state.global_chat_history):
                st.markdown(f"**Q{i+1}.** {chat['question']}")
                st.markdown(chat['answer'])
                st.caption(chat['timestamp'])
                st.divider()

# ====================== 메인 화면 ======================
st.title("🕊️ AI 성경 관주 & 통독 연구소")

if not st.session_state.reading_plan:
    st.info("사이드바에서 통독 계획을 생성하세요.")
    st.stop()

plan = st.session_state.reading_plan
current_day = st.session_state.current_day
if current_day > len(plan): current_day = len(plan)
today_plan = plan[current_day - 1]

st.subheader(f"📖 {current_day}일차 ({today_plan['date'].strftime('%Y-%m-%d')})")
st.caption(f"읽을 장: {', '.join(today_plan['chapters'])}")

for verse in today_plan["verses"]:
    verse_key = f"{verse['book']}{verse['chapter']}:{verse['verse']}"
    st.markdown(f"**{verse_key}**  {verse['text']}")
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🤖 AI 해석", key=f"ai_btn_{verse_key}"):
            st.session_state.selected_verse = verse
            st.session_state.current_verse_key = verse_key
            st.session_state.view_mode = "ai_result"
            st.rerun()
    with col2:
        if verse_key in st.session_state.verse_chat_history:
            with st.expander(f"💬 대화 ({len(st.session_state.verse_chat_history[verse_key])})", expanded=False):
                for msg in st.session_state.verse_chat_history[verse_key]:
                    role = "🙋‍♂️" if msg["role"] == "user" else "🤖"
                    st.markdown(f"{role} {msg['content']}")

st.divider()

st.subheader("💬 구절 질문 (현재 구절)")
verse_q = st.text_area("현재 구절에 대해 질문하세요", key="verse_q_input")
if st.button("구절 질문하기", type="primary"):
    if verse_q.strip() and st.session_state.current_verse_key:
        verse = st.session_state.selected_verse or {}
        prompt = f"현재 구절: {st.session_state.current_verse_key} - {verse.get('text', '')}\n\n질문: {verse_q}\n\n성경적으로 깊이 있게 답변해 주세요."
        answer = call_gemini(prompt)
        key = st.session_state.current_verse_key
        if key not in st.session_state.verse_chat_history:
            st.session_state.verse_chat_history[key] = []
        st.session_state.verse_chat_history[key].append({"role": "user", "content": verse_q, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        st.session_state.verse_chat_history[key].append({"role": "assistant", "content": answer, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        st.rerun()

if st.session_state.verse_chat_history:
    st.subheader("📜 구절 질문 기록")
    book_groups = {}
    for vkey, chats in st.session_state.verse_chat_history.items():
        match = re.match(r"([가-힣]+)", vkey)
        book = match.group(1) if match else "기타"
        if book not in book_groups: book_groups[book] = []
        book_groups[book].append((vkey, chats))
    for book in sorted(book_groups.keys()):
        with st.expander(f"📖 {book}", expanded=True):
            sorted_list = sorted(book_groups[book], key=lambda x: int(re.search(r":(\d+)", x[0]).group(1)) if re.search(r":(\d+)", x[0]) else 0)
            for vkey, chats in sorted_list:
                st.markdown(f"**{vkey}**")
                for msg in chats:
                    role = "🙋‍♂️" if msg["role"] == "user" else "🤖"
                    st.markdown(f"{role} {msg['content']}")
                st.divider()

if st.session_state.view_mode == "ai_result" and st.session_state.selected_verse:
    verse = st.session_state.selected_verse
    verse_key = st.session_state.current_verse_key
    st.header(f"🤖 AI 해석 - {verse_key}")
    st.markdown(f"**본문:** {verse['text']}")
    if st.button("← 읽기 화면으로"):
        st.session_state.view_mode = "read"
        st.rerun()
    if not any(m.get("verse_key") == verse_key for m in st.session_state.ai_chat_history):
        prompt = f"성경 구절: {verse_key} - {verse['text']}\n\n이 구절의 의미, 신학적 중요성, 연관 구절을 종합하여 깊이 있게 설명해 주세요."
        ans = call_gemini(prompt)
        st.session_state.ai_chat_history.append({"verse_key": verse_key, "role": "assistant", "content": ans, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    for msg in st.session_state.ai_chat_history:
        if msg.get("verse_key") == verse_key:
            role = "🙋‍♂️" if msg["role"] == "user" else "🤖"
            st.markdown(f"**{role}** {msg['content']}")
    follow = st.text_input("추가 질문", key="follow_input")
    if st.button("계속 질문하기"):
        if follow.strip():
            history = "\n".join([f"{'사용자' if m['role']=='user' else 'AI'}: {m['content']}" for m in st.session_state.ai_chat_history if m.get("verse_key") == verse_key])
            prompt = f"현재 구절: {verse_key} - {verse['text']}\n\n이전 대화:\n{history}\n\n새 질문: {follow}\n\n자연스럽게 이어지는 답변:"
            ans = call_gemini(prompt)
            st.session_state.ai_chat_history.append({"verse_key": verse_key, "role": "user", "content": follow, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            st.session_state.ai_chat_history.append({"verse_key": verse_key, "role": "assistant", "content": ans, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            st.rerun()

st.caption("© 2026 AI 성경 관주 & 통독 연구소")
