import streamlit as st
import google.generativeai as genai
import json
import os

st.set_page_config(page_title="영어 지문 AI 피드백 Teacher", page_icon="📖", layout="wide")

# --- API 키 확인 ---
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Google Gemini API 키가 설정되지 않았습니다. 관리자 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

DATA_FILE = "problem_bank.json"

# --- 기본 문제 데이터 생성 ---
def get_default_bank():
    default_bank = {}
    
    # 예시 지문 3개
    default_bank[1] = {
        "title": "지문 1: 일기 쓰기와 스트레스 관리",
        "type": "기본 분석 (키워드/주제/흐름)",
        "q1": "1. 지문의 핵심 키워드",
        "q2": "2. 주제 한 문장 요약",
        "q3": "3. 글의 흐름 세 문장 요약",
        "passage": """Research shows that people who keep a journal regularly tend to manage stress better than those who do not. Writing down thoughts and feelings helps process complex emotions and reduces psychological burden. Furthermore, it offers an opportunity to reflect on daily activities and improve decision-making skills.""",
        "key_points": """- 키워드: Journaling, Stress management, Reflect
- 주제: 일기 쓰기가 스트레스 해소 및 감정 정리에 미치는 긍정적 영향
- 흐름: 연구 결과 소개 -> 일기 쓰기의 감정적 이점 -> 반성 및 의사결정 능력 향상으로 연결"""
    }
    default_bank[2] = {
        "title": "지문 2: 수면과 기억력의 관계",
        "type": "기본 분석 (키워드/주제/흐름)",
        "q1": "1. 지문의 핵심 키워드",
        "q2": "2. 주제 한 문장 요약",
        "q3": "3. 글의 흐름 세 문장 요약",
        "passage": """Sleep plays a crucial role in consolidating memories formed during the day. When we sleep, the brain reorganizes and stores information into long-term memory. Lack of sleep impairs attention, working memory, and logical reasoning, leading to lower academic performance.""",
        "key_points": """- 키워드: Sleep, Memory consolidation, Brain
- 주제: 수면이 기억 저장 및 학습 능력 향상에 미치는 중요성
- 흐름: 수면의 기억 저장 역할 -> 뇌의 정보 정리 과정 -> 수면 부족 시 나타나는 부정적 영향"""
    }
    default_bank[3] = {
        "title": "지문 3: 기술 발달과 환경 문제",
        "type": "기본 분석 (키워드/주제/흐름)",
        "q1": "1. 지문의 핵심 키워드",
        "q2": "2. 주제 한 문장 요약",
        "q3": "3. 글의 흐름 세 문장 요약",
        "passage": """While technological advancements have made human life more convenient, they have also contributed to severe environmental degradation. Electronic waste and high energy consumption by data centers pose significant challenges. Therefore, sustainable technological innovations are urgently required.""",
        "key_points": """- 키워드: Technology, Environmental degradation, Sustainability
- 주제: 기술 발전이 가져온 환경적 문제와 지속 가능한 혁신의 필요성
- 흐름: 기술 발전의 편의성 -> 전자기기 쓰레기 및 에너지 소비 등 부작용 -> 지속 가능한 기술 개발 촉구"""
    }

    for i in range(4, 36):
        default_bank[i] = {
            "title": f"지문 {i}: (제목을 입력하세요)",
            "type": "기본 분석 (키워드/주제/흐름)",
            "q1": "1. 지문의 핵심 키워드",
            "q2": "2. 주제 한 문장 요약",
            "q3": "3. 글의 흐름 세 문장 요약",
            "passage": f"여기에 {i}번 영어 지문을 입력하세요.",
            "key_points": "- 키워드: \n- 주제: \n- 흐름: "
        }
    return default_bank

# --- 데이터 불러오기/저장 함수 ---
def load_problem_bank():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                parsed_data = {int(k): v for k, v in data.items()}
                
                # 구버전 데이터 호환 처리 (질문 항목이 없는 경우 채워넣기)
                for i in range(1, 36):
                    if i in parsed_data:
                        if "type" not in parsed_data[i]:
                            parsed_data[i]["type"] = "기본 분석 (키워드/주제/흐름)"
                        if "q1" not in parsed_data[i]:
                            parsed_data[i]["q1"] = "1. 지문의 핵심 키워드"
                        if "q2" not in parsed_data[i]:
                            parsed_data[i]["q2"] = "2. 주제 한 문장 요약"
                        if "q3" not in parsed_data[i]:
                            parsed_data[i]["q3"] = "3. 글의 흐름 세 문장 요약"
                return parsed_data
        except Exception:
            pass
    return get_default_bank()

def save_problem_bank(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 세션 데이터 초기화
if "PROBLEM_BANK" not in st.session_state:
    st.session_state["PROBLEM_BANK"] = load_problem_bank()

# --- 헤더 ---
st.title("📖 영어 모의고사 독해 AI 피드백")
st.write("원하는 문제를 선택하고 지문을 읽은 뒤 답변을 작성하세요.")

# --- 지문 선택 드롭다운 (1번 ~ 35번) ---
options_map = {f"{st.session_state['PROBLEM_BANK'][i]['title']}": i for i in range(1, 36)}

selected_option_label = st.selectbox(
    "📌 풀고 싶은 문제를 선택하세요:",
    list(options_map.keys())
)

selected_id = options_map[selected_option_label]
selected_problem = st.session_state["PROBLEM_BANK"][selected_id]

# --- 교사 전용 수정 사이드바 ---
with st.sidebar:
    st.header(f"⚙️ [교사용] {selected_id}번 문제 수정")
    st.caption("수정 후 아래 [💾 변경사항 전체 저장] 버튼을 누르면 모든 학생에게 반영됩니다.")
    
    # 1. 제목 수정
    new_title = st.text_input("문제 이름 (드롭다운 표시명)", value=selected_problem.get("title", ""), key=f"title_input_{selected_id}")
    
    # 2. 문제 유형 및 질문 설정
    type_options = ["기본 분석 (키워드/주제/흐름)", "서술형 / 요약문 완성", "어휘 및 주요 문장 분석", "자유 질문 (직접 입력)"]
    current_type = selected_problem.get("type", "기본 분석 (키워드/주제/흐름)")
    type_index = type_options.index(current_type) if current_type in type_options else 3
    
    selected_type = st.selectbox("🎯 문제 유형 선택", type_options, index=type_index, key=f"type_select_{selected_id}")
    
    # 유형별 질문 자동 채우기 또는 자유 작성
    if selected_type == "기본 분석 (키워드/주제/흐름)":
        default_q1, default_q2, default_q3 = "1. 지문의 핵심 키워드", "2. 주제 한 문장 요약", "3. 글의 흐름 세 문장 요약"
    elif selected_type == "서술형 / 요약문 완성":
        default_q1, default_q2, default_q3 = "1. 핵심 세부사항 정리", "2. 지문 요약문 작성 (2~3문장)", "3. 글의 핵심 주제문"
    elif selected_type == "어휘 및 주요 문장 분석":
        default_q1, default_q2, default_q3 = "1. 핵심 어휘 및 의미 파악", "2. 가장 중요한 문장 해석", "3. 지문의 요지 요약"
    else:  # 자유 질문
        default_q1 = selected_problem.get("q1", "1. 질문 1")
        default_q2 = selected_problem.get("q2", "2. 질문 2")
        default_q3 = selected_problem.get("q3", "3. 질문 3")

    st.markdown("---")
    st.subheader("❓ 학생 질문 세부 설정")
    q1_text = st.text_input("첫 번째 질문 발문", value=default_q1, key=f"q1_in_{selected_id}")
    q2_text = st.text_input("두 번째 질문 발문", value=default_q2, key=f"q2_in_{selected_id}")
    q3_text = st.text_input("세 번째 질문 발문", value=default_q3, key=f"q3_in_{selected_id}")

    st.markdown("---")
    # 3. 지문 및 모범답안 수정
    new_passage = st.text_area("영어 지문", height=200, value=selected_problem.get("passage", ""), key=f"passage_input_{selected_id}")
    new_key_points = st.text_area("모범 답안 / 핵심 요소 및 채점 기준", height=150, value=selected_problem.get("key_points", ""), key=f"key_input_{selected_id}")

    # 저장 버튼
    if st.button("💾 변경사항 전체 저장", type="primary"):
        st.session_state["PROBLEM_BANK"][selected_id]["title"] = new_title
        st.session_state["PROBLEM_BANK"][selected_id]["type"] = selected_type
        st.session_state["PROBLEM_BANK"][selected_id]["q1"] = q1_text
        st.session_state["PROBLEM_BANK"][selected_id]["q2"] = q2_text
        st.session_state["PROBLEM_BANK"][selected_id]["q3"] = q3_text
        st.session_state["PROBLEM_BANK"][selected_id]["passage"] = new_passage
        st.session_state["PROBLEM_BANK"][selected_id]["key_points"] = new_key_points
        
        save_problem_bank(st.session_state["PROBLEM_BANK"])
        st.success("성공적으로 저장되었습니다! 학생들의 화면에도 동기화됩니다.")
        st.rerun()

# --- 학생 입력 영역 ---
st.markdown("---")
st.subheader(f"📝 {selected_problem['title']}")
st.caption(f"📌 **문제 유형**: {selected_problem.get('type', '기본 분석')}")
st.info(selected_problem['passage'])

col1, col2 = st.columns(2)
with col1:
    user_ans1 = st.text_input(selected_problem.get("q1", "1. 질문 1"), key=f"ans1_{selected_id}")
    user_ans2 = st.text_input(selected_problem.get("q2", "2. 질문 2"), key=f"ans2_{selected_id}")
with col2:
    user_ans3 = st.text_area(selected_problem.get("q3", "3. 질문 3"), height=100, key=f"ans3_{selected_id}")

# --- AI 피드백 생성 ---
if st.button("🚀 AI 피드백 받기", type="primary"):
    if not (user_ans1 and user_ans2 and user_ans3):
        st.warning("모든 질문에 답을 작성한 뒤 버튼을 눌러주세요!")
    else:
        with st.spinner("AI 선생님이 답변을 분석 중입니다..."):
            prompt = f"""
            당신은 친절하고 전문적인 고등학교 영어 교사입니다.
            학생이 제출한 답안을 평가하고 구체적이고 따뜻한 피드백을 제공해주세요.

            [문제 유형]
            {selected_problem.get('type', '일반 분석')}

            [영어 지문]
            {selected_problem['passage']}

            [모범 답안 및 평가 기준]
            {selected_problem['key_points']}

            [학생이 작성한 질문 및 답안]
            - 질문 1: {selected_problem.get('q1')}
              학생 답안: {user_ans1}
            - 질문 2: {selected_problem.get('q2')}
              학생 답안: {user_ans2}
            - 질문 3: {selected_problem.get('q3')}
              학생 답안: {user_ans3}

            [피드백 작성 지침]
            1. 첫 줄에는 반드시 "정답률: O%" 형태로 종합 점수를 적어주세요. (예: 75% 정답입니다.)
            2. 학생이 적은 각 질문별 답안(1번, 2번, 3번)을 각각 나누어 세심하게 평가해 주세요.
            3. 잘한 점(지문 이해도, 정확성 등)을 칭찬해주세요.
            4. 부족하거나 보완해야 할 점(누락된 정보, 요구사항 준수 여부 등)을 따뜻하게 지적해 주세요.
            5. 정답률을 높이기 위한 실질적인 한 줄 조언을 덧붙여주세요.
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
