# 🎯 HR Interview Simulator

An AI-powered interview preparation platform that helps students and job seekers practice interviews, receive intelligent feedback, and track their performance.

Built using **Python, Streamlit, and OpenRouter API**.

## ✨ Features

### 🔐 User Authentication
- Create a new account
- Secure password hashing
- Login and Logout

### 🎤 AI-Powered Interview Practice
- Select from multiple job roles
- Choose experience level and interview difficulty
- Generate interview questions using AI
- Practice HR, technical, and behavioral questions
- Upload a resume in PDF, TXT, or MD format

### 📊 AI Evaluation & Feedback
- Evaluate interview answers using AI
- Receive scores and personalized feedback
- Review relevance, technical knowledge, communication, and answer structure

### 📈 History & Analytics
- View previous interview sessions
- Track completed and ongoing interviews
- Visualize interview status using a pie chart
- Compare interview scores using a bar chart
- View overall performance summaries

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend development |
| Streamlit | User interface |
| OpenRouter API | AI question generation and evaluation |
| SQLite | Database management |
| Requests | API communication |
| Bcrypt | Secure password hashing |
| Pandas | Analytics and data handling |

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/VSaipriyaSec/HR-Interview-Simulator.git
cd HR-Interview-Simulator
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure OpenRouter API

1. Create an API key through [OpenRouter](https://openrouter.ai/).
2. Create a `.streamlit/secrets.toml` file.
3. Configure the API key using the secret name expected by the application.

**Important:** Never upload your API key or `secrets.toml` file to GitHub.

### 5. Run the Application

```bash
streamlit run app.py
```

The application will open in your browser.

## 📁 Project Structure

```text
HR-Interview-Simulator/
│
├── app.py
├── requirements.txt
├── README.md
│
├── src/
│   ├── config.py
│   ├── core/
│   ├── models/
│   ├── services/
│   ├── storage/
│   └── ui/
│
├── tests/
├── data/
└── .streamlit/
```

## 🧪 Testing

Run the project test suite:

```bash
python -m pytest -q
```

## 👩‍💻 Project Author

**V Saipriya**

Final-Year Computer Science and Engineering Student

GitHub: [VSaipriyaSec](https://github.com/VSaipriyaSec)

---

⭐ If you find this project useful, consider giving it a star!