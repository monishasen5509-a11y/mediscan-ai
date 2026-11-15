import streamlit as st
import streamlit.components.v1 as components
from google import genai
from PIL import Image
from datetime import datetime
import json
import urllib.parse

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
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.88rem;
        font-weight: 600;
        margin-right: 8px;
        margin-top: 6px;
    }
    .buy-links a:hover {
        background-color: #0f766e;
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

def extract_med_names(client, text_summary):
    try:
        res = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=f"Extract ONLY the medicine names (with strength if available) as a comma-separated list from this text. Do not add any extra words or numbering:\n\n{text_summary}"
        )
        meds = [m.strip() for m in res.text.split(",") if m.strip()]
        return meds[:8]
    except Exception:
        return []

with st.sidebar:
    st.markdown("## 🏥 MediScan AI")
    st.caption("AI-Powered Prescription & Medicine Analyzer")
    st.divider()
    api_key = st.text_input("🔑 Enter Gemini API Key", type="password", placeholder="AIzaSy...")
    language = st.selectbox("🌐 Output Language", ["Both (English + বাংলা)", "English", "Bengali (বাংলা)"])
    st.divider()
    st.markdown("### 📌 All Features")
    st.markdown("""
    - **Scan & Camera:** Upload or snap prescription live.
    - **Price & Buy Links:** Estimated MRP (₹) + 1mg, PharmEasy & Apollo links.
    - **Search & Safety:** Check uses & drug interactions.
    - **Smart Reminder:** Browser alert at dose time.
    """)
    st.divider()
    st.warning("⚠️ **Medical Disclaimer:** Prices are approximate estimates. Always consult a certified doctor.")

st.markdown("""
    <div class="hero-banner">
        <h1>💊 MediScan AI</h1>
        <p>Complete Smart Health Assistant — Scan Prescriptions, Check Prices, Buy Online & Set Reminders</p>
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
                if not api_key:
                    st.error("⚠️ Please enter your Gemini API Key in the left sidebar first!")
                else:
                    with st.spinner("Reading handwriting, estimating prices & preparing buy links..."):
                        try:
                            client = genai.Client(api_key=api_key)
                            prompt = f"""
                            You are a helpful medical assistant in India. Carefully read this doctor's prescription image and extract all medicines listed.
                            Provide the response in {language}.
                            For each medicine, clearly format:
                            - **Medicine Name & Strength**
                            - **Estimated Current Price in India (MRP in ₹)** (give realistic approximate strip/bottle price range in INR)
                            - **Purpose / What it is used for**
                            - **Dosage & Timing** (morning/night, before/after food, duration)
                            - **Key Precautions / Side Effects**
                            """
                            response = client.models.generate_content(
                                model="gemini-3.8-flash",
                                contents=[image_to_analyze, prompt]
                            )
                            st.session_state.report_text = response.text
                            st.session_state.detected_meds = extract_med_names(client, response.text)
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("👆 Upload an image or take a photo to begin.")

    with tab2:
        st.markdown("### 💊 Search Any Medicine")
        med_query = st.text_input("Enter Medicine Name", placeholder="e.g., Paracetamol 650mg, Pantoprazole 40...")
        med_extra = st.text_area("Specific Question (Optional)", placeholder="e.g., Can I take this before breakfast?")
        if st.button("🔎 Get Medicine Info & Price"):
            if not api_key:
                st.error("⚠️ Please enter your Gemini API Key in the left sidebar first!")
            elif not med_query.strip():
                st.warning("Please enter a medicine name first.")
            else:
                with st.spinner(f"Searching details & price for {med_query}..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        prompt = f"""
                        Provide clear, accurate medical information about the medicine: {med_query} (in India).
                        Additional user question: {med_extra}
                        Provide the response in {language} covering:
                        - **Generic Composition & Category**
                        - **Estimated Current Price in India (MRP in ₹)**
                        - **Primary Uses**
                        - **General Dosage & Food Timing Guidelines**
                        - **Common Side Effects & Safety Warnings**
                        """
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=prompt
                        )
                        st.session_state.report_text = response.text
                        st.session_state.detected_meds = [med_query.strip()]
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab3:
        st.markdown("### ⚠️ Drug Interaction Checker")
        st.caption("Check if taking multiple medicines together is safe.")
        meds_list = st.text_area(
            "Enter 2 or more medicines (separated by commas):",
            placeholder="e.g., Paracetamol 650, Ibuprofen 400, Pantoprazole 40"
        )
        if st.button("🛡️ Check Safety & Interactions"):
            if not api_key:
                st.error("⚠️ Please enter your Gemini API Key in the left sidebar first!")
            elif not meds_list.strip():
                st.warning("Please enter at least two medicine names.")
            else:
                with st.spinner("Checking potential drug interactions..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        prompt = f"""
                        Analyze potential drug interactions between these medicines: {meds_list}.
                        Provide the response in {language} covering:
                        - **Overall Safety Verdict** (Safe together / Moderate caution / Major interaction)
                        - **How They Interact**
                        - **Recommended Spacing / Timing Tips**
                        - **When to Consult a Doctor Immediately**
                        """
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=prompt
                        )
                        st.session_state.report_text = response.text
                        st.session_state.detected_meds = [m.strip() for m in meds_list.split(",") if m.strip()]
                    except Exception as e:
                        st.error(f"Error: {e}")

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
                st.markdown(f"""
                    <div class="buy-box">
                        <div style="font-weight: 700; color: #065f46; font-size: 1rem;">💊 {med}</div>
                        <div class="buy-links">
                            <a href="{url_1mg}" target="_blank">Buy on Tata 1mg ↗</a>
                            <a href="{url_pharmeasy}" target="_blank" style="background-color:#0284c7;">Buy on PharmEasy ↗</a>
                            <a href="{url_apollo}" target="_blank" style="background-color:#0f766e;">Buy on Apollo ↗</a>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.download_button(
            label="📥 Download Analysis Report",
            data=st.session_state.report_text,
            file_name="MediScan_AI_Report.txt",
            mime="text/plain"
        )

        st.divider()
        st.markdown("#### 💬 Have a Question About This Report?")
        follow_up = st.text_input("Ask AI anything about these medicines:", placeholder="e.g., Are there any food restrictions with these medicines?")
        if st.button("Ask AI"):
            if not api_key:
                st.error("⚠️ Please enter your Gemini API Key in the sidebar!")
            elif follow_up.strip():
                with st.spinner("Thinking..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        chat_prompt = f"""
                        Based on this medical report:
                        {st.session_state.report_text}
                        
                        Answer the patient's question clearly in {language}:
                        Question: {follow_up}
                        """
                        ans = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=chat_prompt
                        )
                        st.info(ans.text)
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.markdown("""
            <div class="med-card" style="border-top-color: #94a3b8; opacity: 0.85;">
                <h4 style="color:#475569; margin-top:0;">Waiting for Input...</h4>
                <p style="color:#64748b; margin-bottom:0;">
                    Scan a prescription, search a medicine, check drug safety, or set a dose reminder on the left to see prices and buy links here.
                </p>
            </div>
        """, unsafe_allow_html=True)

st.divider()
st.caption("MediScan AI • Built with Python, Streamlit & Gemini AI")