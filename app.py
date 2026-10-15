import streamlit as st
import google.generativeai as genai
import json
import os
from datetime import datetime, timedelta

# 자동 새로고침 라이브러리 불러오기
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

st.set_page_config(page_title="ENGLISH READING AI ASSISTANT", page_icon="📖", layout="wide")

# --- API 키 및 비밀번호 확인 ---
api_key = st.secrets.get("GEMINI_API_KEY")
teacher_password = st.secrets.get("TEACHER_PASSWORD", "rnswltk1!")

if not api_key:
    st.error("Google Gemini API 키가 설정되지 않았습니다. Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

DATA_FILE = "problem_bank.json"
SUBMISSION_FILE = "submissions.json"

# --- 기본 문제 데이터 생성 (35개 풀세트) ---
def get_default_bank():
    default_bank = {}
    for i in range(1, 36):
        default_bank[i] = {
            "title": f"지문 {i}: (제목을 입력하세요)",
            "q1": "1. 지문의 핵심 키워드",
            "q2": "2. 주제 한 문장 요약",
            "q3": "3. 글의 흐름 세 문장 요약",
            "passage": f"여기에 {i}번 영어 지문을 입력하세요.",
            "key_points": ""
        }
    return default_bank

# --- 문제 데이터 안전하게 불러오기/저장 ---
def load_problem_bank():
    default_bank = get_default_bank()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                parsed_data = {}
                for k, v in data.items():
                    key_num = int(k)
                    # 누락된 필드 자동 보완
                    parsed_data[key_num] = {
                        "title": v.get("title", f"지문 {key_num}"),
                        "q1": v.get("q1", "1. 지문의 핵심 키워드"),
                        "q2": v.get("q2", "2. 주제 한 문장 요약"),
                        "q3": v.get("q3", "3. 글의 흐름 세 문장 요약"),
                        "passage": v.get("passage", f"여기에 {key_num}번 지문을 입력하세요."),
                        "key_points": v.get("key_points", "")
                    }
                # 1~35번 중 빠진 번호가 있다면 기본값 채워넣기
                for i in range(1, 36):
                    if i not in parsed_data:
                        parsed_data[i] = default_bank[i]
                return parsed_data
        except Exception as e:
            st.warning(f"problem_bank.json 파일 읽기 오류가 발생하여 기본 데이터를 불러옵니다: {e}")
            pass
    return default_bank

def save_problem_bank(data):
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

# --- 학생 제출 데이터 불러오기/저장 (60분 자동 삭제) ---
def load_submissions():
    if os.path.exists(SUBMISSION_FILE):
        try:
            with open(SUBMISSION_FILE, "r", encoding="utf-8") as f:
                submissions = json.load(f)
                
            now = datetime.now()
            valid_submissions = []
            for sub in submissions:
                sub_time = datetime.strptime(sub["timestamp"], "%Y-%m-%d %H:%M:%S")
                if now - sub_time <= timedelta(minutes=60):
                    valid_submissions.append(sub)
                    
            if len(valid_submissions) != len(submissions):
                with open(SUBMISSION_FILE, "w", encoding="utf-8") as f:
                    json.dump(valid_submissions, f, ensure_ascii=False, indent=2)
                    
            return valid_submissions
        except Exception:
            pass
    return []

def save_submission(record):
    submissions = load_submissions()
    submissions.append(record)
    json_str = json.dumps(submissions, ensure_ascii=False, indent=2)
    with open(SUBMISSION_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

# 세션 데이터 및 피드백 상태 초기화
if "PROBLEM_BANK" not in st.session_state or not st.session_state["PROBLEM_BANK"]:
    st.session_state["PROBLEM_BANK"] = load_problem_bank()

if "latest_feedback" not in st.session_state:
    st.session_state["latest_feedback"] = None

# --- 사이드바: 교사 제어판 ---
with st.sidebar:
    st.header("🔒 [교사용] 관리자 제어판")
    input_pwd = st.text_input("교사 비밀번호 입력", type="password")
    
    is_teacher = (input_pwd == teacher_password)
    
    if is_teacher:
        st.success("🔓 교사 인증 완료")
        if HAS_AUTOREFRESH:
            st_autorefresh(interval=10000, key="teacher_refresh")
    else:
        st.caption("비밀번호를 입력하면 교사 전용 관리 화면이 열립니다.")

# --- 메인 화면 ---
st.title("📖 ENGLISH READING AI ASSISTANT")
st.write("학번과 이름을 입력하고 문제를 선택하여 답변을 작성하세요.")

# --- 학생 이름 입력 및 지문 선택 ---
col_student, col_select = st.columns([1, 2])
with col_student:
    student_name = st.text_input("👤 학생 이름 (예: 10101 홍길동)", placeholder="학번과 이름을 입력하세요")

# 드롭다운 옵션 구성
options_map = {}
for i in range(1, 36):
    prob = st.session_state['PROBLEM_BANK'].get(i, {})
    title = prob.get('title', f"지문 {i}")
    options_map[f"{title}"] = i

with col_select:
    selected_option_label = st.selectbox(
        "📌 풀고 싶은 문제를 선택하세요:",
        list(options_map.keys())
    )

selected_id = options_map[selected_option_label]
selected_problem = st.session_state["PROBLEM_BANK"][selected_id]

# --- 교사 전용 수정, 백업 및 실시간 피드백 조회 ---
if is_teacher:
    with st.sidebar:
        st.markdown("---")
        st.header(f"⚙️ {selected_id}번 문제 수정")
        
        new_title = st.text_input("문제 이름", value=selected_problem.get("title", ""), key=f"title_{selected_id}")
        q1_text = st.text_input("첫 번째 질문", value=selected_problem.get("q1", "1. 지문의 핵심 키워드"), key=f"q1_{selected_id}")
        q2_text = st.text_input("두 번째 질문", value=selected_problem.get("q2", "2. 주제 한 문장 요약"), key=f"q2_{selected_id}")
        q3_text = st.text_input("세 번째 질문", value=selected_problem.get("q3", "3. 글의 흐름 세 문장 요약"), key=f"q3_{selected_id}")
        new_passage = st.text_area("영어 지문", height=150, value=selected_problem.get("passage", ""), key=f"pass_{selected_id}")
        new_key_points = st.text_area("추가 지시사항 / 채점 주의사항 (선택사항)", height=80, value=selected_problem.get("key_points", ""), key=f"key_{selected_id}", placeholder="특별히 강조할 키워드나 평가 방향이 있는 경우만 작성하세요. 비워두면 AI가 직접 지문을 분석합니다.")

        if st.button("💾 변경사항 적용", type="primary"):
            st.session_state["PROBLEM_BANK"][selected_id]["title"] = new_title
            st.session_state["PROBLEM_BANK"][selected_id]["q1"] = q1_text
            st.session_state["PROBLEM_BANK"][selected_id]["q2"] = q2_text
            st.session_state["PROBLEM_BANK"][selected_id]["q3"] = q3_text
            st.session_state["PROBLEM_BANK"][selected_id]["passage"] = new_passage
            st.session_state["PROBLEM_BANK"][selected_id]["key_points"] = new_key_points
            
            save_problem_bank(st.session_state["PROBLEM_BANK"])
            st.success("화면에 즉시 반영되었습니다!")
            st.rerun()

        st.markdown("---")
        st.header("📊 실시간 학생 답안 조회 (최근 60분)")
        submissions_data = load_submissions()
        
        if not submissions_data:
            st.info("최근 60분 이내에 제출된 학생 답안이 없습니다.")
        else:
            sorted_subs = sorted(submissions_data, key=lambda x: x.get("timestamp", ""), reverse=True)
            sub_labels = [f"{sub['student']} - {sub['problem_title']} ({sub['timestamp'].split()[1]})" for sub in sorted_subs]
            
            selected_sub_label = st.selectbox("📋 제출 내역 선택", sub_labels)
            selected_sub_idx = sub_labels.index(selected_sub_label)
            sub_info = sorted_subs[selected_sub_idx]
            
            st.markdown(f"**👤 학생**: {sub_info['student']}")
            st.markdown(f"**📖 지문**: {sub_info['problem_title']}")
            st.markdown(f"**⏰ 제출 시간**: {sub_info['timestamp']}")
            
            with st.expander("📝 학생 작성 답안 보기", expanded=True):
                st.write(f"**1. 키워드**: {sub_info['ans1']}")
                st.write(f"**2. 주제 요약**: {sub_info['ans2']}")
                st.write(f"**3. 흐름 요약**: {sub_info['ans3']}")
                
            with st.expander("🤖 전달된 AI 피드백 보기", expanded=False):
                st.write(sub_info['feedback'])

        st.markdown("---")
        st.header("📥 백업 파일 다운로드")
        st.caption("수정본을 GitHub에 커밋할 수 있도록 백업 파일을 다운로드받으세요.")
        bank_json = json.dumps(st.session_state["PROBLEM_BANK"], ensure_ascii=False, indent=2)
        st.download_button(
            label="problem_bank.json 다운로드",
            data=bank_json,
            file_name="problem_bank.json",
            mime="application/json"
        )

# --- 학생 문제 풀기 영역 ---
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
    if not student_name.strip():
        st.warning("상단에 학생 이름(학번)을 꼭 입력해 주세요!")
    elif not (user_ans1 and user_ans2 and user_ans3):
        st.warning("모든 질문에 답을 작성한 뒤 버튼을 눌러주세요!")
    else:
        with st.spinner("AI 선생님이 수능 출제 매커니즘에 기반하여 분석 중입니다..."):
            key_points_prompt = selected_problem.get('key_points', '').strip()
            if not key_points_prompt:
                key_points_prompt = "별도의 모범 답안이 지정되지 않았습니다. 지문의 내용과 구문 맥락을 AI가 직접 정확히 해석 및 평가하여 정답 여부를 판정하세요."

            passage_content = selected_problem['passage']
            q1_val = selected_problem.get('q1')
            q2_val = selected_problem.get('q2')
            q3_val = selected_problem.get('q3')

            prompt = (
                "당신은 EBS '수능특강 Light 영어독해연습' 및 대학수학능력시험 영어영역에 매우 정통한 베테랑 고등학교 영어 교사입니다.\n"
                "제시된 지문은 '수능특강 Light 영어독해연습' 수준의 구문이며, 문제 유형은 수능 및 모의고사 출제 유형에 해당합니다.\n\n"
                "제시된 [영어 지문]을 스스로 정확히 분석하여, 학생이 작성한 답안을 기준에 맞추어 전문적이고 친절하게 피드백 해주세요.\n\n"
                f"[영어 지문]\n{passage_content}\n\n"
                f"[교사의 추가 지시사항 및 특이 채점 기준]\n{key_points_prompt}\n\n"
                f"[학생이 작성한 질문 및 답안]\n"
                f"- 질문 1: {q1_val}\n  학생 답안: {user_ans1}\n"
                f"- 질문 2: {q2_val}\n  학생 답안: {user_ans2}\n"
                f"- 질문 3: {q3_val}\n  학생 답안: {user_ans3}\n\n"
                "[피드백 작성 가이드라인]\n"
                '1. **종합 정답률 평가**: 첫 줄에 반드시 "정답률: O%" 형태로 점수를 적어주세요.\n'
                "2. **글의 핵심 주제 및 키워드 파악 평가**:\n"
                "   - 문제 유형과 관계없이 학생이 글의 핵심 주제와 키워드를 얼마나 정확하게 파악했는지 평가해주세요.\n"
                "3. **수능/모의고사 접근 전략 제시**:\n"
                "   - 해당 지문과 수능 유형 문제를 풀기 위해 학생이 어떻게 접근해야 했는지, 글을 읽을 때 어떤 요소(접속사, 대조 구조, 핵심 소재 등)를 중점적으로 살펴야 하는지 전략적으로 설명해주세요.\n"
                "4. **오답 요인 예측 및 분석 (오답이 있는 경우)**:\n"
                "   - 학생이 오답이나 아쉬운 답변을 냈다면, 왜 지문의 특정 부분에 낚이거나 헷갈렸을지(예: 일부 단어에만 얽매임, 부분적 해석 오류 등) 원인을 추측해 분석해 주세요.\n"
                "   - 왜 그것이 오답이며 정답 기준과 어떤 차이가 있는지 확실한 근거를 지문 기반으로 제시해 주세요.\n"
                "5. **따뜻한 총평 및 실전 한 줄 조언**:\n"
                "   - 잘한 점을 격려하고 다음 실전 풀이 시 유용한 한 줄 팁을 남겨주세요."
            )

            try:
                model = genai.GenerativeModel('gemini-3.1-flash-lite')
                response = model.generate_content(prompt)
                
                feedback = response.text
                
                record = {
                    "student": student_name.strip(),
                    "problem_id": selected_id,
                    "problem_title": selected_problem['title'],
                    "ans1": user_ans1,
                    "ans2": user_ans2,
                    "ans3": user_ans3,
                    "feedback": feedback,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_submission(record)

                st.session_state["latest_feedback"] = {
                    "problem_title": selected_problem['title'],
                    "content": feedback
                }

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# 세션 상태에 저장된 피드백 출력 (새로고침 시에도 유지)
if st.session_state["latest_feedback"]:
    st.markdown("---")
    st.success("피드백 작성이 완료되었습니다!")
    st.markdown(f"### 📊 AI 피드백 결과 ({st.session_state
