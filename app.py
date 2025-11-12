from dotenv import load_dotenv
load_dotenv(".env")  # load GEMINI_API_KEY from .env

import os
import re
import streamlit as st
import google.generativeai as genai

# configure gemini with the key we stored
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def rewrite_with_gemini(model_id: str, prompt: str) -> str:
    model = genai.GenerativeModel(model_id)
    resp = model.generate_content(prompt)
    return resp.text


st.set_page_config(page_title="AI Date Message Coach", layout="wide")

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    h1 {
        color: #667eea;
        font-weight: 700;
        text-align: center;
    }
    h2 {
        color: #764ba2;
        font-weight: 600;
    }
    h3 {
        color: #667eea;
    }
    .stButton button {
        border-radius: 8px;
        font-weight: 600;
    }
    .stTextArea textarea {
        border-radius: 8px;
    }
    .stSelectbox {
        border-radius: 8px;
    }
    div[data-testid="stExpander"] {
        background-color: rgba(102, 126, 234, 0.05);
        border-radius: 8px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
</style>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []

if "privacy_mode" not in st.session_state:
    st.session_state.privacy_mode = True

st.title("💬 AI Date Message Coach")
st.caption("Rewrite messages with better tone and clarity using AI")

with st.sidebar:
    st.header("⚙️ Settings")
    
    # FIX: valid model ids
    model_choice = st.selectbox(
        "AI Model",
        ["gemini-2.5-flash", "gemini-2.5-pro"],
        help="Flash is faster, Pro is more nuanced"
    )
    
    system_prompt = st.text_area(
        "System Prompt",
        value="You are an empathetic dating coach. Be concise, kind, and specific. Preserve facts and names. Avoid love bombing and negging.",
        height=120,
        help="Customize how the AI approaches rewriting"
    )
    
    privacy_mode = st.checkbox(
        "🔒 Privacy Mode",
        key="privacy_mode",
        help="Automatically mask emails, phone numbers, and social handles"
    )
    
    st.markdown("---")
    st.subheader("📝 Demo Presets")
    
    demo_messages = {
        "Casual Meetup": {
            "text": "hey wanna hang out sometime maybe if ur free lol",
            "tone": "Confident"
        },
        "First Date": {
            "text": "so i was thinking we could maybe grab coffee or something if you want no pressure though",
            "tone": "Friendly"
        },
        "Follow Up": {
            "text": "had a really good time yesterday!!!! we should definitely do it again soon if you want!!!",
            "tone": "Casual"
        }
    }
    
    for preset_name, preset_data in demo_messages.items():
        if st.button(f"Try: {preset_name}", use_container_width=True):
            st.session_state.input_message = preset_data["text"]
            st.session_state.tone_selector = preset_data["tone"]
            st.rerun()

def sanitize_text(text, privacy_enabled):
    if not privacy_enabled:
        return text
    
    sanitized = text
    sanitized = re.sub(r'\b[\w.%+-]+@[\w.-]+\.\w+\b', '[email]', sanitized)
    sanitized = re.sub(r'\+?\d[\d\s().-]{7,}\d', '[phone]', sanitized)
    sanitized = re.sub(r'@[\w_]+', '@[user]', sanitized)
    return sanitized

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(" Compose")
    
    user_msg = st.text_area("Paste your message", height=150, key="input_message")
    
    char_count = len(user_msg)
    st.caption(f"Character count: {char_count}")
    
    if char_count > 500:
        st.warning("⚠️ Your message is quite long. Consider breaking it into smaller messages for better clarity.")
    
    target_tone = st.selectbox(
        "Desired tone", 
        ["Confident", "Friendly", "Playful", "Casual", "Romantic", "Witty", "Sincere"],
        key="tone_selector"
    )
    
    rewrite_button = st.button("✨ Rewrite", type="primary", use_container_width=True)

with col2:
    st.subheader(" Result")
    
    if rewrite_button and user_msg.strip():
        with st.spinner("Analyzing and rewriting..."):
            try:
                sanitized_msg = sanitize_text(user_msg, privacy_mode)
                
                if privacy_mode and sanitized_msg != user_msg:
                    st.info("🔒 Privacy mode: Sensitive information masked before sending to AI")
                
                prompt = f"""
{system_prompt}

Rewrite the message to sound {target_tone.lower()}, natural, and respectful.
Preserve intent and length where possible.

Please format your response EXACTLY as follows:
**Rewritten Message:**
[your rewritten version here]

**Original Tone:**
[one of: confident, awkward, neutral, shy, overeager, casual]

**Reason for Change:**
[one sentence explanation]

Message:
{sanitized_msg}
"""
                
                max_retries = 3
                retry_count = 0
                last_error = None
                
                while retry_count < max_retries:
                    try:
                        # FIX: use helper with GenerativeModel instead of client.models
                        out = rewrite_with_gemini(model_choice, prompt)
                        
                        st.session_state.history.insert(0, {
                            "original": user_msg,
                            "rewritten": out,
                            "tone": target_tone,
                            "model": model_choice
                        })
                        
                        st.markdown(out)
                        
                        st.markdown("---")
                        st.code(out, language=None)
                        st.caption("📋 Select and copy the text above")
                        
                        break
                        
                    except Exception as e:
                        retry_count += 1
                        last_error = e
                        if retry_count < max_retries:
                            st.warning(f"Retry {retry_count}/{max_retries}...")
                            import time
                            time.sleep(0.4 * (2 ** retry_count))
                        else:
                            raise last_error
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Please check your Google API key and quota. Try again in a moment.")
    elif not user_msg.strip() and rewrite_button:
        st.warning("⚠️ Please enter a message to rewrite.")
    else:
        st.info("👋 Enter your message and click 'Rewrite' to get started, or try a demo preset from the sidebar!")

if st.session_state.history:
    st.markdown("---")
    st.subheader(" Message History")
    st.caption(f"You have {len(st.session_state.history)} rewrite(s) in this session")
    
    for idx, item in enumerate(st.session_state.history):
        with st.expander(f"Rewrite #{idx + 1} - {item['tone']} tone ({item['model']})", expanded=(idx == 0)):
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("**Original:**")
                st.text_area(
                    "Original message",
                    value=item['original'],
                    height=100,
                    key=f"orig_{idx}",
                    disabled=True,
                    label_visibility="collapsed"
                )
            
            with col_b:
                st.markdown("**Rewritten:**")
                st.markdown(item['rewritten'])
    
    if st.button("🗑️ Clear History"):
        st.session_state.history = []
        st.rerun()
