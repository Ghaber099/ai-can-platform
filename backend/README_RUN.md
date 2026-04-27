AI CAN PLATFORM – RUN GUIDE
===========================

📌 Project Overview:
This is an AI-powered CAN log analysis tool.
It can:
- Upload CAN logs
- Analyze CAN IDs
- Detect signals
- Identify best signal
- Show correlation between signals
- Detect anomalies
- Visualize signals in graphs

----------------------------------------

⚙️ Requirements:
- Python 3.10+
- pip installed
- Browser (Chrome recommended)

----------------------------------------

🚀 Backend Setup:

1. Go to backend folder:
cd backend

2. Install dependencies:
pip install fastapi uvicorn python-multipart

3. Run server:
python -m uvicorn main:app --reload

4. Server runs at:
http://127.0.0.1:8000

----------------------------------------

🌐 Frontend Setup:

1. Open frontend folder
2. Open file:
upload.html

3. Run in browser:
Double-click OR use Live Server

----------------------------------------

📂 Usage Steps:

1. Upload CAN log file
2. Select CAN ID
3. Click Analyze

System will:
- Show analysis report
- Detect best signal ⭐
- Show correlated signals 🔗
- Display graph
- Highlight anomalies (if any)

----------------------------------------

📊 Features:

✔ Signal Detection  
✔ Signal Classification  
✔ Score Ranking  
✔ Best Signal Highlight  
✔ Correlation Analysis  
✔ Multi-Signal Graph  
✔ Anomaly Detection  
✔ Export Report  
✔ Export Graph  

----------------------------------------

⚠️ Notes:

- Upload folder must exist
- Backend must be running before frontend
- Use CTRL + F5 to refresh frontend

----------------------------------------

📌 Status:
Phase 1 – Almost Complete