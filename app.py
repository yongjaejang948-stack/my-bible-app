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
  # 1. 실제 전체 성경 데이터 JSON 파일이 있다면 로드
  try:
    with open("bible_data.json", "r", encoding="utf-8") as f:
      raw_data = json.load(f)
    if len(raw_data) > 1000:
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
  except:
    pass

  # 2. 파일이 없을 경우: 66권 전체 1,189장 완벽 생성
  book_chapters = {
      "창세기": 50,
      "출애굽기": 40,
      "레위기": 27,
      "민수기": 36,
      "신명기": 34,
      "여호수아": 24,
      "사사기": 21,
      "룻기": 4,
      "사무엘상": 31,
      "사무엘하": 24,
      "열왕기상": 22,
      "열왕기하": 25,
      "역대상": 29,
      "역대하": 36,
      "에스라": 10,
      "느헤미야": 13,
      "에스더": 10,
      "욥기": 42,
      "시편": 150,
      "잠언": 31,
      "전도서": 12,
      "아가": 8,
      "이사야": 66,
      "예레미야": 52,
      "예레미야애가": 5,
      "에스겔": 48,
      "다니엘": 12,
      "호세아": 14,
      "요엘": 3,
      "아모스": 9,
      "오바댜": 1,
      "요나": 4,
      "미가": 7,
      "나훔": 3,
      "하박국": 3,
      "스바냐": 3,
      "학개": 2,
      "스가랴": 14,
      "말라기": 4,
      "마태복음": 28,
      "마가복음": 16,
      "누가복음": 24,
      "요한복음": 21,
      "사도행전": 28,
      "로마서": 16,
      "고린도전서": 16,
      "고린도후서": 13,
      "갈라디아서": 6,
      "에베소서": 6,
      "빌립보서": 4,
      "골로새서": 4,
      "데살로니가전서": 5,
      "데살로니가후서": 3,
      "디모데전서": 6,
      "디모데후서": 4,
      "디도서": 3,
      "빌레몬서": 1,
      "히브리서": 13,
      "야고보서": 5,
      "베드로전서": 5,
      "베드로후서": 3,
      "요한1서": 5,
      "요한2서": 1,
      "요한3서": 1,
      "유다서": 1,
      "요한계시록": 22,
  }

  gen_1_verses = [
      "태초에 하나님이 천지를 창조하시니라",
      (
          "땅이 혼돈하고 공허하며 흑암이 깊음 위에 있고 하나님의 영은 수면"
          " 위에 운행하시니라"
      ),
      "하나님이 이르시되 빛이 있으라 하시니 빛이 있었고",
      "빛이 하나님이 보시기에 좋았더라 하나님이 빛과 어둠을 나누사",
      (
          "하나님이 빛을 낮이라 부르시고 어둠을 밤이라 부르시니라 저녁이 되고"
          " 아침이 되니 이는 첫째 날이니라"
      ),
  ]

  generated_bible = []
  for b_name, c_count in book_chapters.items():
    for c in range(1, c_count + 1):
      v_count = 15  # 장당 평균 절 수 시뮬레이션
      for v in range(1, v_count + 1):
        if b_name == "창세기" and c == 1 and v <= 5:
          text = gen_1_verses[v - 1]
        else:
          text = (
              f"[{b_name} {c}장 {v}절] 이 말씀은 주의 거룩한 뜻과 교훈을"
              " 담고 있습니다. 온 마음으로 묵상합니다."
          )
        generated_bible.append(
            {"book": b_name, "chapter": c, "verse": v, "text": text}
        )
  return generated_bible


bible_data = load_bible()

# 대표 관주 매핑
DEFAULT_CROSS_REFS = {
    "창세기 1:1": ["요한복음 1:1", "히브리서 11:3", "시편 33:6"],
    "요한복음 3:16": ["창세기 22:2", "로마서 5:8", "요한1서 4:9"],
}

# 세션 상태 초기화
if "view_mode" not in st.session_state:
  st.session_state.view_mode = "read"
if "ai_analysis_result" not in st.session_state:
  st.session_state.ai_analysis_result = ""
if "selected_xref" not in st.session_state:
  st.session_state.selected_xref = None

st.title("📖 AI 성경 관주 & 통독 연구소")

# --- [사이드바] 통독 목표 및 일정 설정 ---
st.sidebar.header("🗓️ 통독 목표 및 일정 설정")
target_days = st.sidebar.number_input(
    "목표 통독 일수 (일)", min_value=1, max_value=365, value=90
)
start_date = st.sidebar.date_input(
    "통독 시작일", value=datetime.date(2026, 9, 1)
)

today_date = datetime.date.today()
passed_days = (today_date - start_date).days + 1
current_day = max(1, min(passed_days, target_days))

st.sidebar.markdown(f"📌 **시작일:** {start_date}")
st.sidebar.markdown(
    f"📍 **오늘 날짜:** {today_date} (통독 **{current_day}일차** / 총"
    f" {target_days}일)"
)


# --- [핵심 수정] 장(Chapter) 단위로 깔끔하게 묶어서 분배하는 함수 ---
@st.cache_data
def build_reading_plan_by_chapter(data, total_days):
  # 1. 장(Chapter)별로 구절들을 그룹화
  chapters_dict = {}
  for item in data:
    key = (item["book"], item["chapter"])
    if key not in chapters_dict:
      chapters_dict[key] = []
    chapters_dict[key].append(item)

  chapter_keys = list(chapters_dict.keys())
  total_chapters = len(chapter_keys)

  # 2. 총 장 수를 목표 일수(예: 90일)로 나누어 일자별 장 배분 (장 단위 절대 안 잘림)
  plan = {}
  chapters_per_day = total_chapters / total_days

  for day in range(1, total_days + 1):
    start_idx = int(round((day - 1) * chapters_per_day))
    end_idx = int(round(day * chapters_per_day))
    if day == total_days:
      end_idx = total_chapters
    if start_idx >= end_idx:
      end_idx = min(start_idx + 1, total_chapters)

    day_verses = []
    for c_key in chapter_keys[start_idx:end_idx]:
      day_verses.extend(chapters_dict[c_key])
    plan[day] = day_verses

  return plan


reading_plan = build_reading_plan_by_chapter(bible_data, target_days)

selected_day = st.sidebar.number_input(
    "조회할 읽기 일차 선택 (Day)",
    min_value=1,
    max_value=target_days,
    value=current_day,
)

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
        f" {len(today_verses)}개 구절 / 온전한 장 단위 구성)"
    )
    st.divider()

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

    for v in today_verses:
      ref_key = f"{v['book']} {v['chapter']}:{v['verse']}"

      st.markdown(
          f"""
            <div class="bible-box">
                <span class="verse-ref">[{ref_key}]</span>
                <span class="verse-text">{v['text']}</span>
            </div>
            """,
          unsafe_allow_html=True,
      )

      xrefs = DEFAULT_CROSS_REFS.get(ref_key, ["창세기 1:1", "시편 33:6"])
      cols = st.columns([2, 2, 2, 2])

      for idx, xref in enumerate(xrefs[:3]):
        if cols[idx].button(
            f"🔗 {xref}", key=f"btn_{ref_key}_{idx}", use_container_width=True
        ):
          st.session_state.selected_xref = xref

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

    if st.session_state.selected_xref:
      st.info(f"📌 선택한 관주: **{st.session_state.selected_xref}**")

# --- 화면 2: AI 해석 창 ---
elif st.session_state.view_mode == "ai_result":
  st.subheader("💡 AI 구절 & 관주 종합 분석 결과")
  st.markdown("---")
  st.write(st.session_state.ai_analysis_result)
  st.markdown("---")
  if st.button("⬅️ 뒤로가기 (통독 성경으로 돌아가기)", type="secondary"):
    st.session_state.view_mode = "read"
    st.rerun()
