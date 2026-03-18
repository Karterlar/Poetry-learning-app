# ====================== 第一步：禁用浏览器（顶部必填）======================
import os
import signal
import sys
os.environ["BROWSER"] = "none"

# ====================== 第二步：导入依赖（极简无冗余）======================
import streamlit as st
import json
import random
import re
from typing import List, Dict
from gtts import gTTS
from audio_recorder_streamlit import audio_recorder  # 极简录音组件，直接输出WAV
import speech_recognition as sr
from difflib import SequenceMatcher
from io import BytesIO

# ====================== 第三步：Streamlit基础配置 ======================
st.config.set_option("showWelcomeAtStartup", False)
st.runtime.legacy_api_is_enabled = False
st.set_page_config(
    page_title="诗词学习助手",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== 第四步：CSS样式（新增译文赏析样式）======================
st.markdown("""
    <style>
    body { font-family: "Microsoft YaHei", 微软雅黑, sans-serif; }
    .main-title { font-size: 2.5rem; color: #2E4057; text-align: center; margin-bottom: 2rem; }
    .stButton>button { background-color: #4A7BA7; color: white; border-radius: 8px; padding: 0.5rem 1.5rem; font-size: 1rem; }
    .stButton>button:hover { background-color: #3A6B97; }
    .exit-btn>button { background-color: #DC3545 !important; margin-top: 20px; }
    .exit-btn>button:hover { background-color: #C82333 !important; }
    .poem-card { background-color: #F8F9FA; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 1rem 0; }
    .progress-card { background-color: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 10px; padding: 1.5rem; margin: 1rem 0; }
    .success-text { color: #28A745; font-size: 1.1rem; font-weight: bold; }
    .error-text { color: #DC3545; font-size: 1.1rem; font-weight: bold; }
    .status-done { color: #28A745; font-weight: bold; }
    .status-pending { color: #6C757D; font-weight: bold; }
    /* 练习模式新增样式 */
    .stats-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; padding: 1rem; text-align: center; }
    .option-btn { width: 100%; text-align: left; margin: 0.3rem 0; }
    .review-btn>button { background-color: #FFC107 !important; color: #212529 !important; }
    .review-btn>button:hover { background-color: #E0A800 !important; }
    .exit-recite-btn>button { background-color: #6C757D !important; }
    /* 译文赏析样式 */
    .poem-expander { margin-top: 1rem; }
    .poem-expander .streamlit-expanderHeader { font-weight: bold; color: #2E4057; }
    .translation-text { line-height: 1.8; color: #495057; font-size: 1.1rem; }
    .appreciation-text { line-height: 1.8; color: #495057; font-size: 1rem; text-indent: 2em; }
    </style>
""", unsafe_allow_html=True)

# ====================== 第五步：核心函数（新增译文赏析兼容）======================
def load_poems() -> List[Dict]:
    """加载诗词数据，兼容旧版JSON，新增译文与赏析字段默认值"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "poems_v2.json")
    if not os.path.exists(json_path):
        st.error(f"❌ 未找到poems_v2.json，路径：{current_dir}")
        return []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            poems_data = json.load(f)
        # 全兼容处理：给所有诗词补充缺失的字段
        for poem in poems_data:
            if "learned" not in poem:
                poem["learned"] = False
            if "progress" not in poem:
                poem["progress"] = {"listened": False, "read_aloud": False, "recited_correctly": False}
            # 新增：译文与赏析字段，无数据则默认空字符串
            if "translation" not in poem:
                poem["translation"] = "暂无译文"
            if "appreciation" not in poem:
                poem["appreciation"] = "暂无赏析"
        return poems_data
    except Exception as e:
        st.error(f"❌ 加载失败：{str(e)}")
        return []

def save_poems(poems_data: List[Dict]):
    """保存学习进度到JSON"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "poems_v2.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(poems_data, f, ensure_ascii=False, indent=2)

def load_game_data():
    """加载游戏数据（积分、错题本）"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    game_path = os.path.join(current_dir, "game_data.json")
    if not os.path.exists(game_path):
        return {"score": 0, "combo": 0, "wrong_questions": [], "achievements": []}
    try:
        with open(game_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"score": 0, "combo": 0, "wrong_questions": [], "achievements": []}

def save_game_data(game_data: Dict):
    """保存游戏数据"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    game_path = os.path.join(current_dir, "game_data.json")
    with open(game_path, "w", encoding="utf-8") as f:
        json.dump(game_data, f, ensure_ascii=False, indent=2)

def text_to_speech(text: str, poem_title: str) -> str:
    """生成诗词朗读音频，缓存复用"""
    temp_dir = "temp_audio"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    audio_path = os.path.join(temp_dir, f"{poem_title}_朗读.mp3")
    if os.path.exists(audio_path):
        return audio_path
    try:
        tts = gTTS(text=text, lang='zh-cn', slow=False)
        tts.save(audio_path)
        return audio_path
    except Exception as e:
        st.error(f"❌ 生成音频失败：{str(e)}，请检查网络")
        return ""

def speech_to_text(audio_bytes: bytes) -> str:
    """【极简版】直接从WAV字节流识别文字"""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(BytesIO(audio_bytes)) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language="zh-CN")
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        return ""

def clean_text(text: str) -> str:
    """清洗文本，去除标点空格"""
    return re.sub(r'[^\w\s]', '', text).replace(" ", "").replace("\n", "")

def text_similarity(text1: str, text2: str) -> float:
    """计算文本相似度"""
    return SequenceMatcher(None, text1, text2).ratio()

def stop_program():
    """一键退出程序"""
    try:
        os.kill(os.getppid(), signal.SIGTERM)
        os.kill(os.getpid(), signal.SIGTERM)
    except:
        st.stop()
        sys.exit(0)

# ====================== 第六步：练习系统核心逻辑 =======================
def generate_question(poems_data: List[Dict], difficulty: str, grade_filter: str, use_wrong_only: bool, game_data: Dict):
    """生成多样化题目"""
    candidates = poems_data
    if grade_filter != "全部":
        candidates = [p for p in candidates if p.get("grade", "") == grade_filter]
    if use_wrong_only and game_data["wrong_questions"]:
        wrong_titles = [q["title"] for q in game_data["wrong_questions"]]
        candidates = [p for p in candidates if p["title"] in wrong_titles]
    
    if not candidates:
        return None
    
    poem = random.choice(candidates)
    content = poem["content"].replace("。", "，").strip()
    lines = [line.strip() for line in content.split("，") if line.strip()]
    
    if difficulty == "简单":
        question_types = ["mcq_next_line", "mcq_author"]
    elif difficulty == "中等":
        question_types = ["fill_blank", "judge"]
    else:
        question_types = ["fill_char", "sort"]
    
    q_type = random.choice(question_types)
    question_data = {"type": q_type, "poem": poem, "title": poem["title"], "author": poem["author"]}
    
    if q_type == "mcq_next_line" and len(lines) >= 2:
        line_idx = random.randint(0, len(lines)-2)
        correct = lines[line_idx+1]
        all_lines = []
        for p in poems_data:
            c = p["content"].replace("。", "，").strip()
            all_lines.extend([l.strip() for l in c.split("，") if l.strip()])
        wrongs = [l for l in all_lines if l != correct and len(l) == len(correct)]
        options = random.sample(wrongs, min(3, len(wrongs))) + [correct]
        random.shuffle(options)
        question_data.update({
            "question": f"「{lines[line_idx]}」的下一句是？",
            "options": options,
            "correct": correct
        })
    elif q_type == "mcq_author":
        all_authors = list(set([p["author"] for p in poems_data]))
        wrongs = [a for a in all_authors if a != poem["author"]]
        options = random.sample(wrongs, min(3, len(wrongs))) + [poem["author"]]
        random.shuffle(options)
        question_data.update({
            "question": f"《{poem['title']}》的作者是谁？",
            "options": options,
            "correct": poem["author"]
        })
    elif q_type == "fill_blank" and len(lines) >= 2:
        line_idx = random.randint(0, len(lines)-2)
        question_data.update({
            "question": f"请填写下一句：\n\n{lines[line_idx]}，______",
            "correct": lines[line_idx+1]
        })
    elif q_type == "judge":
        is_correct = random.choice([True, False])
        if is_correct:
            statement = f"《{poem['title']}》的作者是{poem['author']}。"
        else:
            other_authors = [p["author"] for p in poems_data if p["author"] != poem["author"]]
            fake_author = random.choice(other_authors) if other_authors else "李白"
            statement = f"《{poem['title']}》的作者是{fake_author}。"
        question_data.update({
            "question": statement,
            "correct": is_correct
        })
    elif q_type == "fill_char" and lines:
        line = random.choice(lines)
        if len(line) >= 3:
            char_idx = random.randint(1, len(line)-2)
            missing_char = line[char_idx]
            display_line = line[:char_idx] + "___" + line[char_idx+1:]
            question_data.update({
                "question": f"请补全诗句：\n\n{display_line}",
                "correct": missing_char
            })
        else:
            line_idx = random.randint(0, len(lines)-2) if len(lines)>=2 else 0
            question_data.update({
                "question": f"请填写下一句：\n\n{lines[line_idx]}，______",
                "correct": lines[line_idx+1] if len(lines)>line_idx+1 else lines[line_idx]
            })
    elif q_type == "sort" and len(lines) >= 4:
        shuffled_lines = lines.copy()
        random.shuffle(shuffled_lines)
        question_data.update({
            "question": f"请将以下句子重新排序，组成《{poem['title']}》：",
            "shuffled": shuffled_lines,
            "correct": lines
        })
    else:
        line_idx = random.randint(0, len(lines)-2) if len(lines)>=2 else 0
        question_data.update({
            "type": "fill_blank",
            "question": f"请填写下一句：\n\n{lines[line_idx]}，______",
            "correct": lines[line_idx+1] if len(lines)>line_idx+1 else lines[line_idx]
        })
    
    return question_data

def check_answer(question_data: Dict, user_answer) -> tuple[bool, str]:
    """检查答案"""
    q_type = question_data["type"]
    correct = question_data["correct"]
    
    if q_type in ["mcq_next_line", "mcq_author"]:
        is_correct = (user_answer == correct)
        msg = "✅ 回答正确！" if is_correct else f"❌ 回答错误！正确答案是：{correct}"
    elif q_type in ["fill_blank", "fill_char"]:
        user_clean = clean_text(str(user_answer))
        correct_clean = clean_text(str(correct))
        is_correct = (user_clean == correct_clean)
        msg = "✅ 回答正确！" if is_correct else f"❌ 回答错误！正确答案是：{correct}"
    elif q_type == "judge":
        is_correct = (user_answer == correct)
        msg = "✅ 判断正确！" if is_correct else f"❌ 判断错误！"
    elif q_type == "sort":
        is_correct = (user_answer == correct)
        msg = "✅ 排序正确！太棒了！" if is_correct else "❌ 排序有误，请再试一次"
    else:
        is_correct = False
        msg = "未知题型"
    
    return is_correct, msg

# ====================== 第七步：页面主逻辑 =======================
def main():
    poems_data = load_poems()
    game_data = load_game_data()
    
    st.markdown('<h1 class="main-title">📜 诗词学习助手</h1>', unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 功能选择")
        app_mode = st.radio("请选择模式", ["学习模式", "练习模式"], index=0)
        
        if app_mode == "练习模式":
            st.header("🎯 练习设置")
            difficulty = st.selectbox("难度", ["简单", "中等", "困难"], index=0, key='diff_sel')
            grade_filter = st.selectbox("学段筛选", ["全部", "小学", "初中", "高中"], index=0, key='grade_sel')
            use_wrong_only = st.checkbox("只练错题本", value=False, key='wrong_sel')
            
            st.session_state['diff'] = difficulty
            st.session_state['grade_f'] = grade_filter
            st.session_state['wrong_only'] = use_wrong_only
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🏆 积分", game_data["score"])
            with col2:
                st.metric("🔥 连击", game_data["combo"])
            
            if st.button("📖 查看错题本"):
                st.session_state["show_wrong"] = True
        
        st.header("🎨 样式配置")
        card_bg = st.color_picker("诗词卡片背景", "#F8F9FA")
        btn_color = st.color_picker("按钮主色", "#4A7BA7")
        font_size = st.slider("字体大小", 14, 20, 16)
        st.markdown(f"""
            <style>
            .poem-card {{ background-color: {card_bg}; }}
            .stButton>button {{ background-color: {btn_color}; }}
            body {{ font-size: {font_size}px; }}
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="exit-btn">', unsafe_allow_html=True)
        if st.button("❌ 退出助手", use_container_width=True):
            stop_program()
        st.markdown('</div>', unsafe_allow_html=True)

    # 学习模式（新增译文与赏析）
    if app_mode == "学习模式":
        st.header("📖 学习模式")
        col1, col2 = st.columns([1, 4])
        with col1:
            grade = st.selectbox("选择学段", ["小学", "初中", "高中"], index=0)
            
            # 学段学习进度条
            filtered_poems = [p for p in poems_data if p["grade"] == grade] if poems_data else []
            if filtered_poems:
                learned_count = sum(1 for p in filtered_poems if p["learned"])
                total_count = len(filtered_poems)
                progress_pct = learned_count / total_count
                
                st.markdown("---")
                st.subheader("📊 学段进度")
                st.progress(progress_pct)
                st.caption(f"已完成：{learned_count} / {total_count} 首")

        filtered_poems = [p for p in poems_data if p["grade"] == grade] if poems_data else []

        with col2:
            if filtered_poems:
                poem_titles = [f"{'✅' if p['learned'] else '❌'} {p['title']} - {p['author']}" for p in filtered_poems]
                
                # 修复切换学段报错问题
                current_titles_only = [p["title"] for p in filtered_poems]
                if "selected_poem_title" not in st.session_state or \
                   st.session_state.selected_poem_title not in current_titles_only:
                    st.session_state.selected_poem_title = filtered_poems[0]["title"]
                
                clean_titles_for_index = [t.split(" - ")[0].replace("✅ ", "").replace("❌ ", "") for t in poem_titles]
                try:
                    target_index = clean_titles_for_index.index(st.session_state.selected_poem_title)
                except ValueError:
                    target_index = 0
                    st.session_state.selected_poem_title = clean_titles_for_index[0]
                
                selected_poem_str = st.selectbox("选择诗词", poem_titles, index=target_index)
                selected_title = selected_poem_str.split(" - ")[0].replace("✅ ", "").replace("❌ ", "")
                st.session_state.selected_poem_title = selected_title
                selected_poem = next(p for p in filtered_poems if p["title"] == selected_title)

                progress_key = f"progress_{selected_title}"
                recite_mode_key = f"recite_mode_{selected_title}"
                if progress_key not in st.session_state:
                    st.session_state[progress_key] = selected_poem["progress"].copy()
                if recite_mode_key not in st.session_state:
                    st.session_state[recite_mode_key] = False
                current_progress = st.session_state[progress_key]

                # 退出背诵模式按钮
                if st.session_state[recite_mode_key]:
                    st.markdown('<div class="exit-recite-btn">', unsafe_allow_html=True)
                    if st.button("↩️ 退出背诵模式"):
                        st.session_state[recite_mode_key] = False
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                # 诗词卡片 + 新增译文与赏析
                if not st.session_state[recite_mode_key]:
                    # 原文展示
                    st.markdown(f"""
                        <div class="poem-card">
                            <h3 style="margin:0 0 0.5rem 0;">{selected_title}</h3>
                            <p style="color:#6C757D; margin:0 0 1rem 0;">—— {selected_poem['author']}</p>
                            <p style="font-size:1.2rem; line-height:1.8;">{selected_poem['content']}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    # 新增：译文与赏析折叠面板
                    st.markdown('<div class="poem-expander">', unsafe_allow_html=True)
                    with st.expander("📖 查看译文与赏析", expanded=False):
                        st.subheader("📝 白话译文")
                        st.markdown(f'<p class="translation-text">{selected_poem["translation"]}</p>', unsafe_allow_html=True)
                        st.divider()
                        st.subheader("💡 诗词赏析")
                        st.markdown(f'<p class="appreciation-text">{selected_poem["appreciation"]}</p>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                else:
                    # 背诵模式：隐藏原文、译文、赏析
                    st.markdown(f"""
                        <div class="poem-card">
                            <h3 style="margin:0 0 0.5rem 0;">{selected_title}</h3>
                            <p style="color:#6C757D; margin:0 0 1rem 0;">—— {selected_poem['author']}</p>
                            <p style="font-size:1.2rem; line-height:1.8; color:#F8F9FA; background:#F8F9FA; padding:1rem; border-radius:8px;">
                                （背诵模式：原文已隐藏）
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

                # 学习进度卡片
                st.markdown('<div class="progress-card">', unsafe_allow_html=True)
                st.subheader("📊 学习进度")

                # 任务1：听
                col_listen_txt, col_listen_btn = st.columns([3, 1])
                with col_listen_txt:
                    status = "✅ 已完成" if current_progress["listened"] else "⏳ 待完成"
                    st.markdown(f"1. 听完一遍诗词朗读：<span class='{'status-done' if current_progress['listened'] else 'status-pending'}'>{status}</span>", unsafe_allow_html=True)
                with col_listen_btn:
                    if not current_progress["listened"]:
                        audio_gen_key = f"audio_gen_{selected_title}"
                        if audio_gen_key not in st.session_state:
                            st.session_state[audio_gen_key] = False
                        if not st.session_state[audio_gen_key]:
                            if st.button("🔊 生成并播放朗读", key="btn_gen"):
                                with st.spinner("正在生成音频..."):
                                    full_text = f"{selected_title}，{selected_poem['author']}，{selected_poem['content']}"
                                    audio_path = text_to_speech(full_text, selected_title)
                                    if audio_path:
                                        st.session_state[f"audio_path_{selected_title}"] = audio_path
                                        st.session_state[audio_gen_key] = True
                                        st.rerun()
                        else:
                            st.audio(st.session_state[f"audio_path_{selected_title}"], format="audio/mp3")
                            st.write("")
                            if st.button("✅ 我已听完", key="btn_listen"):
                                current_progress["listened"] = True
                                st.session_state[progress_key] = current_progress
                                st.rerun()

                # 任务2：读
                col_read_txt, col_read_btn = st.columns([3, 1])
                with col_read_txt:
                    status = "✅ 已完成" if current_progress["read_aloud"] else "⏳ 待完成"
                    st.markdown(f"2. 大声朗读一遍：<span class='{'status-done' if current_progress['read_aloud'] else 'status-pending'}'>{status}</span>", unsafe_allow_html=True)
                with col_read_btn:
                    if not current_progress["read_aloud"]:
                        st.write("点击麦克风开始朗读：")
                        audio_bytes = audio_recorder(
                            text="",
                            recording_color="#DC3545",
                            neutral_color="#4A7BA7",
                            icon_size="2x",
                            key=f"read_recorder_{selected_title}"
                        )
                        if audio_bytes:
                            st.success("✅ 录音完成！")
                            st.audio(audio_bytes, format="audio/wav")
                            if st.button("确认这是我的朗读", key="btn_read"):
                                current_progress["read_aloud"] = True
                                st.session_state[progress_key] = current_progress
                                st.rerun()

                # 任务3：背
                col_recite_txt, col_recite_btn = st.columns([3, 1])
                with col_recite_txt:
                    status = "✅ 已完成" if current_progress["recited_correctly"] else "⏳ 待完成"
                    st.markdown(f"3. 语音背诵并检查正确：<span class='{'status-done' if current_progress['recited_correctly'] else 'status-pending'}'>{status}</span>", unsafe_allow_html=True)
                with col_recite_btn:
                    if not current_progress["recited_correctly"]:
                        if not current_progress["listened"] or not current_progress["read_aloud"]:
                            st.info("请先完成前两项任务")
                        else:
                            if not st.session_state[recite_mode_key]:
                                if st.button("📝 开始背诵", key="btn_start_recite"):
                                    st.session_state[recite_mode_key] = True
                                    st.rerun()
                            else:
                                st.write("点击麦克风开始背诵：")
                                recite_audio = audio_recorder(
                                    text="",
                                    recording_color="#DC3545",
                                    neutral_color="#4A7BA7",
                                    icon_size="2x",
                                    key=f"recite_recorder_{selected_title}"
                                )
                                if recite_audio:
                                    st.success("✅ 录音完成，正在识别...")
                                    with st.spinner("正在识别中..."):
                                        recited_text = speech_to_text(recite_audio)
                                        if recited_text:
                                            original_clean = clean_text(selected_poem["content"])
                                            recited_clean = clean_text(recited_text)
                                            similarity = text_similarity(original_clean, recited_clean)
                                            st.info(f"你背诵的内容：{recited_text}")
                                            st.info(f"与原文相似度：{similarity:.2%}")
                                            if similarity >= 0.8:
                                                st.success("🎉 背诵正确！")
                                                if st.button("确认完成", key="btn_recite_done"):
                                                    current_progress["recited_correctly"] = True
                                                    st.session_state[progress_key] = current_progress
                                                    st.session_state[recite_mode_key] = False
                                                    selected_poem["learned"] = True
                                                    selected_poem["progress"] = current_progress
                                                    save_poems(poems_data)
                                                    st.rerun()
                                            else:
                                                st.error("❌ 背诵不准确，请重新背诵")
                                                if st.button("重新背诵", key="btn_recite_retry"):
                                                    st.rerun()
                                        else:
                                            st.warning("⚠️ 未识别到语音，请在安静环境下重试")
                                            if st.button("重新背诵", key="btn_retry_empty"):
                                                st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

                # 全任务完成判定
                if all(current_progress.values()) and not selected_poem["learned"]:
                    st.balloons()
                    st.success("🎉 恭喜！这首诗已全部学完！")
                    selected_poem["progress"] = current_progress
                    selected_poem["learned"] = True
                    save_poems(poems_data)
                elif all(current_progress.values()):
                    st.info("✅ 这首诗已经学完啦，去练习模式巩固吧！")
                    
                    # 温故知新按钮
                    st.markdown('<div class="review-btn">', unsafe_allow_html=True)
                    if st.button("🔄 温故知新（重新学习）"):
                        selected_poem["learned"] = False
                        selected_poem["progress"] = {"listened": False, "read_aloud": False, "recited_correctly": False}
                        save_poems(poems_data)
                        if progress_key in st.session_state:
                            del st.session_state[progress_key]
                        if recite_mode_key in st.session_state:
                            del st.session_state[recite_mode_key]
                        st.success("已重置学习进度，可以重新开始学习啦！")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            else:
                st.info("ℹ️ 该学段暂无诗词数据")

    # 练习模式
    elif app_mode == "练习模式":
        st.header("📝 练习模式")
        
        if st.session_state.get("show_wrong", False):
            with st.expander("📖 错题本", expanded=True):
                if game_data["wrong_questions"]:
                    for i, q in enumerate(game_data["wrong_questions"]):
                        st.write(f"{i+1}. 《{q['title']}》 - {q.get('question', '')}")
                else:
                    st.write("🎉 暂无错题，太棒了！")
                if st.button("关闭错题本"):
                    st.session_state["show_wrong"] = False
        
        if not poems_data:
            st.warning("ℹ️ 暂无诗词数据")
            return

        if "q_data" not in st.session_state:
            st.session_state.q_data = None
        if "answered" not in st.session_state:
            st.session_state.answered = False
        if "result_msg" not in st.session_state:
            st.session_state.result_msg = ""
        if "is_correct" not in st.session_state:
            st.session_state.is_correct = False

        # 刷新题目按钮
        col_header, col_refresh = st.columns([4, 1])
        with col_header:
            pass
        with col_refresh:
            if st.button("🔄 刷新题目"):
                st.session_state.q_data = None
                st.session_state.answered = False
                st.session_state.result_msg = ""
                st.session_state.is_correct = False
                st.rerun()

        if not st.session_state.q_data:
            with st.spinner("正在生成题目..."):
                diff = st.session_state.get('diff', '简单')
                grade_f = st.session_state.get('grade_f', '全部')
                wrong_o = st.session_state.get('wrong_only', False)
                
                st.session_state.q_data = generate_question(poems_data, diff, grade_f, wrong_o, game_data)
                st.session_state.answered = False
                st.session_state.result_msg = ""
                st.session_state.is_correct = False

        q_data = st.session_state.q_data
        if not q_data:
            st.warning("没有符合条件的题目，请调整筛选条件")
            if st.button("重置条件"):
                st.session_state.q_data = None
                st.rerun()
            return

        st.markdown(f"""
            <div class="poem-card">
                <h4>📚 题目类型：{q_data['type']}</h4>
                <p style="font-size:1.3rem; line-height:1.8; white-space: pre-line;">{q_data['question']}</p>
            </div>
        """, unsafe_allow_html=True)

        q_type = q_data["type"]
        
        if not st.session_state.answered:
            if q_type in ["mcq_next_line", "mcq_author"]:
                for i, opt in enumerate(q_data["options"]):
                    if st.button(f"{chr(65+i)}. {opt}", key=f"opt_{i}", use_container_width=True):
                        is_correct, msg = check_answer(q_data, opt)
                        st.session_state.answered = True
                        st.session_state.is_correct = is_correct
                        st.session_state.result_msg = msg
                        st.rerun()
            elif q_type in ["fill_blank", "fill_char"]:
                user_ans = st.text_input("你的答案：", placeholder="请在这里输入")
                if st.button("提交答案"):
                    if user_ans.strip():
                        is_correct, msg = check_answer(q_data, user_ans)
                        st.session_state.answered = True
                        st.session_state.is_correct = is_correct
                        st.session_state.result_msg = msg
                        st.rerun()
            elif q_type == "judge":
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 正确", use_container_width=True):
                        is_correct, msg = check_answer(q_data, True)
                        st.session_state.answered = True
                        st.session_state.is_correct = is_correct
                        st.session_state.result_msg = msg
                        st.rerun()
                with col2:
                    if st.button("❌ 错误", use_container_width=True):
                        is_correct, msg = check_answer(q_data, False)
                        st.session_state.answered = True
                        st.session_state.is_correct = is_correct
                        st.session_state.result_msg = msg
                        st.rerun()
            elif q_type == "sort":
                st.write("当前顺序（请按正确顺序复制下面的句子，用逗号分隔）：")
                st.write(" | ".join(q_data["shuffled"]))
                user_sort = st.text_input("请输入正确顺序（句子间用逗号分隔）：")
                if st.button("提交排序"):
                    user_list = [s.strip() for s in user_sort.split("，") if s.strip()]
                    is_correct, msg = check_answer(q_data, user_list)
                    st.session_state.answered = True
                    st.session_state.is_correct = is_correct
                    st.session_state.result_msg = msg
                    st.rerun()

        if st.session_state.answered:
            if st.session_state.is_correct:
                st.success(st.session_state.result_msg)
                game_data["combo"] += 1
                base_score = 10
                combo_bonus = min(game_data["combo"], 10) * 2
                game_data["score"] += (base_score + combo_bonus)
                game_data["wrong_questions"] = [q for q in game_data["wrong_questions"] if q["title"] != q_data["title"]]
                if game_data["combo"] >= 5:
                    st.balloons()
                    st.info(f"🔥 连击 x{game_data['combo']}！额外奖励 {combo_bonus} 分！")
            else:
                st.error(st.session_state.result_msg)
                game_data["combo"] = 0
                wrong_entry = {"title": q_data["title"], "question": q_data["question"], "correct": q_data["correct"]}
                if not any(q["title"] == wrong_entry["title"] for q in game_data["wrong_questions"]):
                    game_data["wrong_questions"].append(wrong_entry)
            
            save_game_data(game_data)
            
            if st.button("下一题 ➡️"):
                st.session_state.q_data = None
                st.rerun()

if __name__ == "__main__":
    main()