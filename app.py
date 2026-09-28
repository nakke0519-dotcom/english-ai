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
                
                for i in range(1, 36):
                    if i in parsed_data:
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
    
    st.markdown("---")
    st.subheader("❓ 학생 질문 세부 설정")
    q1_text = st.text_input("첫 번째 질문 발문", value=selected_problem.get("q1", "1. 지문의 핵심 키워드"), key=f"q1_in_{selected_id}")
    q2_text = st.text_input("두 번째 질문 발문", value=selected_problem.get("q2", "2. 주제 한 문장 요약"), key=f"q2_in_{selected_id}")
    q3_text = st.text_input("세 번째 질문 발문", value=selected_problem.get("q3", "3. 글의 흐름 세 문장 요약"), key=f"q3_in_{selected_id}")

    st.markdown("---")
    # 2. 지문 및 모범답안 수정
    new_passage = st.text_area("영어 지문", height=200, value=selected_problem.get("passage", ""), key=f"passage_input_{selected_id}")
    new_key_points = st.text_area("모범 답안 / 핵심 요소 및 채점 기준", height=150, value=selected_problem.get("key_points", ""), key=f"key_input_{selected_id}")

    # 저장 버튼
    if st.button("💾 변경사항 전체 저장", type="primary"):
        st.session_state["PROBLEM_BANK"][selected_id]["title"] = new_title
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
st.info(selected_problem['passage'])

col1, col2 = st.columns(2)
with col1:
    user_ans1 = st.text_input(selected_problem.get("q1", "1. 지문의 핵심 키워드"), key=f"ans1_{selected_id}")
    user_ans2 = st.text_input(selected_problem.get("q2", "2. 주제 한 문장 요약"), key=f"ans2_{selected_id}")
with col2:
    user_ans3 = st.text_area(selected_problem.get("q3", "3. 글의 흐름 세 문장 요약"), height=100, key=f"ans3_{selected_id}")

# --- AI 피드백 생성 ---
if st.button("🚀 AI 피드백 받기", type="primary"):
    if not (user_ans1 and user_ans2 and user_ans3):
        st.warning("모든 질문에 답을 작성한 뒤 버튼을 눌러주세요!")
    else:
        with st.spinner("AI 선생님이 수능 출제 매커니즘에 기반하여 분석 중입니다..."):
            prompt = f"""
            당신은 EBS '수능특강 Light 영어독해연습' 및 대학수학능력시험 영어영역에 매우 정통한 베테랑 고등학교 영어 교사입니다.
            제시된 지문은 '수능특강 Light 영어독해연습' 수준의 구문이며, 문제 유형은 수능 및 모의고사 출제 유형에 해당합니다.

            학생이 작성한 답안을 바탕으로 다음과 같은 기준에 맞추어 전문적이고 친절한 피드백을 제공해주세요.

            [영어 지문]
            {selected_problem['passage']}

            [모범 답안 및 채점 기준]
            {selected_problem['key_points']}

            [학생이 작성한 질문 및 답안]
            - 질문 1: {selected_problem.get('q1')}
              학생 답안: {user_ans1}
            - 질문 2: {selected_problem.get('q2')}
              학생 답안: {user_ans2}
            - 질문 3: {selected_problem.get('q3')}
              학생 답안: {user_ans3}

            [피드백 작성 가이드라인]
            1. **종합 정답률 평가**: 첫 줄에 반드시 "정답률: O%" 형태로 점수를 적어주세요.
            2. **글의 핵심 주제 및 키워드 파악 평가**:
               - 문제 유형과 관계없이 학생이 글의 핵심 주제와 키워드를 얼마나 정확하게 파악했는지 평가해주세요.
            3. **수능/모의고사 접근 전략 제시**:
               - 해당 지문과 수능 유형 문제를 풀기 위해 학생이 어떻게 접근해야 했는지, 글을 읽을 때 어떤 요소(접속사, 대조 구조, 핵심 소재 등)를 중점적으로 살펴야 하는지 전략적으로 설명해주세요.
            4. **오답 요인 예측 및 분석 (오답이 있는 경우)**:
               - 학생이 오답이나 아쉬운 답변을 냈다면, 왜 지문의 특정 부분에 낚이거나 헷갈렸을지(예: 일부 단어에만 얽매임, 부분적 해석 오류 등) 원인을 추측해 분석해 주세요.
               - 왜 그것이 오답이며 정답 기준과 어떤 차이가 있는지 확실한 근거를 지문 기반으로 제시해 주세요.
            5. **따뜻한 총평 및 실전 한 줄 조언**:
               - 잘한 점을 격려하고 다음 실전 풀이 시 유용한 한 줄 팁을 남겨주세요.
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
