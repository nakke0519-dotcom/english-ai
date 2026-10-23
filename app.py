import streamlit as st
import google.generativeai as genai
import json
import os
import re
from datetime import datetime, timedelta

# GitHub API 라이브러리 불러오기
try:
    from github import Github
    HAS_GITHUB = True
except ImportError:
    HAS_GITHUB = False

st.set_page_config(page_title="ENGLISH READING AI ASSISTANT", page_icon="📖", layout="wide")

# --- Custom CSS: 지문 상자 줄 간격 확대 및 마우스 호버 툴팁 스타일 ---
st.markdown("""
    <style>
    .passage-box {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 25px 30px;
        font-size: 18px;
        line-height: 2.3;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #1f2937;
        margin-bottom: 20px;
        word-break: break-word;
    }
    
    /* 호버 툴팁 스타일 (밑줄 제거, 볼드체 강조) */
    .vocab-tooltip {
        position: relative;
        display: inline-block;
        font-weight: bold;
        color: #1d4ed8;
        cursor: pointer;
        padding: 0 2px;
    }

    .vocab-tooltip .tooltip-text {
        visibility: hidden;
        width: max-content;
        max-width: 220px;
        background-color: #1e293b;
        color: #ffffff;
        text-align: center;
        border-radius: 6px;
        padding: 6px 10px;
        position: absolute;
        z-index: 10;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.2s ease-in-out;
        font-size: 14px;
        font-weight: normal;
        line-height: 1.4;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.15);
    }

    .vocab-tooltip .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #1e293b transparent transparent transparent;
    }

    .vocab-tooltip:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    </style>
""", unsafe_allow_html=True)

# --- 영어 지문 줄바꿈 자동 정돈 및 툴팁 태그 파싱 함수 ---
def clean_passage_text(text):
    if not text:
        return ""
    text = re.sub(r'\n\s*\n', ' [[PARAGRAPH]] ', text)
    text = re.sub(r'\s*\n\s*', ' ', text)
    text = text.replace(' [[PARAGRAPH]] ', '\n\n')
    text = re.sub(r' +', ' ', text)
    return text.strip()

def render_passage_with_tooltips(passage_text):
    if not passage_text:
        return ""
    
    formatted = passage_text.replace('\n', '<br>')
    pattern = r'\[\[(.*?)\:(.*?)\]\]'
    def replace_with_tooltip(match):
        word = match.group(1).strip()
        meaning = match.group(2).strip()
        return f'<span class="vocab-tooltip">{word}<span class="tooltip-text">{meaning}</span></span>'
    
    return re.sub(pattern, replace_with_tooltip, formatted)

# --- API 키 및 비밀번호 확인 ---
api_key = st.secrets.get("GEMINI_API_KEY")
teacher_password = st.secrets.get("TEACHER_PASSWORD", "rnswltk1!")
github_token = st.secrets.get("GITHUB_TOKEN")
github_repo_name = st.secrets.get("GITHUB_REPO")

if not api_key:
    st.error("Google Gemini API 키가 설정되지 않았습니다. Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

DATA_FILE = "problem_bank.json"
VOCAB_FILE = "vocabulary.json"
SUBMISSION_FILE = "submissions.json"

# --- 기본 데이터 생성 ---
def get_default_bank():
    default_bank = {}
    for i in range(1, 36):
        default_bank[i] = {
            "title": f"지문 {i}: (제목을 입력하세요)",
            "q1": "1. 지문의 핵심 키워드",
            "q2": "2. 주제 한 문장 요약",
            "q3": "3. 글의 흐름 세 문장 요약",
            "passage": f"여기에 {i}번 영어 지문을 입력하세요. [[crucial:중요한]] 표시는 단어 툴팁 예시입니다.",
            "key_points": ""
        }
    return default_bank

def get_default_vocab_dict():
    vocab_dict = {}
    for i in range(1, 36):
        vocab_dict[i] = [
            {"word": "crucial", "meaning": "중요한, 결정적인"},
            {"word": "perspective", "meaning": "관점, 시각"},
            {"word": "emphasize", "meaning": "강조하다"}
        ]
    return vocab_dict

# --- 문제 및 단어 데이터 불러오기/저장 ---
def load_problem_bank():
    default_bank = get_default_bank()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                parsed_data = {}
                for k, v in data.items():
                    key_num = int(k)
                    parsed_data[key_num] = {
                        "title": v.get("title", f"지문 {key_num}"),
                        "q1": v.get("q1", "1. 지문의 핵심 키워드"),
                        "q2": v.get("q2", "2. 주제 한 문장 요약"),
                        "q3": v.get("q3", "3. 글의 흐름 세 문장 요약"),
                        "passage": v.get("passage", f"여기에 {key_num}번 지문을 입력하세요."),
                        "key_points": v.get("key_points", "")
                    }
                for i in range(1, 36):
                    if i not in parsed_data:
                        parsed_data[i] = default_bank[i]
                return parsed_data
        except Exception:
            pass
    return default_bank

def load_vocab_dict():
    default_vocab = get_default_vocab_dict()
    if os.path.exists(VOCAB_FILE):
        try:
            with open(VOCAB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                parsed_vocab = {}
                for k, v in data.items():
                    parsed_vocab[int(k)] = v
                for i in range(1, 36):
                    if i not in parsed_vocab:
                        parsed_vocab[i] = default_vocab[i]
                return parsed_vocab
        except Exception:
            pass
    return default_vocab

def save_vocab_dict(vocab_dict):
    json_str = json.dumps(vocab_dict, ensure_ascii=False, indent=2)
    with open(VOCAB_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

    if HAS_GITHUB and github_token and github_repo_name:
        try:
            g = Github(github_token)
            repo = g.get_repo(github_repo_name.strip())
            try:
                contents = repo.get_contents(VOCAB_FILE)
                repo.update_file(
                    path=VOCAB_FILE,
                    message=f"Update vocabulary.json via Web Editor ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                    content=json_str,
                    sha=contents.sha
                )
            except Exception:
                repo.create_file(
                    path=VOCAB_FILE,
                    message=f"Create vocabulary.json via Web Editor ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                    content=json_str
                )
        except Exception:
            pass

def save_problem_bank(data):
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

    if HAS_GITHUB and github_token and github_repo_name:
        try:
            g = Github(github_token)
            repo = g.get_repo(github_repo_name.strip())
            try:
                contents = repo.get_contents(DATA_FILE)
                repo.update_file(
                    path=DATA_FILE,
                    message=f"Update problem_bank.json via Web Editor ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                    content=json_str,
                    sha=contents.sha
                )
            except Exception:
                repo.create_file(
                    path=DATA_FILE,
                    message=f"Create problem_bank.json via Web Editor ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                    content=json_str
                )
            return True, "✅ GitHub 저장소에 자동 저장 커밋이 완료되었습니다!"
        except Exception as e:
            return False, f"❌ GitHub 저장 오류: {e}"
    return True, "로컬 세션에 저장되었습니다."

# --- 학생 제출 데이터 불러오기/저장 (20분 자동 삭제) ---
def load_submissions():
    if os.path.exists(SUBMISSION_FILE):
        try:
            with open(SUBMISSION_FILE, "r", encoding="utf-8") as f:
                submissions = json.load(f)
            now = datetime.now()
            valid_submissions = []
            for sub in submissions:
                sub_time = datetime.strptime(sub["timestamp"], "%Y-%m-%d %H:%M:%S")
                if now - sub_time <= timedelta(minutes=20):
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

# 세션 데이터 초기화
if "PROBLEM_BANK" not in st.session_state or not st.session_state["PROBLEM_BANK"]:
    st.session_state["PROBLEM_BANK"] = load_problem_bank()

if "VOCAB_DICT" not in st.session_state or not st.session_state["VOCAB_DICT"]:
    st.session_state["VOCAB_DICT"] = load_vocab_dict()

if "latest_feedback" not in st.session_state:
    st.session_state["latest_feedback"] = None

if "ai_hints" not in st.session_state:
    st.session_state["ai_hints"] = {}

if "recent_summary" not in st.session_state:
    st.session_state["recent_summary"] = None

# --- 사이드바: 교사 제어판 ---
with st.sidebar:
    st.header("🔒 [교사용] 관리자 제어판")
    input_pwd = st.text_input("교사 비밀번호 입력", type="password")
    
    is_teacher = (input_pwd == teacher_password) if teacher_password else False
    
    if is_teacher:
        st.success("🔓 교사 인증 완료")
    else:
        st.caption("비밀번호를 입력하면 교사 전용 관리 화면이 열립니다.")

# --- 메인 화면 ---
st.title("📖 ENGLISH READING AI ASSISTANT")
st.write("학번과 이름을 입력하고 단어 테스트 및 지문 문제 풀이를 진행하세요.")

col_student, col_select = st.columns([1, 2])
with col_student:
    student_name = st.text_input("👤 학생 이름 (예: 10101 홍길동)", placeholder="학번과 이름을 입력하세요")

options_map = {}
for i in range(1, 36):
    prob = st.session_state['PROBLEM_BANK'].get(i, {})
    title = prob.get('title', f"지문 {i}")
    options_map[f"{title}"] = i

with col_select:
    selected_option_label = st.selectbox(
        "📌 풀고 싶은 지문을 선택하세요:",
        list(options_map.keys())
    )

selected_id = options_map[selected_option_label]
selected_problem = st.session_state["PROBLEM_BANK"][selected_id]
current_vocab_list = st.session_state["VOCAB_DICT"].get(selected_id, [])

# --- 콜백 함수 정의 ---
def clean_passage_callback(pass_key, sel_id):
    current_txt = st.session_state.get(pass_key, "")
    cleaned_p = clean_passage_text(current_txt)
    st.session_state[pass_key] = cleaned_p
    st.session_state["PROBLEM_BANK"][sel_id]["passage"] = cleaned_p

def generate_vocab_tags_callback(pass_key, sel_id):
    current_txt = st.session_state.get(pass_key, "")
    clean_target_passage = re.sub(r'\[\[(.*?)\:(.*?)\]\]', r'\1', current_txt)
    
    tag_prompt = (
        "당신은 대한민국 대학수학능력시험 및 EBS 수능특강 영어 출제 전문위원입니다.\n\n"
        "[CRITICAL RULE: DO NOT ALTER ORIGINAL WORDS]\n"
        "1. **절대로 원문의 단어를 다른 유의어나 고급 어휘로 바꾸거나(paraphrase) 문장을 재작성하지 마세요.** (예: bad -> detrimental 변경 절대 금지)\n"
        "2. 원본 지문에 존재하는 단어 단 1글자도 변경하지 말고, **지문 원문에 이미 존재하는 어휘 중** 고2~고3 수능 난이도 수준의 어휘/숙어 3~5개만 선택하세요.\n"
        "3. 선택한 단어의 원본 텍스트 그대로 `[[원본영단어:문맥에 맞는 한글뜻]]` 형태의 태그만 입히세요.\n"
        "4. 중등~고1 수준 기본 단어(know, make, think, show, bad 등)는 태그 대상에서 제외하세요.\n"
        "5. 다른 인사말이나 마크다운 없이 오직 태그만 부착된 원본 지문 전체를 출력하세요.\n\n"
        f"[영어 지문]\n{clean_target_passage}"
    )
    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        res_tagged = model.generate_content(tag_prompt)
        tagged_text = res_tagged.text.strip()
        st.session_state[pass_key] = tagged_text
        st.session_state["PROBLEM_BANK"][sel_id]["passage"] = tagged_text
    except Exception as e:
        st.error(f"AI 단어 태그 생성 오류: {e}")

# --- 교사 전용 관리 제어판 ---
if is_teacher:
    with st.sidebar:
        st.markdown("---")
        
        # 1. 학생 답안 조회 및 최근 5분 요약 기능
        with st.expander("📊 실시간 학생 답안 조회 (최근 20분)", expanded=True):
            if st.button("🔄 제출 내역 새로고침", use_container_width=True):
                st.rerun()
                
            submissions_data = load_submissions()
            
            now = datetime.strptime(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
            recent_5min_subs = []
            for sub in submissions_data:
                sub_time = datetime.strptime(sub["timestamp"], "%Y-%m-%d %H:%M:%S")
                if now - sub_time <= timedelta(minutes=5):
                    recent_5min_subs.append(sub)

            st.markdown("---")
            if st.button("⚡ 최근 5분 학생 오답 패턴 요약 분석", type="primary", use_container_width=True):
                if not recent_5min_subs:
                    st.session_state["recent_summary"] = "⚠️ 최근 5분 이내에 제출된 학생 답안이 없습니다."
                else:
                    with st.spinner("최근 5분간 제출된 답안 분석 중..."):
                        sub_text_block = ""
                        for idx, s in enumerate(recent_5min_subs, 1):
                            sub_text_block += (
                                f"[학생 {idx}: {s['student']}]\n"
                                f"- 키워드 답안: {s['ans1']}\n"
                                f"- 주제 답안: {s['ans2']}\n"
                                f"- 흐름 답안: {s['ans3']}\n"
                                f"- AI 피드백 내용 요약: {s['feedback'][:150]}...\n\n"
                            )

                        summary_prompt = (
                            "당신은 베테랑 영어 교사의 수업 보조 AI 분석가입니다.\n"
                            "최근 5분 동안 학생들이 제출한 답안과 AI 피드백 요약본을 바탕으로, "
                            "선생님이 지금 교실에서 바로 설명해 주셔야 할 가이드라인을 아주 간결하게 작성해 주세요.\n\n"
                            f"[지문 제목]: {selected_problem['title']}\n"
                            f"[최근 5분간 작성된 학생 답안 모음]\n{sub_text_block}\n"
                            "[출력 형식 규칙]\n"
                            "1. ❓ **학생들이 주로 헷갈려하는 부분** (2문장 이내)\n"
                            "2. 💡 **교사가 지금 중점적으로 설명해야 할 포인트** (2문장 이내)"
                        )
                        try:
                            model = genai.GenerativeModel('gemini-3.1-flash-lite')
                            res = model.generate_content(summary_prompt)
                            st.session_state["recent_summary"] = res.text
                        except Exception as e:
                            st.session_state["recent_summary"] = f"분석 중 오류 발생: {e}"

            if st.session_state.get("recent_summary"):
                st.info(f"### 🎯 최근 5분 실시간 오답 분석\n{st.session_state['recent_summary']}")

            st.markdown("---")
            if not submissions_data:
                st.info("최근 20분 이내에 제출된 학생 답안이 없습니다.")
            else:
                sorted_subs = sorted(submissions_data, key=lambda x: x.get("timestamp", ""), reverse=True)
                sub_labels = [f"{sub['student']} - {sub['problem_title']} ({sub['timestamp'].split()[1]})" for sub in sorted_subs]
                
                selected_sub_label = st.selectbox("📋 개별 제출 내역 상세 선택", sub_labels)
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

        # 2. 지문 및 문제 수정
        with st.expander(f"⚙️ {selected_id}번 지문 및 문제 수정", expanded=False):
            new_title = st.text_input("문제 이름", value=selected_problem.get("title", ""), key=f"title_{selected_id}")
            q1_text = st.text_input("첫 번째 질문", value=selected_problem.get("q1", "1. 지문의 핵심 키워드"), key=f"q1_{selected_id}")
            q2_text = st.text_input("두 번째 질문", value=selected_problem.get("q2", "2. 주제 한 문장 요약"), key=f"q2_{selected_id}")
            q3_text = st.text_input("세 번째 질문", value=selected_problem.get("q3", "3. 글의 흐름 세 문장 요약"), key=f"q3_{selected_id}")
            
            st.caption("💡 **단어 툴팁 팁**: `[[영단어:한글뜻]]` 형태로 작성하거나 아래 AI 자동 생성 버튼을 누르세요!")
            
            pass_key = f"pass_{selected_id}"
            if pass_key not in st.session_state:
                st.session_state[pass_key] = selected_problem.get("passage", "")
                
            new_passage = st.text_area("영어 지문", height=150, key=pass_key)
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.button(
                    "🧹 줄바꿈 자동 정돈",
                    key=f"clean_btn_{selected_id}",
                    on_click=clean_passage_callback,
                    args=(pass_key, selected_id),
                    use_container_width=True
                )

            with col_b2:
                st.button(
                    "🤖 AI 고난도 단어 툴팁 태그 생성",
                    key=f"auto_vocab_btn_{selected_id}",
                    on_click=generate_vocab_tags_callback,
                    args=(pass_key, selected_id),
                    use_container_width=True
                )

            new_key_points = st.text_area("추가 지시사항 / 채점 주의사항 (선택사항)", height=80, value=selected_problem.get("key_points", ""), key=f"key_{selected_id}")

            if st.button("💾 지문 변경사항 저장", type="primary"):
                st.session_state["PROBLEM_BANK"][selected_id]["title"] = new_title
                st.session_state["PROBLEM_BANK"][selected_id]["q1"] = q1_text
                st.session_state["PROBLEM_BANK"][selected_id]["q2"] = q2_text
                st.session_state["PROBLEM_BANK"][selected_id]["q3"] = q3_text
                st.session_state["PROBLEM_BANK"][selected_id]["passage"] = st.session_state[pass_key]
                st.session_state["PROBLEM_BANK"][selected_id]["key_points"] = new_key_points
                
                success, msg = save_problem_bank(st.session_state["PROBLEM_BANK"])
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
                st.rerun()

        # 3. 지문별 수업 전 단어 테스트 관리
        with st.expander(f"🔤 [{selected_id}번 지문] 단어 테스트 관리", expanded=False):
            current_vocab_str = "\n".join([f"{item['word']} : {item['meaning']}" for item in current_vocab_list])
            new_vocab_raw = st.text_area("단어 : 뜻 (한 줄에 하나씩 작성)", value=current_vocab_str, height=180, key=f"v_edit_{selected_id}", help="예시:\ncrucial : 중요한\nperspective : 관점")
            
            if st.button(f"💾 {selected_id}번 지문 단어 목록 저장", type="primary"):
                new_vocab_list = []
                for line in new_vocab_raw.strip().split("\n"):
                    if ":" in line:
                        w, m = line.split(":", 1)
                        new_vocab_list.append({"word": w.strip(), "meaning": m.strip()})
                    elif line.strip():
                        new_vocab_list.append({"word": line.strip(), "meaning": ""})
                
                st.session_state["VOCAB_DICT"][selected_id] = new_vocab_list
                save_vocab_dict(st.session_state["VOCAB_DICT"])
                st.success(f"{selected_id}번 지문의 단어 테스트 목록이 저장되었습니다!")
                st.rerun()

# --- 학생용: 1. 선택된 지문 전용 단어 테스트 영역 ---
st.markdown("---")
with st.expander(f"📝 [수업 전 3분] {selected_id}번 지문 핵심 영단어 테스트", expanded=True):
    if not current_vocab_list:
        st.info("등록된 단어가 없습니다.")
    else:
        st.caption("지문을 읽기 전에 아래 영단어/표현의 뜻을 한글로 작성해 보세요!")
        
        vocab_inputs = {}
        cols = st.columns(min(len(current_vocab_list), 3) or 1)
        
        for idx, item in enumerate(current_vocab_list):
            col_target = cols[idx % len(cols)]
            with col_target:
                vocab_inputs[item['word']] = st.text_input(f"📌 {item['word']}", key=f"vocab_{selected_id}_{idx}", placeholder="뜻을 입력하세요")
                
        if st.button("✅ 단어 답안 정답 확인"):
            st.markdown("##### 🎯 단어 테스트 결과 및 정답")
            for idx, item in enumerate(current_vocab_list):
                user_m = vocab_inputs.get(item['word'], '').strip()
                correct_m = item.get('meaning', '').strip()
                
                if user_m:
                    st.write(f"- **{item['word']}**: 작성한 뜻 (`{user_m}`) ➔ 정답/모범뜻: **{correct_m}**")
                else:
                    st.write(f"- **{item['word']}**: ⚠️ 미작성 ➔ 정답/모범뜻: **{correct_m}**")

# --- 학생용: 2. 영어 지문 및 문제 영역 ---
st.markdown("---")
st.subheader(f"📝 {selected_problem['title']}")

# 툴팁 HTML이 포함된 지문 상자 출력
html_passage = render_passage_with_tooltips(selected_problem['passage'])
st.markdown(f'<div class="passage-box">{html_passage}</div>', unsafe_allow_html=True)

# 💡 간결한 AI 도우미 콜업 버튼
col_hint_btn, _ = st.columns([1, 2])
with col_hint_btn:
    if st.button("💡 너무 어려워요! AI 도우미 콜업", key=f"hint_btn_{selected_id}"):
        with st.spinner("AI 도우미 분석 중..."):
            clean_prompt_passage = re.sub(r'\[\[(.*?)\:(.*?)\]\]', r'\1', selected_problem['passage'])
            hint_prompt = (
                "당신은 고등학교 영어 교사입니다.\n"
                "학생이 지문을 읽고 스스로 생각할 수 있도록 돕는 힌트를 작성해 주세요.\n"
                "불필요한 인사말이나 길고 장황한 설명 없이, 오직 아래 지정된 서식대로만 간결하게 작성하세요.\n\n"
                f"[영어 지문]\n{clean_prompt_passage}\n\n"
                "[출력 서식 규칙 (반드시 이 규칙대로만 작성하세요)]\n"
                "첫 줄: AI 도우미 등장!\n\n"
                "🔍 **주제 추론 단서 문장**:\n"
                "- (지문의 주제를 직접 알려주지 말고, 주제를 추론할 수 있는 힌트가 되는 핵심 원문 한 문장을 영어로 인용하고 간단한 힌트 한 줄 덧붙이기)\n\n"
                "📌 **주의 깊게 봐야 할 문장 파트**:\n"
                "- (글의 논지 전환, 대조, 또는 핵심 인과관계가 드러나는 문장 영역이나 구문을 짚어주고 어떤 점에 집중해서 읽어야 할지 설명)"
            )
            try:
                model = genai.GenerativeModel('gemini-3.1-flash-lite')
                hint_response = model.generate_content(hint_prompt)
                st.session_state["ai_hints"][selected_id] = hint_response.text
            except Exception as e:
                st.error(f"힌트를 불러오는 중 오류가 발생했습니다: {e}")

# 💡 생성된 힌트 출력 상자
if selected_id in st.session_state["ai_hints"]:
    st.info(st.session_state['ai_hints'][selected_id])

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

            clean_ai_passage = re.sub(r'\[\[(.*?)\:(.*?)\]\]', r'\1', selected_problem['passage'])
            q1_val = selected_problem.get('q1')
            q2_val = selected_problem.get('q2')
            q3_val = selected_problem.get('q3')

            prompt = (
                "당신은 EBS '수능특강 Light 영어독해연습' 및 대학수학능력시험 영어영역에 매우 정통한 베테랑 고등학교 영어 교사입니다.\n"
                "제시된 지문은 '수능특강 Light 영어독해연습' 수준의 구문이며, 문제 유형은 수능 및 모의고사 출제 유형에 해당합니다.\n\n"
                "제시된 [영어 지문]을 스스로 정확히 분석하여, 학생이 작성한 답안을 기준에 맞추어 전문적이고 친절하게 피드백 해주세요.\n\n"
                f"[영어 지문]\n{clean_ai_passage}\n\n"
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

# --- 세션 상태에 저장된 피드백 출력 ---
if st.session_state.get("latest_feedback"):
    fb_data = st.session_state["latest_feedback"]
    p_title = fb_data.get("problem_title", "")
    p_content = fb_data.get("content", "")
    
    st.markdown("---")
    st.success("피드백 작성이 완료되었습니다!")
    st.markdown(f"### 📊 AI 피드백 결과 ({p_title})")
    st.write(p_content)
    
