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
st.caption("AI Image & Video Generator – Cinematic, Animation, Fast & Obedient")

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

    st.markdown("---")
    st.header("🎬 Style & Duration")
    style = st.selectbox("Style", ["Cinematic", "Animation", "Standard"])
    duration = st.slider("Duration (seconds)", min_value=1, max_value=60, value=5)

    st.markdown("---")
    st.header("📁 Upload Files")
    uploaded_image = st.file_uploader(
        "Upload an image (for image‑to‑video or editing)",
        type=["png", "jpg", "jpeg", "bmp", "webp"],
        key="image_uploader"
    )
    uploaded_video = st.file_uploader(
        "Upload a video to edit",
        type=["mp4", "mov", "avi", "mkv"],
        key="video_uploader"
    )

# ---------- Helper functions ----------
def call_deepseek(messages, temperature=0.1, max_tokens=2000):
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

# ---------- System prompts ----------
IMAGE_PROMPT_TEMPLATE = (
    "You are a minimalist image generator. "
    "The user wants an image in style: {style}. "
    "Write the SHORTEST Python code using PIL, OpenCV, or matplotlib. "
    "If an input image path is in `input_path`, edit that image; otherwise generate from scratch. "
    "Save to `output_image.png`. "
    "Return ONLY ```python code block. No extra text."
)

VIDEO_PROMPT_TEMPLATE = (
    "You are a hyper‑efficient video processing bot. "
    "The user wants a video of duration {duration}s in style: {style}. "
    "They may upload an image (path in `image_path`) or video (path in `video_path`). "
    "If an image is provided, create a video from it using effects (cinematic: Ken Burns zoom/pan, fade, letterbox; animation: motion graphics, smooth transitions). "
    "If a video is provided, edit it: apply the chosen style, trim or loop to exactly {duration}s. "
    "Write the SHORTEST Python code using moviepy (preferred) or opencv. "
    "Save output to `output_video.mp4` (video) or `output_image.png` (image). "
    "Use minimal lines, no comments. Return ONLY ```python code block. No extra text."
)

# ---------- Main UI ----------
st.subheader("Describe what you want")
prompt = st.text_area(
    "Type your request (e.g. 'a sunset over mountains', 'add slow zoom and film grain'):",
    height=100,
    placeholder="Describe the image or video..."
)

if st.button("🚀 Generate"):
    if not prompt.strip():
        st.warning("Please describe what you want.")
    else:
        # Prepare system prompt
        if mode == "🎨 Image Generator":
            system_msg = IMAGE_PROMPT_TEMPLATE.format(style=style)
        else:
            system_msg = VIDEO_PROMPT_TEMPLATE.format(style=style, duration=duration)

        context = [{"role": "system", "content": system_msg}]

        # Handle uploaded files
        image_path = None
        video_path = None

        if uploaded_image is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                tmp.write(uploaded_image.read())
                image_path = tmp.name
            context.append({"role": "system", "content": f"An input image is at: {image_path}"})

        if uploaded_video is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                tmp.write(uploaded_video.read())
                video_path = tmp.name
            context.append({"role": "system", "content": f"An input video is at: {video_path}"})

        # Add user prompt
        context.append({"role": "user", "content": prompt})

        with st.spinner("Wild Tech is creating..."):
            ai_response = call_deepseek(context, temperature=0.1)

        if ai_response is None:
            st.stop()

        code = extract_code(ai_response)
        if not code:
            st.error("The AI did not return valid code. Raw response:")
            st.text(ai_response)
            st.stop()

        # Show generated code
        with st.expander("📝 View generated code"):
            st.code(code, language="python")

        # Prepare execution environment
        exec_globals = {
            "image_path": image_path,
            "video_path": video_path,
            "duration": duration,
            "style": style,
            "os": os,
            "tempfile": tempfile,
        }

        if mode == "🎨 Image Generator":
            exec_globals.update({
                "Image": Image,
                "cv2": cv2,
                "plt": __import__('matplotlib.pyplot'),
                "np": __import__('numpy'),
            })
        else:
            exec_globals.update({
                "mp": mp,
                "cv2": cv2,
            })

        result = safe_exec(code, exec_globals)

        if "error" in result:
            st.error(f"Execution error:\n{result['error']}")
        else:
            if result.get("output"):
                st.text(result["output"])

            # Show & download results
            if mode == "🎨 Image Generator":
                if os.path.exists("output_image.png"):
                    st.image("output_image.png", use_column_width=True)
                    with open("output_image.png", "rb") as f:
                        st.download_button("📥 Download Image", f, "generated_image.png", "image/png")
                else:
                    st.warning("No output_image.png found.")
            else:
                if os.path.exists("output_video.mp4"):
                    st.video("output_video.mp4")
                    with open("output_video.mp4", "rb") as f:
                        st.download_button("📥 Download Video", f, "generated_video.mp4", "video/mp4")
                elif os.path.exists("output_image.png"):
                    st.image("output_image.png", use_column_width=True)
                    with open("output_image.png", "rb") as f:
                        st.download_button("📥 Download Image", f, "frame.png", "image/png")
                else:
                    st.warning("No output file found. Check the generated code.")

        # Clean up temp files
        for path in [image_path, video_path]:
            if path:
                try:
                    os.unlink(path)
                except:
                    pass

st.markdown("---")
st.caption("⚡ Wild Tech Innovation – upload an image, set duration & style, get cinematic/animated videos instantly.")
