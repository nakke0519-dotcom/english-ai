import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="영어 지문 AI 피드백 Teacher", page_icon="📖", layout="wide")

# --- API 키 확인 ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Google Gemini API 키가 설정되지 않았습니다. 관리자 설정을 확인해주세요.")
    st.stop()

# Gemini API 설정
genai.configure(api_key=api_key)

# --------------------------------------------------------------------------
# 📚 [40개 문제 은행]
# 아래 양식에 맞추어 지문과 모범 답안을 추가/수정해 주시면 됩니다.
# --------------------------------------------------------------------------
PROBLEM_BANK = {
    "지문 1: 일기 쓰기와 스트레스 관리": {
        "passage": """Research shows that people who keep a journal regularly tend to manage stress better than those who do not. Writing down thoughts and feelings helps process complex emotions and reduces psychological burden. Furthermore, it offers an opportunity to reflect on daily activities and improve decision-making skills.""",
        "key_points": """- 키워드: Journaling, Stress management, Reflect
- 주제: 일기 쓰기가 스트레스 해소 및 감정 정리에 미치는 긍정적 영향
- 흐름: 연구 결과 소개 -> 일기 쓰기의 감정적 이점 -> 반성 및 의사결정 능력 향상으로 연결"""
    },
    "지문 2: 수면과 기억력의 관계": {
        "passage": """Sleep plays a crucial role in consolidating memories formed during the day. When we sleep, the brain reorganizes and stores information into long-term memory. Lack of sleep impairs attention, working memory, and logical reasoning, leading to lower academic performance.""",
        "key_points": """- 키워드: Sleep, Memory consolidation, Brain
- 주제: 수면이 기억 저장 및 학습 능력 향상에 미치는 중요성
- 흐름: 수면의 기억 저장 역할 -> 뇌의 정보 정리 과정 -> 수면 부족 시 나타나는 부정적 영향"""
    },
    "지문 3: 기술 발달과 환경 문제": {
        "passage": """While technological advancements have made human life more convenient, they have also contributed to severe environmental degradation. Electronic waste and high energy consumption by data centers pose significant challenges. Therefore, sustainable technological innovations are urgently required.""",
        "key_points": """- 키워드: Technology, Environmental degradation, Sustainability
- 주제: 기술 발전이 가져온 환경적 문제와 지속 가능한 혁신의 필요성
- 흐름: 기술 발전의 편의성 -> 전자기기 쓰레기 및 에너지 소비 등 부작용 -> 지속 가능한 기술 개발 촉구"""
    },
    # 💡 4번부터 40번 지문은 위 양식을 그대로 복사해서 아래에 계속 추가하시면 됩니다!
}

# --- 헤더 ---
st.title("📖 영어 모의고사 독해 AI 피드백")
st.write("원하는 문제를 선택하고 지문을 읽은 뒤 답변을 작성하세요.")

# --- 지문 선택 드롭다운 ---
selected_title = st.selectbox(
    "📌 풀고 싶은 문제를 선택하세요:",
    list(PROBLEM_BANK.keys())
)

selected_problem = PROBLEM_BANK[selected_title]

# --- 교사 전용 수정 사이드바 (필요 시 선택된 문제 수정 가능) ---
with st.sidebar:
    st.header("⚙️ [교사용] 현재 문제 실시간 편집")
    st.caption("여기서 수정하는 내용은 화면에 즉시 반영됩니다.")
    passage = st.text_area("영어 지문", height=200, value=selected_problem["passage"])
    key_points = st.text_area("모범 답안 / 핵심 요소", height=150, value=selected_problem["key_points"])

# --- 학생 입력 영역 ---
st.markdown("---")
st.subheader(f"📝 {selected_title}")
st.info(passage)

col1, col2 = st.columns(2)
with col1:
    user_keywords = st.text_input("1. 지문의 핵심 키워드", key=f"kw_{selected_title}")
    user_topic = st.text_input("2. 주제 한 문장 요약", key=f"tp_{selected_title}")
with col2:
    user_flow = st.text_area("3. 글의 흐름 세 문장 요약", height=100, key=f"fl_{selected_title}")

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
            1. 핵심 키워드: {user_keywords}
            2. 주제 한 문장 요약: {user_topic}
            3. 글의 흐름 세 문장 요약: {user_flow}

            [피드백 작성 지침]
            1. 첫 줄에는 반드시 "정답률: O%" 형태로 종합 점수를 적어주세요. (예: 75% 정답입니다.)
            2. 학생이 적은 1) 핵심 키워드, 2) 주제 한 문장 요약, 3) 글의 흐름 세 문장 요약을 각각 나누어 평가해 주세요.
            3. 잘한 점(맞춘 키워드나 적절한 맥락 파악)을 칭찬해주세요.
            4. 부족하거나 보완해야 할 점(누락된 정보, 3문장 요약 형식을 지켰는지 등)을 따뜻하게 지적해 주세요.
            5. 정답률을 올리기 위한 간단한 한 줄 조언을 덧붙여주세요.
            """

            try:
                model = genai.GenerativeModel('gemini-3.8-flash')
                response = model.generate_content(prompt)
                
                feedback = response.text
                st.success("피드백 작성이 완료되었습니다!")
                st.markdown("### 📊 AI 피드백 결과")
                st.write(feedback)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
