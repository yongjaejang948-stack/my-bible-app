import json
import google.generativeai as genai
import streamlit as st

st.set_page_config(
    page_title="AI 성경 관주 & 통독 연구소", layout="wide"
)

# Gemini API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

BOOK_NAMES = [
    "창세기",
    "출애굽기",
    "레위기",
    "민수기",
    "신명기",
    "여호수아",
    "사사기",
    "룻기",
    "사무엘상",
    "사무엘하",
    "열왕기상",
    "열왕기하",
    "역대상",
    "역대하",
    "에스라",
    "느헤미야",
    "에스더",
    "욥기",
    "시편",
    "잠언",
    "전도서",
    "아가",
    "이사야",
    "예레미야",
    "예레미야애가",
    "에스겔",
    "다니엘",
    "호세아",
    "요엘",
    "아모스",
    "오바댜",
    "요나",
    "미가",
    "나훔",
    "하박국",
    "스바냐",
    "학개",
    "스가랴",
    "말라기",
    "마태복음",
    "마가복음",
    "누가복음",
    "요한복음",
    "사도행전",
    "로마서",
    "고린도전서",
    "고린도후서",
    "갈라디아서",
    "에베소서",
    "빌립보서",
    "골로새서",
    "데살로니가전서",
    "데살로니가후서",
    "디모데전서",
    "디모데후서",
    "디도서",
    "빌레몬서",
    "히브리서",
    "야고보서",
    "베드로전서",
    "베드로후서",
    "요한1서",
    "요한2서",
    "요한3서",
    "유다서",
    "요한계시록",
]


@st.cache_data
def load_bible():
  with open("bible_data.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

  formatted_data = []
  for item in raw_data:
    book_val = item.get("book") or item.get("book_name")
    if isinstance(book_val, int) and 1 <= book_val <= 66:
      book_name = BOOK_NAMES[book_val - 1]
    else:
      book_name = str(book_val)

    formatted_data.append({
        "book": book_name,
        "chapter": item["chapter"],
        "verse": item["verse"],
        "text": item["text"].strip(),
    })
  return formatted_data


bible_data = load_bible()

# 대표적인 핵심 관주 매핑 데이터베이스 (주요 구절 하이퍼링크용)
DEFAULT_CROSS_REFS = {
    "요한복음 3:16": ["창세기 22:2", "로마서 5:8", "요한1서 4:9"],
    "창세기 1:1": ["요한복음 1:1", "히브리서 11:3", "시편 33:6"],
    "로마서 5:8": ["요한복음 3:16", "요한1서 4:10", "에베소서 2:4"],
    "마태복음 28:19": ["사도행전 1:8", "고린도후서 13:13"],
}

st.title("🌐 AI 성경 관주 & 통독 연구소")

tab1, tab2 = st.tabs(["📅 기간별 성경 통독 & 관주", "🔍 개별 구절 검색"])

# --- TAB 1: 텍스트량 기준 통독 + 하이퍼링크 관주 + AI 버튼 ---
with tab1:
  st.sidebar.header("🗓️ 통독 기간 설정")
  target_days = st.sidebar.number_input(
      "목표 통독 일수 (일)", min_value=1, max_value=1000, value=90
  )

  @st.cache_data
  def build_plan(data, days):
    total_chars = sum(len(item["text"]) for item in data)
    target_per_day = total_chars / days
    plan = {}
    day = 1
    current_chars = 0
    for item in data:
      if day not in plan:
        plan[day] = []
      plan[day].append(item)
      current_chars += len(item["text"])
      if current_chars >= target_per_day and day < days:
        day += 1
        current_chars = 0
    return plan

  plan = build_plan(bible_data, target_days)
  selected_day = st.number_input(
      "읽을 일차 (Day 선택)", min_value=1, max_value=target_days, value=1
  )

  today_verses = plan.get(selected_day, [])

  if today_verses:
    first_v = today_verses[0]
    last_v = today_verses[-1]
    st.subheader(
        f"📍 Day {selected_day}: {first_v['book']} {first_v['chapter']}:{first_v['verse']} ~"
        f" {last_v['book']} {last_v['chapter']}:{last_v['verse']}"
    )
    st.caption(
        f"오늘의 읽기 분량: 총 {len(today_verses)}개 구절 (약"
        f" {sum(len(v['text']) for v in today_verses)}자)"
    )
    st.divider()

    # 클릭된 관주 구절의 텍스트를 저장할 상태값
    if "selected_xref" not in st.session_state:
      st.session_state.selected_xref = None

    # 구절별 출력 및 관주 하이퍼링크 버튼 생성
    for v in today_verses:
      ref_key = f"{v['book']} {v['chapter']}:{v['verse']}"
      st.markdown(f"**[{ref_key}]** {v['text']}")

      # 해당 구절에 등록된 관주 버튼 또는 대표 관주 매핑 확인
      xrefs = DEFAULT_CROSS_REFS.get(ref_key, [])

      # 관주 버튼 렌더링 (스케치해주신 [관주1] [관주2] 태그 형태)
      if xrefs:
        cols = st.columns([1] * (len(xrefs) + 4))
        cols[0].caption("🔗 연결 관주:")
        for idx, xref in enumerate(xrefs):
          if cols[idx + 1].button(xref, key=f"btn_{ref_key}_{xref}"):
            st.session_state.selected_xref = xref

      st.markdown("---")

    # 하이퍼링크(관주 버튼) 클릭 시 해당 연관 구절 본문 미리보기 창
    if st.session_state.selected_xref:
      st.info(f"📌 선택한 관주 구절: **{st.session_state.selected_xref}**")
      # bible_data에서 해당 관주 찾아 표시
      xref_parts = st.session_state.selected_xref.split()
      if len(xref_parts) == 2:
        b_name = xref_parts[0]
        c_v = xref_parts[1].split(":")
        found = [
            i
            for i in bible_data
            if i["book"] == b_name
            and i["chapter"] == int(c_v[0])
            and i["verse"] == int(c_v[1])
        ]
        if found:
          st.write(f"↪ *\"{found[0]['text']}\"*")

    # 스케치 제일 우측 [AI 분석] 버튼
    st.markdown("### 🤖 오늘의 통독 & 관주 AI 종합 해석")
    if st.button("✨ 오늘 읽은 구절 + 연관 관주 AI 자동 해석하기"):
      # 오늘 읽은 본문 텍스트 정리
      today_text = " ".join([
          f"{v['book']} {v['chapter']}:{v['verse']} - {v['text']}"
          for v in today_verses[:10]
      ])

      prompt = f"""
            오늘 사용자가 읽은 성경 본문 목록입니다:
            {today_text}

            위 본문 전체와 구절들에 연결된 주요 관주들의 신학적 의미를 종합하여 다음 3가지를 한국어로 작성해줘:
            1. **오늘 본문의 핵심 주제 요약**
            2. **구절 간/관주 간 영적 연결성 분석** (예: 구약 예언과 신약 성취, 신학적 맥락)
            3. **오늘의 삶에 적용할 묵상 질문 2가지**
            """

      with st.spinner("Gemini가 오늘 본문과 관주 텍스트 전체를 종합 분석 중입니다..."):
        res = model.generate_content(prompt)
        st.success("AI 해석이 완료되었습니다!")
        st.write(res.text)

# --- TAB 2: 개별 검색 ---
with tab2:
  col1, col2, col3 = st.columns(3)
  books = list(dict.fromkeys([item["book"] for item in bible_data]))
  with col1:
    sb = st.selectbox("성경 선택", books, key="s1")
  chapters = list(
      dict.fromkeys([item["chapter"] for item in bible_data if item["book"] == sb])
  )
  with col2:
    sc = st.selectbox("장 선택", chapters, key="s2")
  verses = [item for item in bible_data if item["book"] == sb and item["chapter"] == sc]
  with col3:
    sv = st.selectbox("절 선택", [v["verse"] for v in verses], key="s3")

  selected_item = next(v for v in verses if v["verse"] == sv)
  st.markdown(
      f"### {selected_item['book']} {selected_item['chapter']}:{selected_item['verse']}"
  )
  st.info(f'"{selected_item["text"]}"')
