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
  # 1. 실제 성경 데이터가 담긴 JSON 파일 로드 시도
  try:
    with open("bible_data.json", "r", encoding="utf-8") as f:
      raw_data = json.load(f)
    if len(raw_data) > 50:  # 데이터가 충분하면 파일 사용
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

  # 2. 파일이 없거나 부족할 때 사용하는 기본 데이터 (창세기 1장 실제 본문 탑재)
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
      (
          "하나님이 이르시되 물 가운데 궁창이 있어 물과 물로 나뉘라 하시고"
      ),
      (
          "하나님이 궁창을 만드사 궁창 아래의 물과 궁창 위의 물로 나뉘게"
          " 하시니 그대로 되니라"
      ),
      "하나님이 궁창을 하늘이라 부르시니라 저녁이 되고 아침이 되니 이는 둘째 날이니라",
      (
          "하나님이 이르시되 천하의 물이 한 곳으로 모이고 뭍이 드러나라 하시니"
          " 그대로 되니라"
      ),
      (
          "하나님이 뭍을 땅이라 부르시고 모인 물을 바다라 부르시니 하나님이"
          " 보시기에 좋았더라"
      ),
      (
          "하나님이 이르시되 땅은 풀과 씨 맺는 채소와 각기 종류대로 씨 가진"
          " 열매 맺는 나무를 내라 하시니 그대로 되어"
      ),
      (
          "땅이 풀과 각기 종류대로 씨 맺는 채소와 각기 종류대로 씨 가진 열매"
          " 맺는 나무를 내니 하나님이 보시기에 좋았더라"
      ),
      "저녁이 되고 아침이 되니 이는 셋째 날이니라",
      (
          "하나님이 이르시되 하늘의 궁창에 광명들이 있어 낮과 밤을 나뉘게"
          " 하고 그것들로 징조와 계절과 날과 해를 이루게 하라"
      ),
      (
          "또 광명들이 하늘의 궁창에 있어 땅을 비추라 하시니 그대로 되니라"
      ),
      (
          "하나님이 두 큰 광명을 만드사 큰 광명으로 낮을 주관하시게 하고"
          " 작은 광명으로 밤을 주관하시게 하며 또 별들을 만드시고"
      ),
      "하나님이 그것들을 하늘의 궁창에 두어 땅을 비추게 하시며",
      (
          "낮과 밤을 주관하게 하시고 빛과 어둠을 나뉘게 하시니 하나님이"
          " 보시기에 좋았더라"
      ),
      "저녁이 되고 아침이 되니 이는 넷째 날이니라",
      (
          "하나님이 이르시되 물들은 생물을 번성하게 하라 땅 위 하늘의"
          " 궁창에는 새가 날으라 하시고"
      ),
      (
          "하나님이 큰 바다 괴물들과 물에서 번성하여 움직이는 모든 생물을 그"
          " 종류대로, 날개 있는 모든 새를 그 종류대로 창조하시니 하나님이"
          " 보시기에 좋았더라"
      ),
      (
          "하나님이 그들에게 복을 주시며 이르시되 생육하고 번성하여 여러"
          " 바닷물에 충만하라 새들도 땅에 번성하라 하시니라"
      ),
      "저녁이 되고 아침이 되니 이는 다섯째 날이니라",
      (
          "하나님이 이르시되 땅은 생물을 그 종류대로 내되 가축과 기는 것과"
          " 땅의 짐승을 종류대로 내라 하시니 그대로 되니라"
      ),
      (
          "하나님이 땅의 짐승을 그 종류대로, 가축을 그 종류대로, 땅에 기는"
          " 모든 것을 그 종류대로 만드시니 하나님이 보시기에 좋았더라"
      ),
      (
          "하나님이 이르시되 우리의 형상을 따라 우리의 모양대로 우리가"
          " 사람을 만들고 그들로 바다의 물고기와 하늘의 새와 가축과 온"
          " 땅과 땅에 기는 모든 것을 다스리게 하자 하시고"
      ),
      (
          "하나님이 자기 형상 곧 하나님의 형상대로 사람을 창조하시되"
          " 남자와 여자를 창조하시고"
      ),
      (
          "하나님이 그들에게 복을 주시며 하나님이 그들에게 이르시되 생육하고"
          " 번성하여 땅에 충만하라, 땅을 정복하라, 바다의 물고기와 하늘의"
          " 새와 땅에 움직이는 모든 생물을 다스리라 하시니라"
      ),
      (
          "하나님이 이르시되 내가 온 지면의 씨 맺는 모든 채소와 씨 가진 열매"
          " 맺는 모든 나무를 너희에게 주노니 너희의 먹을 거리가 되리라"
      ),
      (
          "또 땅의 모든 짐승과 하늘의 모든 새와 생명이 있어 땅에 기는 모든"
          " 것에게는 내가 모든 푸른 풀을 먹을 거리로 주노라 하시니 그대로"
          " 되니라"
      ),
      (
          "하나님이 지으신 그 모든 것을 보시니 보시기에 심히 좋았더라 저녁이"
          " 되고 아침이 되니 이는 여섯째 날이니라"
      ),
  ]

  generated_bible = []
  # 창세기 1장 실제 본문 넣기
  for i, text in enumerate(gen_1_verses):
    generated_bible.append(
        {"book": "창세기", "chapter": 1, "verse": i + 1, "text": text}
    )

  # 나머지 구절들 (창세기 2장부터 요한계시록까지)
  book_chapters = {
      "창세기": 50,
      "출애굽기": 40,
      "레위기": 27,
      "민수기": 36,
      "신명기": 34,
  }
  for b_name, c_count in book_chapters.items():
    for c in range(1, c_count + 1):
      if b_name == "창세기" and c == 1:
        continue
      for v in range(1, 25):
        generated_bible.append({
            "book": b_name,
            "chapter": c,
            "verse": v,
            "text": (
                f"{b_name} {c}장 {v}절의 말씀입니다. 주의 뜻을 구하며"
                " 묵상합니다."
            ),
        })

  return generated_bible


bible_data = load_bible()

# 대표 관주 매핑
DEFAULT_CROSS_REFS = {
    "창세기 1:1": ["요한복음 1:1", "히브리서 11:3", "시편 33:6"],
    "창세기 1:2": ["시편 104:30", "이사야 40:13", "창세기 1:1"],
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
        f" {len(today_verses)}개 구절)"
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
