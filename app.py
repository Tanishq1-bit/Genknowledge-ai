
import streamlit as st
import requests
import json
import re

st.set_page_config(page_title="GenKnowledge AI", page_icon="🎓")

API = "http://127.0.0.1:8000"

st.title("🎓 GenKnowledge AI")
st.caption("Your AI-powered learning assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# Sidebar
page = st.sidebar.radio("Navigation", ["Chat Assistant", "Quiz Generator"])

file = st.sidebar.file_uploader("Upload Course PDF", type="pdf")

if file and st.sidebar.button("Upload Document"):
    try:
        r = requests.post(API + "/upload",
            files={"file": (file.name, file.getvalue(), "application/pdf")})
        r.raise_for_status()
        st.sidebar.success("Document uploaded successfully!")
    except requests.RequestException:
        st.sidebar.error("Upload failed. Check FastAPI.")

# Chat Assistant
if page == "Chat Assistant":

    st.header("💬 Chat Assistant")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])
            if m.get("sources"):
                with st.expander("View Sources"):
                    for s in m["sources"]:
                        st.write("Page:", s.get("page"))
                        st.caption(s["text"])

    question = st.chat_input("Ask something about your course...")

    if question:
        history = st.session_state.messages[-8:]

        try:
            r = requests.post(API + "/chat", json={
                "question": question,
                "history": history
            })
            r.raise_for_status()
            data = r.json()

            st.session_state.messages.extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": data["answer"],
                 "sources": data.get("sources", [])}
            ])
            st.rerun()

        except requests.RequestException:
            st.error("FastAPI connection failed.")

# Quiz Generator
else:

    st.header("📝 Quiz Generator")
    topic = st.text_input("Enter a topic")

    if st.button("Generate Quiz") and topic.strip():
        try:
            r = requests.post(API + "/quiz", json={"topic": topic})
            r.raise_for_status()

            text = r.json()["quiz"]
            text = re.sub(r"```(?:json)?|```", "", text).strip()
            data = json.loads(text[text.find("{"):text.rfind("}")+1])

            st.session_state.quiz = data["questions"]
            st.session_state.submitted = False
            st.rerun()

        except Exception as e:
            st.error(f"Quiz generation failed: {e}")

    if st.session_state.quiz:
        questions = st.session_state.quiz

        if not st.session_state.submitted:

            with st.form("quiz_form"):
                for i, q in enumerate(questions):
                    st.write(f"**Q{i+1}. {q['question']}**")
                    st.radio("Choose answer", ["A", "B", "C", "D"],
                        format_func=lambda x, q=q: f"{x}) {q['options'][x]}",
                        key=f"q{i}", index=None)

                submit = st.form_submit_button("Submit Quiz")

            if submit:
                st.session_state.submitted = True
                st.rerun()

        else:
            score = 0

            for i, q in enumerate(questions):
                answer = st.session_state.get(f"q{i}")
                correct = q["answer"]

                if answer == correct:
                    score += 1
                    st.success(f"Q{i+1}: Correct!")
                else:
                    st.error(f"Q{i+1}: Incorrect!")

                st.write("Your answer:", answer or "Not attempted")
                st.write("Correct answer:", correct)
                st.info(q["explanation"])

            st.metric("Final Score", f"{score}/{len(questions)}")

            if st.button("Generate New Quiz"):
                st.session_state.quiz = None
                st.session_state.submitted = False
                st.rerun()
