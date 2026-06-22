import streamlit as st
from ultralytics import YOLO
import cv2
import numpy as np
import tempfile, os, time
import streamlit.components.v1 as components
import requests
from dotenv import load_dotenv
from datetime import datetime
import smtplib
from email.message import EmailMessage

# ================= LOAD ENV =================
ENV_PATH = "/home/arman/ecovision_app/.env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

# ================= SESSION STATE =================
defaults = {
    "theme": "dark",
    "run": False,
    "pothole_count": 0,
    "garbage_count": 0,
    "last_alert_time": 0,
    "detect_start_time": None,
    "alert_sent": False,
    "video_alert_sent": False,
    "gps": "",
    "detected_image": None,
    "detected_issue": None,
    "detected_conf": 0.0
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================= PAGE =================
st.set_page_config(page_title="ECOVISION", layout="wide")

# ================= THEME =================
theme_toggle = st.sidebar.toggle("🌙 Dark Mode", value=True)
st.session_state.theme = "dark" if theme_toggle else "light"

if st.session_state.theme == "dark":
    st.markdown("""
    <style>
    .stApp {background:#0E1117;color:white;}
    div[data-testid="stMetric"] {background:#1c1f26;color:white;border-radius:10px;padding:10px;}
    .stTextInput input {background:#1c1f26;color:white;}
    </style>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <style>
    .stApp {background:white;color:black;}
    html, body, [class*="css"] {color:black !important;}

    section[data-testid="stSidebar"] {
        background-color:#f5f5f5 !important;
        color:black !important;
    }

    div[data-testid="stMetric"] {
        background:#ffffff !important;
        color:black !important;
        border:1px solid #ddd;
        border-radius:10px;
        padding:10px;
    }

    .stTextInput input {
        background:#ffffff !important;
        color:black !important;
        border:1px solid #ccc;
    }

    section[data-testid="stFileUploader"] {
        background:#ffffff !important;
        color:black !important;
        border:1px solid #ccc;
        border-radius:10px;
        padding:10px;
    }

    section[data-testid="stFileUploader"] * {
        color:black !important;
    }

    label {color:black !important;}
    button {color:black !important;}
    </style>
    """, unsafe_allow_html=True)

# ================= TITLE =================
st.title("🌿 ECOVISION - Smart Detection System")

# ================= DASHBOARD =================
c1, c2, c3 = st.columns(3)
c1.metric("🚧 Potholes", st.session_state.pothole_count)
c2.metric("🗑 Garbage", st.session_state.garbage_count)
c3.metric("📊 Total", st.session_state.pothole_count + st.session_state.garbage_count)

# ================= GPS =================
def gps_widget():
    components.html("""
    <button onclick="getLocation()" style="padding:8px 15px;background:#4CAF50;color:white;border:none;border-radius:5px;">
    📍 Get My GPS Location</button>
    <p id="gps_status"></p>
    <script>
    function getLocation(){
        navigator.geolocation.getCurrentPosition(pos=>{
            const txt=pos.coords.latitude+","+pos.coords.longitude;
            navigator.clipboard.writeText(txt);
            document.getElementById("gps_status").innerHTML=
            "<span style='color:#00E676'>Copied: </span><span style='color:#FF5252'>"+txt+"</span>";
        });
    }
    </script>
    """, height=120)

# ================= SOUND =================
def play_alert():
    st.markdown("""<audio autoplay>
    <source src="https://www.soundjay.com/buttons/sounds/beep-07.mp3">
    </audio>""", unsafe_allow_html=True)

# ================= TELEGRAM =================
def send_telegram(issue, image, conf, gps):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    emoji = "🗑" if issue.lower() in ["waste","garbage"] else "🚧"
    issue = "Waste" if issue.lower()=="garbage" else issue.capitalize()

    gps = gps if gps else "Not Provided"
    map_link = f"https://maps.google.com/?q={gps}"

    msg = f"""
🚨 <b>ECOVISION ALERT</b> 🚨

{emoji} <b>Issue:</b> {issue}
📊 <b>Confidence:</b> {conf*100:.2f}%

📍 <b>Coordinates:</b> {gps}
🗺 <b>Map:</b> <a href="{map_link}">Open Location</a>

⏰ <b>Time:</b> {datetime.now().strftime('%d-%m-%Y | %H:%M:%S')}
"""

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    cv2.imwrite(tmp.name, image)

    with open(tmp.name, "rb") as photo:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id, "caption": msg, "parse_mode": "HTML"},
            files={"photo": photo}
        )

    os.remove(tmp.name)

# ================= EMAIL =================
def send_email(issue, image, conf, gps):
    sender = os.getenv("ALERT_EMAIL_FROM")
    password = os.getenv("ALERT_EMAIL_PASSWORD")
    receiver = os.getenv("ALERT_EMAIL_TO")

    emoji = "🗑" if issue.lower() in ["waste","garbage"] else "🚧"
    issue = "Waste" if issue.lower()=="garbage" else issue.capitalize()
    gps = gps if gps else "Not Provided"
    map_link = f"https://maps.google.com/?q={gps}"

    html = f"""
    <html><body style="font-family:Arial;background:#ffffff;color:black;padding:20px;">
    <h2 style="color:#FF5252;">🚨 ECOVISION ALERT 🚨</h2>
    <p><b>{emoji} Issue:</b> {issue}</p>
    <p><b>📊 Confidence:</b> {conf*100:.2f}%</p>
    <p><b>📍 Coordinates:</b> {gps}</p>
    <p><b>🗺 Map:</b> <a href="{map_link}" style="color:#4CAF50;">Open Location</a></p>
    <p><b>⏰ Time:</b> {datetime.now().strftime('%d-%m-%Y | %H:%M:%S')}</p>
    </body></html>
    """

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = "🚨 ECOVISION ALERT"
    msg.set_content("Alert")
    msg.add_alternative(html, subtype='html')

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    cv2.imwrite(tmp.name, image)

    with open(tmp.name, "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="jpeg")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

    os.remove(tmp.name)

# ================= MODEL =================
model = YOLO("best.pt")

# ================= DETECT =================
def detect(frame, conf):
    results = model.predict(frame, conf=conf, verbose=False)

    if len(results[0].boxes) == 0:
        return frame, [], []

    r = results[0]
    annotated = r.plot()
    issues, scores = [], []

    for i in range(len(r.boxes.cls)):
        cls = model.names[int(r.boxes.cls[i])]
        sc = float(r.boxes.conf[i])

        issues.append(cls)
        scores.append(sc)

        if cls.lower()=="pothole":
            st.session_state.pothole_count += 1
        elif cls.lower() in ["garbage","waste"]:
            st.session_state.garbage_count += 1

    return annotated, issues, scores

# ================= SIDEBAR =================
mode = st.sidebar.radio("Mode", ["Image","Video","Webcam"])
conf = st.sidebar.slider("Confidence",0.1,1.0,0.45)

# ================= IMAGE =================
if mode=="Image":
    gps_widget()
    gps = st.text_input("GPS")
    st.session_state.gps = gps

    file = st.file_uploader("Upload Image",["jpg","png"])
    if file:
        img = cv2.imdecode(np.frombuffer(file.read(),np.uint8),1)
        out,issues,scores = detect(img,conf)
        st.image(out,channels="BGR")

        for i in range(len(issues)):
            st.success(f"{issues[i]} ({scores[i]*100:.2f}%)")

        if issues:
            st.session_state.detected_image = out
            st.session_state.detected_issue = issues[0]
            st.session_state.detected_conf = scores[0]

# ================= VIDEO =================
elif mode=="Video":
    gps_widget()
    gps = st.text_input("GPS")
    st.session_state.gps = gps
    st.session_state.video_alert_sent = False

    file = st.file_uploader("Upload Video",["mp4","avi","mov"])
    if file:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(file.read())

        cap = cv2.VideoCapture(tfile.name)
        stframe = st.empty()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            out, issues, scores = detect(frame, conf)
            stframe.image(out, channels="BGR")

            if issues:
                st.session_state.detected_image = out
                st.session_state.detected_issue = issues[0]
                st.session_state.detected_conf = scores[0]

                if not st.session_state.video_alert_sent:
                    send_telegram(issues[0], out, scores[0], st.session_state.gps)
                    send_email(issues[0], out, scores[0], st.session_state.gps)
                    play_alert()
                    st.success("🚨 Video Alert Sent!")
                    st.session_state.video_alert_sent = True

        cap.release()

# ================= WEBCAM =================
elif mode=="Webcam":
    gps_widget()
    gps = st.text_input("GPS")
    st.session_state.gps = gps

    col1,col2 = st.columns(2)
    if col1.button("▶ Start"): st.session_state.run=True
    if col2.button("⏹ Stop"): st.session_state.run=False

    cap = cv2.VideoCapture(0)
    frame_window = st.empty()

    if not cap.isOpened():
        st.error("Camera not working. Try index 1")
    else:
        while st.session_state.run:
            ret, frame = cap.read()
            if not ret: break

            frame = cv2.resize(frame,(640,480))
            out, issues, scores = detect(frame, conf)

            for i in range(len(issues)):
                cv2.putText(out,f"{issues[i]} ({scores[i]*100:.1f}%)",
                            (10,30+i*30),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)

            now = time.time()

            if issues:
                if st.session_state.detect_start_time is None:
                    st.session_state.detect_start_time = now

                elapsed = now - st.session_state.detect_start_time

                cv2.putText(out,f"Timer: {int(elapsed)}s",
                            (10,450),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,255),2)

                if elapsed > 10 and not st.session_state.alert_sent:
                    send_telegram(issues[0], out, scores[0], st.session_state.gps)
                    send_email(issues[0], out, scores[0], st.session_state.gps)
                    play_alert()
                    st.success("🚨 Auto Alert Sent!")
                    st.session_state.alert_sent = True
            else:
                st.session_state.detect_start_time = None
                st.session_state.alert_sent = False

            frame_window.image(out, channels="BGR")

        cap.release()

# ================= ALERT BUTTONS =================
if st.session_state.detected_image is not None:
    c1,c2 = st.columns(2)

    if c1.button("Send Telegram"):
        send_telegram(
            st.session_state.detected_issue,
            st.session_state.detected_image,
            st.session_state.detected_conf,
            st.session_state.gps
        )
        st.success("Telegram sent")

    if c2.button("Send Email"):
        send_email(
            st.session_state.detected_issue,
            st.session_state.detected_image,
            st.session_state.detected_conf,
            st.session_state.gps
        )
        st.success("Email sent")
