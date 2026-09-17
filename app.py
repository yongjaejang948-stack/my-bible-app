import json
import google.generativeai as genai
import streamlit as st

st.set_page_config(page_title="AI 성경 관주 & 통독 연구소", layout="wide")

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

# 대표 관주 매핑
DEFAULT_CROSS_REFS = {
    "요한복음 3:16": ["창세기 22:2", "로마서 5:8", "요한1서 4:9"],
    "창세기 1:1": ["요한복음 1:1", "히브리서 11:3", "시편 33:6"],
    "로마서 5:8": ["요한복음 3:16", "요한1서 4:10", "에베소서 2:4"],
}

# 세션 상태 초기화 (화면 전환 제어용)
if "view_mode" not in st.session_state:
  st.session_state.view_mode = "read"  # 'read' 또는 'ai_result'
if "ai_analysis_result" not in st.session_state:
  st.session_state.ai_analysis_result = ""
if "selected_xref" not in st.session_state:
  st.session_state.selected_xref = None

st.title("📖 AI 성경 관주 & 통독 연구소")

# --- 화면 1: 성경 읽기 & 관주 모드 ---
if st.session_state.view_mode == "read":
  st.sidebar.header("🗓️ 통독 설정")
  target_days = st.sidebar.number_input(
      "목표 통독 일수", min_value=1, max_value=1000, value=90
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
      "읽을 일차 (Day)", min_value=1, max_value=target_days, value=1
  )
  today_verses = plan.get(selected_day, [])

  if today_verses:
    first_v = today_verses[0]
    last_v = today_verses[-1]
    st.subheader(
        f"📍 Day {selected_day}: {first_v['book']} {first_v['chapter']}:{first_v['verse']} ~"
        f" {last_v['book']} {last_v['chapter']}:{last_v['verse']}"
    )
    st.divider()

    # 스케치하신 상단 구절 + 관주 + AI 버튼 레이아웃
    for v in today_verses:
      ref_key = f"{v['book']} {v['chapter']}:{v['verse']}"

      # 책처럼 읽는 본문: 구절(검은색) + 본문 텍스트(빨간색)
      st.markdown(
          f"**<span style='color:black; font-size:1.1em;'>[{ref_key}]</span>**"
          f" <span style='color:#D32F2F; font-size:1.15em;"
          f" font-weight:500;'>{v['text']}</span>",
          unsafe_allow_html=True,
      )

      # 관주 버튼 및 AI 버튼 한 줄 배치
      xrefs = DEFAULT_CROSS_REFS.get(ref_key, ["관주1", "관주2"])

      # 버튼들을 한 라인에 가로 배열
      btn_cols = st.columns(len(xrefs) + 2)

      # 관주 버튼 렌더링
      for idx, xref in enumerate(xrefs):
        if btn_cols[idx].button(
            f"🔗 {xref}", key=f"btn_{ref_key}_{xref}", use_container_width=True
        ):
          st.session_state.selected_xref = xref

      # 스케치 제일 우측 [AI 버튼]
      if btn_cols[-1].button(
          "🤖 AI 해석", key=f"ai_{ref_key}", type="primary", use_container_width=True
      ):
        with st.spinner("Gemini가 구절과 연관 관주의 영적 의미를 분석 중입니다..."):
          prompt = f"""
                    성경 구절: '{ref_key}'
                    본문: "{v['text']}"
                    연관 관주: {', '.join(xrefs)}

                    이 구절과 관주들이 가지는 신학적/영적 의미를 상세히 해석해줘.
                    """
          res = model.generate_content(prompt)
          st.session_state.ai_analysis_result = res.text
          st.session_state.view_mode = "ai_result"
          st.rerun()

      st.markdown("---")

    # 선택한 관주 클릭 시 바로 밑에 본문 표시
    if st.session_state.selected_xref:
      st.info(f"📌 선택한 관주: **{st.session_state.selected_xref}**")

# --- 화면 2: AI 해석 상세 창 (새로운 창으로 전환) ---
elif st.session_state.view_mode == "ai_result":
  st.subheader("💡 AI 구절 & 관주 종합 해석 결과")
  st.markdown("---")

  # AI 분석 결과 출력
  st.write(st.session_state.ai_analysis_result)

  st.markdown("---")
  # 스케치대로 뒤로가기 누르면 다시 성경 읽기 화면으로 복귀
  if st.button("⬅️ 뒤로가기 (성경 목록으로 돌아가기)", type="secondary"):
    st.session_state.view_mode = "read"
    st.rerun()
