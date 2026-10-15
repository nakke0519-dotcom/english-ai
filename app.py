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

# --- 기본 문제 데이터 생성 ---
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

# --- 문제 데이터 불러오기/저장 ---
def load_problem_bank():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except Exception:
            pass
    return get_default_bank()

def save_problem_bank(data):
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

# --- 학생 제출 데이터 불러오기/저장 (60분 자동 삭제 로직) ---
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
if "PROBLEM_BANK" not in st.session_state:
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
        
        # 교사 모드일 때만 10초 주기 자동 새로고침 동작
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

options_map = {f"{st.session_state['PROBLEM_BANK'][i]['title']}": i for i in range(1, 36)}

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
