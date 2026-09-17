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
  possible_filenames = [
      "bible.json",
      "bible_data.json",
      "data.json",
      "krv.json",
      "ko_bible.json",
  ]
  raw_data = None
  used_filename = None

  # 다양한 인코딩 시도 (utf-8, utf-8-sig, cp949)
  for fname in possible_filenames:
    for enc in ["utf-8-sig", "utf-8", "cp949"]:
      try:
        with open(fname, "r", encoding=enc) as f:
          raw_data = json.load(f)
          used_filename = fname
          break
      except:
        continue
    if raw_data is not None:
      break

  formatted_data = []

  if raw_data:
    # 1. 리스트 형태인 경우
    if isinstance(raw_data, list):
      for item in raw_data:
        if not isinstance(item, dict):
          continue
        b_val = (
            item.get("book")
            or item.get("book_name")
            or item.get("name")
            or item.get("book_no")
        )
        if isinstance(b_val, int) and 1 <= b_val <= 66:
          book_name = BOOK_NAMES[b_val - 1]
        else:
          book_name = str(b_val) if b_val else "창세기"

        chapter = (
            item.get("chapter")
            or item.get("chap")
            or item.get("c")
            or item.get("chapter_number")
            or 1
        )
        verse = (
            item.get("verse")
            or item.get("ver")
            or item.get("v")
            or item.get("verse_number")
            or 1
        )
        text = (
            item.get("text")
            or item.get("content")
            or item.get("message")
            or item.get("verse_text")
            or ""
        )

        if text:
          try:
            formatted_data.append({
                "book": book_name,
                "chapter": int(chapter),
                "verse": int(verse),
                "text": str(text).strip(),
            })
          except:
            pass

    # 2. 딕셔너리 형태인 경우 (책 이름이 키인 구조)
    elif isinstance(raw_data, dict):
      for b_key, b_val in raw_data.items():
        b_name = str(b_key)
        if isinstance(b_val, dict):
          for c_key, c_val in b_val.items():
            try:
              c_num = int(c_key)
            except:
              continue

            # c_val이 딕셔너리인 경우 (절 번호 -> 본문)
            if isinstance(c_val, dict):
              for v_key, v_text in c_val.items():
                try:
                  v_num = int(v_key)
                  formatted_data.append({
                      "book": b_name,
                      "chapter": c_num,
                      "verse": v_num,
                      "text": str(v_text).strip(),
                  })
                except:
                  pass
            # c_val이 리스트인 경우 (인덱스가 곧 절 번호 - 1인 형태)
            elif isinstance(c_val, list):
              for v_idx, v_item in enumerate(c_val):
                v_num = v_idx + 1
                if isinstance(v_item, str):
                  formatted_data.append({
                      "book": b_name,
                      "chapter": c_num,
                      "verse": v_num,
                      "text": v_item.strip(),
                  })
                elif isinstance(v_item, dict):
                  t = (
                      v_item.get("text")
                      or v_item.get("content")
                      or v_item.get("verse")
                  )
                  if t:
                    formatted_data.append({
                        "book": b_name,
                        "chapter": c_num,
                        "verse": v_num,
                        "text": str(t).strip(),
                    })
        elif isinstance(b_val, list):
          for item in b_val:
            if isinstance(item, dict):
              c = item.get("chapter") or item.get("chap") or 1
              v = item.get("verse") or item.get("ver") or 1
              t = item.get("text") or item.get("content") or ""
              if t:
                try:
                  formatted_data.append({
                      "book": b_name,
                      "chapter": int(c),
                      "verse": int(v),
                      "text": str(t).strip(),
                  })
                except:
                  pass

  if formatted_data:
    return formatted_data, used_filename

  # 파일을 전혀 읽지 못한 경우 시뮬레이션 반환
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

  generated_bible = []
  for b_name, c_count in book_chapters.items():
    for c in range(1, c_count + 1):
      for v in range(1, 16):
        text = (
            f"{{{b_name} {c}장 {v}절}} 주님의 진리의 말씀과 은혜의 언약이"
            " 선포되는 거룩한 본문입니다."
        )
        generated_bible.append(
            {"book": b_name, "chapter": c, "verse": v, "text": text}
        )
  return generated_bible, None


bible_data, loaded_filename = load_bible()

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

# 파일 로드 상태 표시
if loaded_filename:
  st.sidebar.success(
      f"✅ 성경 파일 로드 성공: `{loaded_filename}` ({len(bible_data):,}구절)"
  )
else:
  st.sidebar.error(
      "⚠️ 실제 성경 파일을 읽지 못해 시뮬레이션 본문이 출력 중입니다."
  )

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


# --- 장(Chapter) 단위로 깔끔하게 묶어서 분배하는 함수 ---
@st.cache_data
def build_reading_plan_by_chapter(data, total_days):
  chapters_dict = {}
  for item in data:
    key = (item["book"], item["chapter"])
    if key not in chapters_dict:
      chapters_dict[key] = []
    chapters_dict[key].append(item)

  chapter_keys = list(chapters_dict.keys())
  total_chapters = len(chapter_keys)

  plan = {}
  if total_chapters == 0:
    for day in range(1, total_days + 1):
      plan[day] = data
    return plan

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
