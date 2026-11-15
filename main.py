import streamlit as st
import streamlit.components.v1 as components
from google import genai
from PIL import Image
from datetime import datetime
import json
import urllib.parse
import re

st.set_page_config(
    page_title="MediScan AI | Smart Medicine Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #f4f7f9;
    }
    .hero-banner {
        background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.8rem;
        box-shadow: 0 6px 18px rgba(13, 148, 136, 0.18);
    }
    .hero-banner h1 {
        margin: 0;
        font-size: 2.3rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .hero-banner p {
        margin: 0.5rem 0 0 0;
        font-size: 1.05rem;
        opacity: 0.92;
    }
    .med-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 14px;
        border-top: 4px solid #0d9488;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    .buy-box {
        background-color: #f0fdf4;
        border: 1px solid #86efac;
        padding: 1rem 1.2rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
    }
    .buy-links a {
        display: inline-block;
        background-color: #0d9488;
        color: white !important;
        text-decoration: none;
        padding: 7px 15px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        margin-right: 8px;
        margin-top: 8px;
    }
    .buy-links a:hover {
        opacity: 0.9;
    }
    .wa-btn {
        display: inline-block;
        background-color: #25D366;
        color: white !important;
        text-decoration: none;
        padding: 10px 18px;
        border-radius: 10px;
        font-size: 0.98rem;
        font-weight: 700;
        text-align: center;
        width: 100%;
        margin-top: 8px;
        box-shadow: 0 3px 10px rgba(37, 211, 102, 0.25);
    }
    .wa-btn:hover {
        opacity: 0.92;
    }
    .reminder-badge {
        background-color: #ecfdf5;
        border: 1px solid #10b981;
        color: #065f46;
        padding: 0.7rem 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    .stButton>button {
        background: linear-gradient(90deg, #0d9488 0%, #0284c7 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

if "report_text" not in st.session_state:
    st.session_state.report_text = ""
if "detected_meds" not in st.session_state:
    st.session_state.detected_meds = []
if "reminders" not in st.session_state:
    st.session_state.reminders = []

FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-3.8-flash"
]

def get_client():
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def generate_with_fallback(client, contents):
    last_error = None
    for model_name in FALLBACK_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = e
            continue
    raise last_error

def parse_report_and_meds(raw_text):
    clean_report = raw_text.strip()
    meds = []

    if "MEDS_LIST:" in raw_text:
        parts = raw_text.split("MEDS_LIST:")
        clean_report = parts[0].strip()
        meds_line = parts[1].strip().splitlines()[0]
        meds = [m.strip(" -*•`") for m in meds_line.split(",") if m.strip(" -*•`")]

    if not meds:
        matches = re.findall(r"(?:^|\n)\s*(?:#+\s*|\*\*)?\d+\.\s*(?:\*\*)?([A-Za-z0-9\s\-\+\./\(\)]+?)(?:\*\*|\n|$)", clean_report)
        for m in matches:
            cleaned = m.strip(" :-*")
            if 2 < len(cleaned) < 55 and not any(skip in cleaned.lower() for skip in ["summary", "advice", "complaint", "finding", "test", "consultation", "follow"]):
                meds.append(cleaned)

    seen = set()
    unique_meds = []
    for m in meds:
        key = m.lower()
        if key not in seen:
            seen.add(key)
            unique_meds.append(m)

    return clean_report, unique_meds[:10]

with st.sidebar:
    st.markdown("## 🏥 MediScan AI")
    st.caption("AI-Powered Prescription & Medicine Analyzer")
    st.divider()
    language = st.selectbox("🌐 Output Language", ["Both (English + বাংলা)", "English", "Bengali (বাংলা)"])
    st.divider()
    st.markdown("### 📌 All Features")
    st.markdown("""
    - **Scan & Camera:** Upload or snap prescription live.
    - **Generic Alternatives:** Affordable Jan Aushadhi / generic options.
    - **Price & Buy Links:** Estimated MRP (₹) + 1mg, PharmEasy & Apollo links.
    - **Voice Reader & WhatsApp:** Listen to report & share in 1 click.
    - **Search, Safety & Reminder:** Drug check & browser dose alerts.
    """)
    st.divider()
    st.warning("⚠️ **Medical Disclaimer:** Prices & generic suggestions are informational. Consult a doctor or pharmacist before substituting medicines.")

st.markdown("""
    <div class="hero-banner">
        <h1>💊 MediScan AI</h1>
        <p>Complete Smart Health Assistant — Scan, Generic Alternatives, Voice Reader, Buy Online & Reminders</p>
    </div>
""", unsafe_allow_html=True)

left_col, right_col = st.columns([1, 1.25], gap="large")

with left_col:
    tab1, tab2, tab3, tab4 = st.tabs(["📷 Scan", "⌨️ Search", "⚠️ Safety", "⏰ Reminder"])

    with tab1:
        st.markdown("### 📄 Scan Prescription")
        input_mode = st.radio("Choose Input Method:", ["📁 Upload Image", "📸 Use Live Camera"], horizontal=True)
        
        image_to_analyze = None
        if input_mode == "📁 Upload Image":
            uploaded_file = st.file_uploader("Choose prescription (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])
            if uploaded_file is not None:
                image_to_analyze = Image.open(uploaded_file)
                st.image(image_to_analyze, caption="Uploaded Prescription", use_container_width=True)
        else:
            camera_photo = st.camera_input("Take a clear photo of your prescription")
            if camera_photo is not None:
                image_to_analyze = Image.open(camera_photo)

        if image_to_analyze is not None:
            if st.button("🔍 Analyze Prescription"):
                client = get_client()
                if not client:
                    st.error("⚠️ Server API Key not configured yet.")
                else:
                    with st.spinner("Reading handwriting, finding generic alternatives & preparing buy links..."):
                        try:
                            prompt = f"""
                            You are a helpful medical assistant in India. Carefully read this doctor's prescription image and extract all medicines listed.
                            Provide the response in {language}.
                            Number each medicine clearly like:
                            ### 1. Medicine Name & Strength
                            - **Composition / উপাদান**
                            - **Estimated Price (MRP in ₹)** (realistic approximate strip/bottle price range in India)
                            - **Affordable Generic Alternative (Jan Aushadhi / সাশ্রয়ী বিকল্প)** (mention exact generic salt/molecule name and approximate lower Jan Aushadhi / generic price in ₹)
                            - **Purpose / কাজের বিবরণ**
                            - **Dosage & Timing / খাওয়ার নিয়ম** (morning/night, before/after food, duration)
                            - **Key Precautions & Side Effects**

                            MANDATORY FINAL LINE:
                            At the very bottom of your response, write a single line starting with MEDS_LIST: followed by the clean medicine names separated by commas. Example:
                            MEDS_LIST: Tab. Ventidox-M, Tab. HH-Fexo 120
                            """
                            raw_response = generate_with_fallback(client, [image_to_analyze, prompt])
                            clean_rep, meds_found = parse_report_and_meds(raw_response)
                            st.session_state.report_text = clean_rep
                            st.session_state.detected_meds = meds_found
                        except Exception as e:
                            st.error(f"Temporarily busy. Please try again in a few seconds. ({e})")
        else:
            st.info("👆 Upload an image or take a photo to begin.")

    with tab2:
        st.markdown("### 💊 Search Any Medicine")
        med_query = st.text_input("Enter Medicine Name", placeholder="e.g., Paracetamol 650mg, Pantoprazole 40...")
        med_extra = st.text_area("Specific Question (Optional)", placeholder="e.g., Can I take this before breakfast?")
        if st.button("🔎 Get Medicine Info & Generic"):
            client = get_client()
            if not client:
                st.error("⚠️ Server API Key not configured yet.")
            elif not med_query.strip():
                st.warning("Please enter a medicine name first.")
            else:
                with st.spinner(f"Searching details, price & generic alternatives for {med_query}..."):
                    try:
                        prompt = f"""
                        Provide clear, accurate medical information about the medicine: {med_query} (in India).
                        Additional user question: {med_extra}
                        Provide the response in {language} covering:
                        - **Generic Composition & Category**
                        - **Estimated Current Price in India (MRP in ₹)**
                        - **Affordable Generic Alternative (Jan Aushadhi / সাশ্রয়ী বিকল্প)** (exact generic salt & approximate lower price in ₹)
                        - **Primary Uses**
                        - **General Dosage & Food Timing Guidelines**
                        - **Common Side Effects & Safety Warnings**
                        """
                        result_text = generate_with_fallback(client, prompt)
                        st.session_state.report_text = result_text
                        st.session_state.detected_meds = [med_query.strip()]
                    except Exception as e:
                        st.error(f"Temporarily busy. Please try again in a few seconds. ({e})")

    with tab3:
        st.markdown("### ⚠️ Drug Interaction Checker")
        st.caption("Check if taking multiple medicines together is safe.")
        meds_list = st.text_area(
            "Enter 2 or more medicines (separated by commas):",
            placeholder="e.g., Paracetamol 650, Ibuprofen 400, Pantoprazole 40"
        )
        if st.button("🛡️ Check Safety & Interactions"):
            client = get_client()
            if not client:
                st.error("⚠️ Server API Key not configured yet.")
            elif not meds_list.strip():
                st.warning("Please enter at least two medicine names.")
            else:
                with st.spinner("Checking potential drug interactions..."):
                    try:
                        prompt = f"""
                        Analyze potential drug interactions between these medicines: {meds_list}.
                        Provide the response in {language} covering:
                        - **Overall Safety Verdict** (Safe together / Moderate caution / Major interaction)
                        - **How They Interact**
                        - **Recommended Spacing / Timing Tips**
                        - **When to Consult a Doctor Immediately**
                        """
                        result_text = generate_with_fallback(client, prompt)
                        st.session_state.report_text = result_text
                        st.session_state.detected_meds = [m.strip() for m in meds_list.split(",") if m.strip()]
                    except Exception as e:
                        st.error(f"Temporarily busy. Please try again in a few seconds. ({e})")

    with tab4:
        st.markdown("### ⏰ Set Medicine Reminder")
        rem_med = st.text_input("Medicine Name", placeholder="e.g., Tab. Paracetamol 650mg")
        rem_time = st.time_input("Select Dose Time", value=datetime.now().time())
        rem_note = st.text_input("Instruction", placeholder="e.g., After food (খাবারের পর)")

        if st.button("➕ Add Reminder"):
            if rem_med.strip():
                time_str = rem_time.strftime("%H:%M")
                st.session_state.reminders.append({
                    "medicine": rem_med.strip(),
                    "time": time_str,
                    "note": rem_note.strip() or "Take as prescribed"
                })
                st.success(f"✅ Reminder set for {rem_med} at {time_str}")
            else:
                st.warning("Please enter a medicine name.")

        if st.session_state.reminders:
            st.markdown("#### 📋 Active Reminders")
            for r in st.session_state.reminders:
                st.markdown(
                    f'<div class="reminder-badge">💊 <b>{r["medicine"]}</b> — 🕒 <b>{r["time"]}</b> ({r["note"]})</div>',
                    unsafe_allow_html=True
                )
            if st.button("🗑️ Clear All Reminders"):
                st.session_state.reminders = []
                st.rerun()

reminders_json = json.dumps(st.session_state.reminders)
components.html(f"""
    <div style="font-family: sans-serif; padding: 10px 14px; background: #e0f2fe; border-radius: 10px; border: 1px solid #38bdf8; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
        <span id="notif-status" style="font-size: 14px; color: #0369a1; font-weight: 600;">🔔 Enable browser alerts for medicine reminders</span>
        <button onclick="requestNotifPermission()" style="background: #0284c7; color: white; border: none; padding: 7px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; white-space: nowrap;">
            Allow Notifications
        </button>
    </div>

    <script>
    const reminders = {reminders_json};
    let notifiedKeys = new Set();

    function updateStatus() {{
        const statusEl = document.getElementById("notif-status");
        if (!("Notification" in window)) {{
            statusEl.innerText = "⚠️ Browser does not support notifications.";
        }} else if (Notification.permission === "granted") {{
            statusEl.innerText = "✅ Notifications Allowed! Keep this tab open for dose alerts.";
        }} else if (Notification.permission === "denied") {{
            statusEl.innerText = "❌ Notifications blocked. Please allow from browser site settings.";
        }}
    }}

    function requestNotifPermission() {{
        if ("Notification" in window) {{
            Notification.requestPermission().then(permission => {{
                updateStatus();
                if (permission === "granted") {{
                    new Notification("MediScan AI 💊", {{
                        body: "Medicine notifications are now active!"
                    }});
                }}
            }});
        }}
    }}

    function playBeep() {{
        try {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            osc.type = "sine";
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.5);
        }} catch(e) {{}}
    }}

    setInterval(() => {{
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, '0');
        const mm = String(now.getMinutes()).padStart(2, '0');
        const currentTime = hh + ":" + mm;
        const todayKey = now.toDateString() + "_" + currentTime;

        reminders.forEach(item => {{
            const uniqueKey = todayKey + "_" + item.medicine;
            if (item.time === currentTime && !notifiedKeys.has(uniqueKey)) {{
                notifiedKeys.add(uniqueKey);
                playBeep();
                if (Notification.permission === "granted") {{
                    new Notification("💊 Medicine Time: " + item.medicine, {{
                        body: "Time: " + item.time + " | " + item.note
                    }});
                }} else {{
                    alert("💊 Medicine Time: " + item.medicine + " (" + item.note + ")");
                }}
            }}
        }});
    }}, 5000);

    updateStatus();
    </script>
""", height=68)

with right_col:
    st.markdown("### 📋 AI Analysis & Medicine Details")
    if st.session_state.report_text:
        clean_speech = re.sub(r"[#*`_>\-]+", " ", st.session_state.report_text)
        clean_speech = re.sub(r"\s+", " ", clean_speech).strip()
        speech_json = json.dumps(clean_speech)

        components.html(f"""
            <div style="font-family: sans-serif; display: flex; align-items: center; gap: 10px; background: #f8fafc; padding: 10px 14px; border-radius: 12px; border: 1px solid #cbd5e1;">
                <span style="font-size: 14px; font-weight: 600; color: #334155;">🔊 Audio Reader:</span>
                <button onclick="speakReport()" style="background: #0d9488; color: white; border: none; padding: 7px 14px; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    ▶️ Listen Report
                </button>
                <button onclick="stopReport()" style="background: #ef4444; color: white; border: none; padding: 7px 14px; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    ⏹️ Stop
                </button>
            </div>
            <script>
            const textToRead = {speech_json};
            function speakReport() {{
                if ("speechSynthesis" in window) {{
                    window.speechSynthesis.cancel();
                    const utterance = new SpeechSynthesisUtterance(textToRead);
                    utterance.rate = 0.95;
                    window.speechSynthesis.speak(utterance);
                }} else {{
                    alert("Sorry, voice reader is not supported in this browser.");
                }}
            }}
            function stopReport() {{
                if ("speechSynthesis" in window) {{
                    window.speechSynthesis.cancel();
                }}
            }}
            </script>
        """, height=62)

        st.markdown('<div class="med-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.report_text)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.detected_meds:
            st.markdown("#### 🛒 Order Medicines Online (Compare Live Prices)")
            for med in st.session_state.detected_meds:
                encoded = urllib.parse.quote(med)
                url_1mg = f"https://www.1mg.com/search/all?name={encoded}"
                url_pharmeasy = f"https://pharmeasy.in/search/all?name={encoded}"
                url_apollo = f"https://www.apollopharmacy.in/search-medicines/{encoded}"
                buy_html = (
                    '<div class="buy-box">'
                    f'<div style="font-weight: 700; color: #065f46; font-size: 1.05rem;">💊 {med}</div>'
                    '<div class="buy-links">'
                    f'<a href="{url_1mg}" target="_blank">Buy on Tata 1mg ↗</a>'
