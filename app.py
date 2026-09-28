import streamlit as st
from google import genai

st.set_page_config(page_title="영어 지문 AI 피드백 Teacher", page_icon="📖")

st.title("📖 영어 모의고사 독해 AI 피드백")
st.write("지문을 읽고 질문에 답을 작성한 뒤 아래 **[AI 피드백 받기]** 버튼을 누르세요.")

# --- API 키 확인 ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Google Gemini API 키가 설정되지 않았습니다. 관리자 설정을 확인해주세요.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- 교사 입력 영역 (지문 및 모범답안) ---
with st.sidebar:
    st.header("⚙️ [교사용] 문제 설정")
    passage = st.text_area("영어 지문 입력", height=200, value="""Research shows that people who keep a journal regularly tend to manage stress better than those who do not. Writing down thoughts and feelings helps process complex emotions and reduces psychological burden. Furthermore, it offers an opportunity to reflect on daily activities and improve decision-making skills.""")
    key_points = st.text_area("모범 답안 / 핵심 요소", height=150, value="""- 키워드: Journaling, Stress management, Reflect
- 주제: 일기 쓰기가 스트레스 해소 및 감정 정리에 미치는 긍정적 영향
- 흐름: 연구 결과 소개 -> 일기 쓰기의 감정적 이점 -> 반성 및 의사결정 능력 향상으로 연결""")

# --- 학생 입력 영역 ---
st.subheader("📝 문제: 아래 지문을 읽고 답변을 작성하세요.")
st.info(passage)

col1, col2 = st.columns(2)
with col1:
    user_keywords = st.text_input("1. 지문의 핵심 키워드 (2~3개)")
    user_topic = st.text_input("2. 생각한 지문의 주제")
with col2:
    user_flow = st.text_area("3. 글의 전체적인 흐름 (서론-본론-결론 등)", height=100)

# --- AI 피드백 생성 ---
if st.button("🚀 AI 피드백 받기", type="primary"):
    if not (user_keywords and user_topic and user_flow):
        st.warning("모든 질문에 답을 작성한 뒤 버튼을 눌러주세요!")
    else:
        with st.spinner("AI 선생님이 답변을 분석 중입니다..."):
            prompt = f"""
            당신은 친절하고 전문적인 고등학교 영어 교사입니다.
            학생이 제출한 지문 분석 답안을 평가하고 구체적이고 따뜻한 피드백을 제공해주세요.

            [영어 지문]
            {passage}

            [모범 답안 / 기준]
            {key_points}

            [학생이 제출한 답안]
            - 학생의 키워드: {user_keywords}
            - 학생의 주제: {user_topic}
            - 학생의 글 흐름 분석: {user_flow}

            [피드백 작성 지침]
            1. 첫 줄에는 반드시 "정답률: O%" 형태로 종합 점수를 적어주세요. (예: 75% 정답입니다.)
            2. 잘한 점(맞춘 키워드나 적절한 파악)을 칭찬해주세요.
            3. 부족하거나 보완해야 할 점(누락된 맥락이나 아쉬운 표현)을 알려주세요.
            4. 정답률을 올리기 위한 간단한 한 줄 조언을 덧붙여주세요.
            """

            try:
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt,
                )
                
                feedback = response.text
                st.success("피드백 작성이 완료되었습니다!")
                st.markdown("### 📊 AI 피드백 결과")
                st.write(feedback)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
