
from typing import List, Optional, Dict


def get_interviewer_system_prompt() -> str:
    return (
        "You are a professional technical and HR interviewer. "
        "Generate relevant, clear, realistic interview questions. "
        "Return only valid JSON. No markdown or explanations."
    )


def get_evaluator_system_prompt() -> str:
    return (
        "You are an objective senior interview evaluator. "
        "Evaluate answers fairly using four scoring dimensions. "
        "Use evidence from the candidate's actual answer. "
        "Never invent evidence or quotations. "
        "Return only valid JSON matching the requested structure. "
        "Do not use markdown."
    )


def build_question_generation_messages(
    role: str,
    experience_level: str,
    difficulty: str,
    category: str,
    question_index: int,
    total_questions: int,
    previous_questions: List[str],
    resume_context: Optional[str] = None
) -> List[Dict[str, str]]:

    previous = "\n".join(
        f"- {question}" for question in previous_questions
    ) or "None"

    resume_section = ""
    if resume_context and resume_context.strip():
        resume_section = (
            "\nCandidate resume context:\n"
            f"{resume_context.strip()[:2500]}\n"
        )

    user_prompt = f"""
Generate interview question {question_index} of {total_questions}.

Role: {role}
Experience: {experience_level}
Difficulty: {difficulty}
Category: {category}

Previously asked questions:
{previous}

{resume_section}

Requirements:
- Ask one clear, realistic question.
- Match the candidate's experience level.
- Avoid repeating previous questions.
- Personalize using the resume when relevant.
- Keep context_hint to one short sentence.

Return exactly this JSON structure:
{{
    "question": "Interview question",
    "category": "{category}",
    "target_competency": "Main skill being evaluated",
    "context_hint": "Short answer guidance"
}}
"""

    return [
        {
            "role": "system",
            "content": get_interviewer_system_prompt()
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]


def build_follow_up_messages(
    role: str,
    experience_level: str,
    difficulty: str,
    current_question: str,
    candidate_answer: str,
    target_competency: str
) -> List[Dict[str, str]]:

    user_prompt = f"""
Interview role: {role}
Experience: {experience_level}
Difficulty: {difficulty}
Target competency: {target_competency}

Original question:
{current_question}

Candidate answer:
{candidate_answer[:3000]}

Generate ONE useful follow-up question.
Ask for clarification, technical depth, reasoning, or measurable results.

Return exactly this JSON structure:
{{
    "question": "Follow-up question",
    "category": "Follow-Up (Deep Dive)",
    "target_competency": "{target_competency}",
    "context_hint": "Short guidance"
}}
"""

    return [
        {
            "role": "system",
            "content": get_interviewer_system_prompt()
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]


def build_evaluation_messages(
    role: str,
    experience_level: str,
    difficulty: str,
    category: str,
    question_text: str,
    candidate_answer: str,
    is_follow_up: bool = False
) -> List[Dict[str, str]]:

    if category == "Technical & Domain":
        category_focus = (
            "Prioritize technical correctness, depth, problem solving, "
            "and explanations of why and how."
        )
    elif category == "Behavioral (STAR Method)":
        category_focus = (
            "Prioritize Situation, Task, Action, Result, "
            "individual contribution, and measurable outcomes."
        )
    else:
        category_focus = (
            "Prioritize relevance, communication, professionalism, "
            "motivation, and career direction."
        )

    user_prompt = f"""
Evaluate this candidate's interview answer.

Role: {role}
Experience: {experience_level}
Difficulty: {difficulty}
Category: {category}
Follow-up: {is_follow_up}

Interview question:
{question_text}

Candidate answer:
{candidate_answer[:5000]}

Score each dimension from 0.0 to 10.0:

1. relevance_score: How directly the answer addresses the question.
2. technical_score: Technical accuracy and depth.
3. communication_score: Clarity and professionalism.
4. structure_score: Logical organization and STAR structure where relevant.

Category-specific focus:
{category_focus}

Evidence rules:
- Strengths and weaknesses must use exact words from the answer.
- Use at least three consecutive words for each evidence_quote.
- Never invent quotations.
- If no suitable quote exists, use an empty string.
- Give at most 2 strengths and 2 weaknesses.
- Give at most 3 actionable tips.
- Keep each point concise.
- Keep model_answer around 100-150 words.
- Return valid JSON only. No markdown.

Return exactly this JSON structure:
{{
    "relevance_score": 7.5,
    "technical_score": 7.0,
    "communication_score": 8.0,
    "structure_score": 7.5,
    "strengths": [
        {{
            "point": "Clear strength",
            "evidence_quote": "Exact words from answer"
        }}
    ],
    "weaknesses": [
        {{
            "point": "Area to improve",
            "evidence_quote": "Exact words from answer",
            "suggestion": "Specific improvement"
        }}
    ],
    "actionable_tips": [
        "Practical improvement tip"
    ],
    "model_answer": "A concise professional example answer."
}}
"""

    return [
        {
            "role": "system",
            "content": get_evaluator_system_prompt()
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]
