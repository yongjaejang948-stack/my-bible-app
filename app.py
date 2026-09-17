import json
import google.generativeai as genai
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="AI 성경 관주 & 통독 연구소", layout="wide")

# Gemini API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# 성경 66권 한글 이름 매핑
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
        "cross_references": item.get("cross_references", []),
    })
  return formatted_data


bible_data = load_bible()

st.title("📖 AI 성경 관주 & 통독 연구소")

tab1, tab2 = st.tabs(["🔍 성경 구절 검색", "📅 기간별 성경 통독"])

# --- TAB 1: 성경 구절 3단계 검색 및 AI 해설 ---
with tab1:
  col1, col2, col3 = st.columns(3)
  books = list(dict.fromkeys([item["book"] for item in bible_data]))

  with col1:
    selected_book = st.selectbox("성경 선택", books)

  chapters = list(
      dict.fromkeys([
          item["chapter"]
          for item in bible_data
          if item["book"] == selected_book
      ])
  )
  with col2:
    selected_chapter = st.selectbox("장 선택", chapters)

  verses = [
      item
      for item in bible_data
      if item["book"] == selected_book and item["chapter"] == selected_chapter
  ]
  with col3:
    selected_verse_num = st.selectbox("절 선택", [v["verse"] for v in verses])

  selected_item = next(v for v in verses if v["verse"] == selected_verse_num)

  st.markdown(
      f"### {selected_item['book']} {selected_item['chapter']}:{selected_item['verse']}"
  )
  st.info(f'"{selected_item["text"]}"')

  if st.button("이 구절 AI 해석 보기"):
    prompt = f"'{selected_item['book']} {selected_item['chapter']}:{selected_item['verse']}' 구절의 영적 의미와 묵상 포인트를 한글로 알기 쉽게 설명해줘."
    response = model.generate_content(prompt)
    st.write(response.text)

# --- TAB 2: 글자 수 기준 기간별 통독 플랜 ---
with tab2:
  st.sidebar.header("🗓️ 통독 설정")
  target_days = st.sidebar.number_input(
      "몇 일 동안 통독하시겠습니까?", min_value=1, max_value=1000, value=90
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
      "읽을 일차(Day) 선택", min_value=1, max_value=target_days, value=1
  )

  today_verses = plan.get(selected_day, [])
  if today_verses:
    st.subheader(
        f"📍 Day {selected_day}: {today_verses[0]['book']}"
        f" {today_verses[0]['chapter']}:{today_verses[0]['verse']} ~"
        f" {today_verses[-1]['book']}"
        f" {today_verses[-1]['chapter']}:{today_verses[-1]['verse']}"
    )
    st.caption(
        f"오늘 분량: 총 {len(today_verses)}개 구절 (약"
        f" {sum(len(v['text']) for v in today_verses)}자)"
    )

    with st.expander("오늘의 성경 본문 열기", expanded=True):
      for v in today_verses:
        st.write(f"**[{v['book']} {v['chapter']}:{v['verse']}]** {v['text']}")

    if st.button("오늘 분량 AI 묵상 가이드 생성"):
      text_chunk = " ".join([
          f"{v['book']}{v['chapter']}:{v['verse']} {v['text']}"
          for v in today_verses[:15]
      ])
      prompt = (
          f"다음은 오늘 읽을 성경 본문의 일부입니다:\n{text_chunk}\n\n이 본문의 핵심"
          " 주제 3가지와 오늘 삶에 적용할 묵상 질문 2가지를 작성해줘."
      )
      res = model.generate_content(prompt)
      st.write(res.text)
