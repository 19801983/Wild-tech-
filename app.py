import sys, subprocess

# Install system dependencies before anything else
subprocess.run(["apt-get", "update", "-qq"], capture_output=True)
subprocess.run(["apt-get", "install", "-y", "-qq", "libglib2.0-0t64", "libgthread-2.0-0"], capture_output=True)

import streamlit as st
import openai
import os
import tempfile
import re
import io
from contextlib import redirect_stdout, redirect_stderr
from PIL import Image
import moviepy.editor as mp
import cv2

# ---------- Page config ----------
st.set_page_config(page_title="Wild Tech Innovation – Media Generator", layout="wide")
st.title("🚀 Wild Tech Innovation")
st.caption("AI Image & Video Generator – Fast, obedient, do‑anything media agent")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("🔑 API Configuration")
    api_key = st.text_input("DeepSeek API Key", type="password",
                            value=st.secrets.get("DEEPSEEK_API_KEY", ""))
    base_url = "https://api.deepseek.com/v1"
    model = st.selectbox("Model", ["deepseek-chat", "deepseek-reasoner"], index=0)
    if api_key:
        openai.api_key = api_key
        openai.api_base = base_url
        st.success("Connected ✓")
    else:
        st.warning("Paste your API key to start.")

    st.markdown("---")
    st.header("🧩 Mode")
    mode = st.radio("Choose generation type:",
                    ["🎨 Image Generator",
                     "🎥 Video Generator"])

    # ------------------ File upload (optional) ------------------
    st.markdown("---")
    st.header("📁 Upload a file (optional)")
    uploaded_file = st.file_uploader(
        "Upload an image or video to edit. If you don't upload, I'll generate from scratch.",
        type=["png", "jpg", "jpeg", "bmp", "mp4", "mov", "avi", "mkv"]
    )

# ---------- Helper functions ----------
def call_deepseek(messages, temperature=0.1, max_tokens=1500):
    if not api_key:
        st.error("API key missing")
        return None
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def safe_exec(code, globals_dict=None):
    if globals_dict is None:
        globals_dict = {}
    safe_builtins = {
        'print': print, 'len': len, 'range': range, 'int': int, 'float': float,
        'str': str, 'list': list, 'dict': dict, 'bool': bool, 'True': True,
        'False': False, 'None': None, 'abs': abs, 'round': round, 'min': min,
        'max': max, 'sum': sum, 'enumerate': enumerate, 'zip': zip,
        '__import__': __import__, 'Exception': Exception, 'open': open,
        'os': os, 'tempfile': tempfile, 'io': io
    }
    globals_dict['__builtins__'] = safe_builtins
    f = io.StringIO()
    try:
        with redirect_stdout(f), redirect_stderr(f):
            exec(code, globals_dict)
        output = f.getvalue()
        return {"output": output}
    except Exception as e:
        return {"error": str(e) + "\n" + f.getvalue()}

def extract_code(text):
    match = re.search(r"```python(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

IMAGE_PROMPT = (
    "You are a minimalist image generator. "
    "You have access to PIL, OpenCV, and matplotlib. "
    "Write the SHORTEST Python code to produce the image and save to `output_image.png`. "
    "Return ONLY the code block between ```python and ```. No other text."
)

VIDEO_PROMPT = (
    "You are a hyper‑efficient video processing bot. "
    "Write the shortest Python code using moviepy/opencv. "
    "Save output to `output_video.mp4` or `output_audio.mp3` or `output_image.png`. "
    "Return ONLY the code block between ```python and ```. No other text."
)

st.subheader("What do you want to create?")
prompt = st.text_area("Describe the image or video you want:", height=100)

if st.button("Generate"):
    if not prompt.strip():
        st.warning("Please describe what you want.")
    else:
        system_msg = IMAGE_PROMPT if mode == "🎨 Image Generator" else VIDEO_PROMPT
        context = [{"role": "system", "content": system_msg}]

        input_path = None
        if uploaded_file is not None:
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                input_path = tmp.name
            context.append({"role": "system", "content": f"An input file is at: {input_path}"})

        context.append({"role": "user", "content": prompt})

        with st.spinner("Generating..."):
            ai_response = call_deepseek(context, temperature=0.1)

        if ai_response is None:
            st.stop()

        code = extract_code(ai_response)
        if not code:
            st.error("The AI did not return valid code.")
            st.text(ai_response)
            st.stop()

        with st.expander("📝 View generated code"):
            st.code(code, language="python")

        exec_globals = {"input_path": input_path, "os": os, "tempfile": tempfile}
        if mode == "🎨 Image Generator":
            exec_globals.update({
                "Image": Image,
                "cv2": cv2,
                "plt": __import__('matplotlib.pyplot'),
                "np": __import__('numpy') if 'numpy' in code else None,
            })
        else:
            exec_globals.update({"mp": mp, "cv2": cv2})

        result = safe_exec(code, exec_globals)

        if "error" in result:
            st.error(f"Execution error:\n{result['error']}")
        else:
            if result.get("output"):
                st.text(result["output"])
            if mode == "🎨 Image Generator":
                if os.path.exists("output_image.png"):
                    st.image("output_image.png", use_column_width=True)
                    with open("output_image.png", "rb") as f:
                        st.download_button("📥 Download Image", f, "generated_image.png", "image/png")
            else:
                if os.path.exists("output_video.mp4"):
                    st.video("output_video.mp4")
                    with open("output_video.mp4", "rb") as f:
                        st.download_button("📥 Download Video", f, "generated_video.mp4", "video/mp4")
                elif os.path.exists("output_audio.mp3"):
                    st.audio("output_audio.mp3")
                    with open("output_audio.mp3", "rb") as f:
                        st.download_button("📥 Download Audio", f, "generated_audio.mp3", "audio/mpeg")
                elif os.path.exists("output_image.png"):
                    st.image("output_image.png")
                    with open("output_image.png", "rb") as f:
                        st.download_button("📥 Download Image", f, "frame.png", "image/png")
                else:
                    st.warning("No output file found.")

        if input_path:
            try:
                os.unlink(input_path)
            except:
                pass

st.markdown("---")
st.caption("⚡ Wild Tech Innovation – fast, obedient image & video agent. Upload or describe – I'll do the rest")
