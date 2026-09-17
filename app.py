import streamlit as st
import json
import os
from google import genai
from google.genai import types

st.set_page_config(page_title="한국어 AI 성경 관주 앱", layout="wide")
st.title("📖 AI 성경 관주 연구소")

# API 키 자동 불러오기 (Streamlit Secrets 연동)
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    api_key = st.sidebar.text_input("Gemini API Key를 입력하세요:", type="password")

if not api_key:
    st.info("좌측 사이드바에 Gemini API 키를 입력하면 AI 기능이 활성화됩니다.")
    st.stop()

client = genai.Client(api_key=api_key)

@st.cache_data
def load_bible_data():
    try:
        with open("bible_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

bible_data = load_bible_data()

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📜 성경 본문 및 관주(Cross-Reference)")
    if bible_data:
        options = [f"{item['book']} {item['chapter']}:{item['verse']}" for item in bible_data]
        selected_verse_str = st.selectbox("구절 선택:", options)
        selected_item = next(item for item in bible_data if f"{item['book']} {item['chapter']}:{item['verse']}" == selected_verse_str)
        
        st.markdown(f"### **{selected_verse_str}**")
        st.info(f"\"{selected_item['text']}\"")
        
        st.markdown("#### 🔗 연결된 관주 구절")
        for ref in selected_item.get("cross_references", []):
            st.write(f"- **{ref}**")
    else:
        st.error("bible_data.json 파일을 찾을 수 없습니다.")

with col2:
    st.subheader("🤖 Gemini 성경 해석 & 관주 분석")
    if bible_data:
        user_query = st.text_area(
            "질문을 입력하세요:", 
            value=f"'{selected_verse_str}' 구절과 관주 구절들이 영적으로 어떻게 연결되는지 한글로 상세히 설명해줘.",
            height=100
        )
        
        if st.button("AI에게 질문하기", type="primary"):
            with st.spinner("Gemini가 성경 분석 중입니다..."):
                system_instruction = "당신은 성경 연구 전문 AI 보조자입니다. 제공된 본문과 관주 데이터를 바탕으로 질문에 대해 깊이 있고 친절하게 한국어로 답변하세요."
                prompt = f"[현재 선택된 구절]\n{selected_verse_str}: {selected_item['text']}\n\n[등록된 관주 목록]\n{', '.join(selected_item.get('cross_references', []))}\n\n[사용자 질문]\n{user_query}"
                
                try:
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.3
                        )
                    )
                    st.markdown("### 💡 AI 답변")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
                  
