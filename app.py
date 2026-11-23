import streamlit as st
import requests
import datetime

st.set_page_config(
    page_title="HR Interview Simulator",
    page_icon="💼",
    layout="centered"
)

API_KEY = st.secrets["API_KEY"]
st.title("HR Interview Simulator")

st.markdown("Practice HR interviews with AI-powered feedback.")

st.info("Practice HR interview questions and improve your answers using AI feedback.")

if "history" not in st.session_state:
    st.session_state.history = []

questions = [
    "Tell me about yourself.",
    "What are your strengths?",
    "What are your weaknesses?",
    "Why should we hire you?",
    "Describe a challenge you faced.",
    "Where do you see yourself in 5 years?",
    "Why do you want this job?",
    "Tell me about a time you worked in a team.",
    "How do you handle pressure?",
    "Describe a leadership experience."
]

question = st.selectbox("Choose Interview Question", questions)

answer = st.text_area("Type your answer")

st.caption("Try answering in 3-5 sentences for better evaluation.")

if st.button("Evaluate Answer"):

    prompt = f"""
    You are an HR interviewer.

    Evaluate this answer.

    Question:
    {question}

    Answer:
    {answer}

    Give:
    1. Score out of 10
    2. Strengths
    3. Weaknesses
    4. Better answer
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openrouter/auto",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    with st.spinner("Evaluating your answer..."):

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )

        result = response.json()

        st.subheader("🤖 AI Feedback")

        try:
            feedback = result["choices"][0]["message"]["content"]

            st.success("Evaluation Completed Successfully!")

            st.write(feedback)

            st.download_button(
                label="Download Feedback",
                data=feedback,
                file_name="feedback.txt",
                mime="text/plain"
            )

            st.session_state.history.append({
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "question": question,
                "answer": answer,
                "feedback": feedback
            })

        except:
            st.error(result)

st.divider()
if st.button("Clear History"):
    st.session_state.history = []
st.subheader("📜 Previous Attempts")

for item in st.session_state.history:

    with st.expander(f"{item['time']} - {item['question']}"):

        st.write("**Your Answer:**")
        st.write(item["answer"])

        st.write("**Feedback:**")
        st.write(item["feedback"])
st.markdown("---")
st.caption("Developed by V Saipriya PDKV")
