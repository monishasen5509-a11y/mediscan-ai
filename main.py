import streamlit as st
import streamlit.components.v1 as components
from google import genai
from PIL import Image
from datetime import datetime
import json, urllib.parse, re

st.set_page_config(page_title="MediScan AI", page_icon="💊", layout="wide")

st.markdown("""
<style>
.stApp {background-color: #f4f7f9;}
.hero {background: linear-gradient(135deg, #0d9488, #0284c7); padding: 1.5rem 2rem; border-radius: 14px; color: white; margin-bottom: 1.5rem;}
.card {background: #fff; padding: 1.3rem; border-radius: 12px; border-top: 4px solid #0d9488; box-shadow: 0 3px 10px rgba(0,0,0,0.05); margin-bottom: 1rem;}
.buy-box {background: #f0fdf4; border: 1px solid #86efac; padding: 0.9rem; border-radius: 10px; margin-bottom: 0.7rem;}
.buy-box a {display: inline-block; background: #0d9488; color: #fff !important; text-decoration: none; padding: 6px 12px; border-radius: 7px; font-size: 0.85rem; font-weight: 600; margin: 5px 6px 0 0;}
.wa-btn {display: block; background: #25D366; color: #fff !important; text-decoration: none; padding: 9px; border-radius: 9px; font-weight: 700; text-align: center; margin-top: 6px;}
.rem-box {background: #ecfdf5; border: 1px solid #10b981; color: #065f46; padding: 0.6rem; border-radius: 8px; margin-bottom: 0.4rem;}
.stButton>button {background: linear-gradient(90deg, #0d9488, #0284c7); color: white; border: none; border-radius: 9px; font-weight: 600; width: 100%;}
</style>
""", unsafe_allow_html=True)

for k, v in [("report_text", ""), ("detected_meds", []), ("reminders", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-3.8-flash"]

def ask_gemini(contents):
    key = st.secrets.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError("API Key missing in Secrets")
    client = genai.Client(api_key=key)
    err = None
    for m in MODELS:
        try:
            res = client.models.generate_content(model=m, contents=contents)
            if res and res.text:
                return res.text
        except Exception as e:
            err = e
    raise err

def parse_output(raw):
    clean = raw.strip()
    meds = []
    if "MEDS_LIST:" in raw:
        p = raw.split("MEDS_LIST:")
        clean = p[0].strip()
        meds = [x.strip(" -*•`") for x in p[1].splitlines()[0].split(",") if x.strip(" -*•`")]
    if not meds:
        found = re.findall(r"(?:^|\n)\s*(?:#+\s*|\*\*)?\d+\.\s*(?:\*\*)?([A-Za-z0-9\s\-\+\./\(\)]+?)(?:\*\*|\n|$)", clean)
        meds = [x.strip(" :-*") for x in found if 2 < len(x.strip()) < 50]
    return clean, list(dict.fromkeys(meds))[:10]

with st.sidebar:
    st.markdown("## 🏥 MediScan AI")
    lang = st.selectbox("🌐 Output Language", ["Both (English + বাংলা)", "English", "Bengali (বাংলা)"])
    st.divider()
    st.info("Scan prescriptions, check generic alternatives, compare pharmacy prices, listen to reports & set dose alerts.")
    st.warning("⚠️ Consult a doctor before substituting medicines.")

st.markdown('<div class="hero"><h1>💊 MediScan AI</h1><p>Smart Prescription Scanner, Generic Finder, Voice Reader & Pharmacy Links</p></div>', unsafe_allow_html=True)

left, right = st.columns([1, 1.25], gap="large")

with left:
    t1, t2, t3, t4 = st.tabs(["📷 Scan", "⌨️ Search", "⚠️ Safety", "⏰ Reminder"])

    with t1:
        mode = st.radio("Input:", ["📁 Upload Image", "📸 Live Camera"], horizontal=True)
        img = None
        if mode == "📁 Upload Image":
            f = st.file_uploader("Upload prescription", type=["png", "jpg", "jpeg"])
            if f:
                img = Image.open(f)
                st.image(img, use_container_width=True)
        else:
            cam = st.camera_input("Take photo")
            if cam:
                img = Image.open(cam)

        if img and st.button("🔍 Analyze Prescription"):
            with st.spinner("Analyzing prescription..."):
                try:
                    p = f"""Read this Indian prescription in {lang}. Format each medicine as:
### 1. Medicine Name & Strength
- **Composition / উপাদান**
- **Estimated Price (MRP ₹)**
- **Affordable Generic Alternative (Jan Aushadhi / সাশ্রয়ী বিকল্প)**
- **Purpose / কাজ**
- **Dosage & Timing / খাওয়ার নিয়ম**
- **Precautions**
End with exact line: MEDS_LIST: Med1, Med2"""
                    rep, m_list = parse_output(ask_gemini([img, p]))
                    st.session_state.report_text = rep
                    st.session_state.detected_meds = m_list
                except Exception as e:
                    st.error(f"Error: {e}")

    with t2:
        q = st.text_input("Medicine Name", placeholder="e.g., Paracetamol 650")
        extra = st.text_input("Question (Optional)", placeholder="e.g., Before or after food?")
        if st.button("🔎 Search Medicine") and q.strip():
            with st.spinner("Searching..."):
                try:
                    p = f"Explain medicine {q} in India ({lang}). Question: {extra}. Include Composition, Estimated MRP (₹), Affordable Jan Aushadhi Generic Alternative, Uses, Dosage & Side Effects."
                    st.session_state.report_text = ask_gemini(p)
                    st.session_state.detected_meds = [q.strip()]
                except Exception as e:
                    st.error(f"Error: {e}")

    with t3:
        mlist = st.text_area("Enter 2+ medicines (comma separated)", placeholder="Paracetamol 650, Ibuprofen 400")
        if st.button("🛡️ Check Interactions") and mlist.strip():
            with st.spinner("Checking safety..."):
                try:
                    p = f"Check drug interactions between: {mlist} in {lang}. Give Safety Verdict, Interaction details & Timing tips."
                    st.session_state.report_text = ask_gemini(p)
                    st.session_state.detected_meds = [x.strip() for x in mlist.split(",") if x.strip()]
                except Exception as e:
                    st.error(f"Error: {e}")

    with t4:
        rmed = st.text_input("Medicine", placeholder="Tab. Paracetamol")
        rtime = st.time_input("Time", value=datetime.now().time())
        rnote = st.text_input("Note", placeholder="After food")
        if st.button("➕ Set Reminder") and rmed.strip():
            st.session_state.reminders.append({"med": rmed.strip(), "time": rtime.strftime("%H:%M"), "note": rnote or "Take dose"})
            st.success("Reminder added!")
        for r in st.session_state.reminders:
            st.markdown(f'<div class="rem-box">💊 <b>{r["med"]}</b> — 🕒 {r["time"]} ({r["note"]})</div>', unsafe_allow_html=True)
        if st.session_state.reminders and st.button("🗑️ Clear Reminders"):
            st.session_state.reminders = []
            st.rerun()

rem_json = json.dumps(st.session_state.reminders)
components.html(f"""
<div style="font-family:sans-serif;padding:8px 12px;background:#e0f2fe;border-radius:8px;display:flex;justify-content:space-between;align-items:center;">
<span id="st" style="font-size:13px;color:#0369a1;font-weight:600;">🔔 Enable Dose Alerts</span>
<button onclick="req()" style="background:#0284c7;color:#fff;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;">Allow</button>
</div>
<script>
const rems = {rem_json}; let done = new Set();
function req(){{ if("Notification" in window) Notification.requestPermission().then(p=>{{if(p==="granted") document.getElementById("st").innerText="✅ Alerts Active";}}); }}
setInterval(()=>{{
  const d=new Date(), t=String(d.getHours()).padStart(2,'0')+":"+String(d.getMinutes()).padStart(2,'0');
  rems.forEach(x=>{{ const k=d.toDateString()+t+x.med; if(x.time===t && !done.has(k)){{ done.add(k); alert("💊 Medicine Time: "+x.med+" ("+x.note+")"); }} }});
}}, 5000);
</script>
""", height=55)

with right:
    st.markdown("### 📋 Analysis & Order Links")
    if st.session_state.report_text:
        speech_txt = json.dumps(re.sub(r"[#*`_>\-]+", " ", st.session_state.report_text))
        components.html(f"""
        <div style="font-family:sans-serif;display:flex;gap:8px;align-items:center;background:#f8fafc;padding:8px 12px;border-radius:8px;border:1px solid #cbd5e1;">
        <b style="font-size:13px;">🔊 Voice Reader:</b>
        <button onclick="speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance({speech_txt}))" style="background:#0d9488;color:#fff;border:none;padding:5px 12px;border-radius:6px;cursor:pointer;">▶️ Listen</button>
        <button onclick="speechSynthesis.cancel()" style="background:#ef4444;color:#fff;border:none;padding:5px 12px;border-radius:6px;cursor:pointer;">⏹️ Stop</button>
        </div>
        """, height=52)

        st.markdown(f'<div class="card">{st.session_state.report_text}</div>', unsafe_allow_html=True)

        if st.session_state.detected_meds:
            st.markdown("#### 🛒 Buy Medicines Online")
            for m in st.session_state.detected_meds:
                q_med = urllib.parse.quote(m)
                st.markdown(f"""<div class="buy-box"><b>💊 {m}</b><br>
                <a href="https://www.1mg.com/search/all?name={q_med}" target="_blank">Tata 1mg ↗</a>
                <a href="https://pharmeasy.in/search/all?name={q_med}" target="_blank" style="background:#0284c7;">PharmEasy ↗</a>
                <a href="https://www.apollopharmacy.in/search-medicines/{q_med}" target="_blank" style="background:#0f766e;">Apollo ↗</a>
                </div>""", unsafe_allow_html=True)

        wa_txt = urllib.parse.quote(f"💊 *MediScan AI Report*\n\n{st.session_state.report_text[:1200]}")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 Download (.txt)", st.session_state.report_text, "MediScan_Report.txt")
        with c2:
            st.markdown(f'<a href="https://api.whatsapp.com/send?text={wa_txt}" target="_blank" class="wa-btn">📲 Share on WhatsApp ↗</a>', unsafe_allow_html=True)

        st.divider()
        fq = st.text_input("💬 Ask a follow-up question:")
        if st.button("Ask AI") and fq.strip():
            with st.spinner("Thinking..."):
                try:
                    st.info(ask_gemini(f"Report:\n{st.session_state.report_text}\n\nAnswer in {lang}: {fq}"))
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.markdown('<div class="card" style="opacity:0.8;"><h4>Waiting for Input...</h4><p>Upload a prescription or search a medicine on the left.</p></div>', unsafe_allow_html=True)
