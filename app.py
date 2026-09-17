import datetime
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

# 세션 상태 초기화
if "view_mode" not in st.session_state:
  st.session_state.view_mode = "read"
if "ai_analysis_result" not in st.session_state:
  st.session_state.ai_analysis_result = ""
if "selected_xref" not in st.session_state:
  st.session_state.selected_xref = None

st.title("📖 AI 성경 관주 & 통독 연구소")

# --- [사이드바] 통독 목표 및 일차 설정 ---
st.sidebar.header("🗓️ 통독 목표 및 일정 설정")
target_days = st.sidebar.number_input(
    "목표 통독 일수 (일)", min_value=1, max_value=365, value=90
)
start_date = st.sidebar.date_input(
    "통독 시작일", value=datetime.date(2026, 9, 1)
)

# 오늘이 몇일차인지 자동 계산
today_date = datetime.date.today()
passed_days = (today_date - start_date).days + 1
current_day = max(1, min(passed_days, target_days))

st.sidebar.markdown(f"📌 **시작일:** {start_date}")
st.sidebar.markdown(
    f"📍 **오늘 날짜:** {today_date} (통독 **{current_day}일차** / 총"
    f" {target_days}일)"
)

# --- 전체 성경을 목표 일수(예: 90일) 분량으로 균등 배분하는 함수 ---


@st.cache_data
def build_reading_plan(data, total_days):
  total_chars = sum(len(item["text"]) for item in data)
  target_per_day = total_chars / total_days

  plan = {}
  day = 1
  current_chars = 0
  for item in data:
    if day not in plan:
      plan[day] = []
    plan[day].append(item)
    current_chars += len(item["text"])
    if current_chars >= target_per_day and day < total_days:
      day += 1
      current_chars = 0
  return plan


reading_plan = build_reading_plan(bible_data, target_days)

# 사용자가 직접 몇일차를 볼지 선택할 수도 있게 제공 (기본값은 오늘 일차)
selected_day = st.sidebar.number_input(
    "조회할 읽기 일차 선택 (Day)",
    min_value=1,
    max_value=target_days,
    value=current_day,
)

# 오늘(선택한 일차) 읽을 전체 구절 목록 가져오기 (중간에 끊기지 않고 전체 출력)
today_verses = reading_plan.get(selected_day, bible_data)

# --- 화면 1: 책 형태 성경 통독 모드 ---
if st.session_state.view_mode == "read":
  if today_verses:
    first_v = today_verses[0]
    last_v = today_verses[-1]

    st.subheader(
        f"📖 Day {selected_day} 통독 분량 ({first_v['book']}"
        f" {first_v['chapter']}:{first_v['verse']} ~ {last_v['book']}"
        f" {last_v['chapter']}:{last_v['verse']})"
    )
    st.caption(
        f"목표 통독: 총 {target_days}일 중 **{selected_day}일차** 분량입니다. (총"
        f" {len(today_verses)}개 구절)"
    )
    st.divider()

    # 종이책 질감 및 글자 디자인 커스텀 CSS
    st.markdown(
        """
        <style>
        .bible-box {
            background-color: #FAFAFA;
            padding: 12px 15px;
            border-radius: 6px;
            border-left: 4px solid #D32F2F;
            margin-bottom: 10px;
        }
        .verse-ref {
            color: #111111;
            font-weight: bold;
            font-size: 1.05em;
            margin-right: 6px;
        }
        .verse-text {
            color: #D32F2F;
            font-size: 1.1em;
            font-weight: 500;
            line-height: 1.6;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 오늘 읽을 분량 전체를 책처럼 연속 출력
    for v in today_verses:
      ref_key = f"{v['book']} {v['chapter']}:{v['verse']}"

      # 구절명(검은색) + 본문(빨간색)
      st.markdown(
          f"""
            <div class="bible-box">
                <span class="verse-ref">[{ref_key}]</span>
                <span class="verse-text">{v['text']}</span>
            </div>
            """,
          unsafe_allow_html=True,
      )

      # 관주 버튼 및 AI 버튼 레이아웃 (구절별 하단 배치)
      xrefs = DEFAULT_CROSS_REFS.get(ref_key, ["창세기 1:1", "로마서 5:8"])
      cols = st.columns([2, 2, 2, 2])

      for idx, xref in enumerate(xrefs[:3]):
        if cols[idx].button(
            f"🔗 {xref}", key=f"btn_{ref_key}_{idx}", use_container_width=True
        ):
          st.session_state.selected_xref = xref

      # 우측 [AI 해석] 버튼
      if cols[-1].button(
          "🤖 AI 해석", key=f"ai_{ref_key}", type="primary", use_container_width=True
      ):
        with st.spinner(f"{ref_key} 구절과 관주를 종합 분석 중입니다..."):
          prompt = f"""
                    성경 구절: '{ref_key}'
                    본문: "{v['text']}"
                    연관 관주: {', '.join(xrefs)}

                    이 구절과 관주들이 가지는 신학적/영적 의미 및 삶의 적용점을 자세히 해석해줘.
                    """
          res = model.generate_content(prompt)
          st.session_state.ai_analysis_result = res.text
          st.session_state.view_mode = "ai_result"
          st.rerun()

      st.write("")

    # 선택한 관주 클릭 시 미리보기
    if st.session_state.selected_xref:
      st.info(f"📌 선택한 관주: **{st.session_state.selected_xref}**")

# --- 화면 2: AI 해석 창 (새 창 전환) ---
elif st.session_state.view_mode == "ai_result":
  st.subheader("💡 AI 구절 & 관주 종합 분석 결과")
  st.markdown("---")

  st.write(st.session_state.ai_analysis_result)

  st.markdown("---")
  if st.button("⬅️ 뒤로가기 (통독 성경으로 돌아가기)", type="secondary"):
    st.session_state.view_mode = "read"
    st.rerun()
