"""
Prompt Templates and Builders for AI Interview Generation and Evaluation.
Enforces strict JSON schema output, persona conditioning,
contextual tailoring, evidence-based rubrics, and quotation verification.
"""

from typing import List, Optional, Dict, Any


def get_interviewer_system_prompt() -> str:
    """Returns the core system persona prompt for the AI interviewer."""
    return (
        "You are an elite, highly experienced Technical & HR Hiring Manager at a top technology company. "
        "Your objective is to conduct realistic, professional, and insightful interviews. "
        "Your questions must be clear, relevant, contextual, and calibrated to the candidate's experience level. "
        "Always output ONLY valid JSON matching the exact schema requested. Do not include markdown preamble or explanations."
    )


def get_evaluator_system_prompt() -> str:
    """Returns the evaluator persona prompt for evidence-based assessment."""
    return (
        "You are an expert Interview Evaluation Panelist and Senior Bar Raiser at a premier technology company. "
        "Your role is to provide transparent, evidence-based, objective evaluations of candidate interview answers. "
        "You evaluate candidate answers strictly against four objective dimensions (each scored 0.0 to 10.0): "
        "Answer Relevance, Technical Depth & Correctness, Communication & Clarity, and Structure & STAR Compliance. "
        "For all strengths and weaknesses, you MUST cite exact verbatim words from the candidate's answer as evidence. "
        "Always output ONLY valid JSON matching the exact schema requested. Do not invent or fabricate quotes."
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
    """
    Constructs messages for generating a new interview question.
    """
    prev_str = "\n".join([f"- {q}" for q in previous_questions]) if previous_questions else "None (First question)"

    resume_section = ""
    if resume_context and resume_context.strip():
        resume_section = f"""
Candidate Resume Context (Reference projects, technologies, or education if relevant):
\"\"\"
{resume_context.strip()}
\"\"\"
"""

    user_prompt = f"""
Generate Question #{question_index} of {total_questions} for an upcoming interview.

Interview Parameters:
- Target Job Role: {role}
- Candidate Experience Level: {experience_level}
- Target Difficulty: {difficulty}
- Required Category: {category}

Already Asked Questions (DO NOT REPEAT OR CLOSELY PARAPHRASE):
{prev_str}
{resume_section}
Requirements:
1. Question must be realistic, highly relevant to {role}, and calibrated for {experience_level}.
2. If Category is 'Technical & Domain', assess technical fundamentals, problem-solving, or system design.
3. If Category is 'Behavioral (STAR Method)', frame the question to prompt Situation, Task, Action, Result.
4. If Category is 'HR & Background', evaluate career motivations, teamwork, adaptability, or work ethics.
5. If resume context is provided, personalize the question towards their actual experience or projects when appropriate.

Return ONLY a JSON object with this EXACT structure:
{{
  "question": "<The interview question text>",
  "category": "{category}",
  "target_competency": "<Key skill or competency being evaluated (e.g., Problem Solving, Concurrency, System Design, Conflict Resolution)>",
  "context_hint": "<A concise 1-sentence tip on what a strong answer should demonstrate>"
}}
"""
    return [
        {"role": "system", "content": get_interviewer_system_prompt()},
        {"role": "user", "content": user_prompt}
    ]


def build_follow_up_messages(
    role: str,
    experience_level: str,
    difficulty: str,
    current_question: str,
    candidate_answer: str,
    target_competency: str
) -> List[Dict[str, str]]:
    """
    Constructs messages for generating a dynamic follow-up question
    based on the candidate's immediate response.
    """
    user_prompt = f"""
You are continuing the interview for a {role} ({experience_level}).

Original Question:
\"{current_question}\"

Candidate's Answer:
\"\"\"
{candidate_answer}
\"\"\"

Task:
Generate a sharp, insightful FOLLOW-UP question that digs deeper into the candidate's answer.
- If they mentioned a specific tool, algorithm, or decision, probe why they chose it over alternatives.
- If their answer was too vague or surface-level, ask for a concrete technical detail or outcome.
- If their answer was strong, escalate the scenario (e.g., "What if the traffic doubled?" or "How did you measure that impact?").

Return ONLY a JSON object with this EXACT structure:
{{
  "question": "<The follow-up interview question>",
  "category": "Follow-Up (Deep Dive)",
  "target_competency": "{target_competency}",
  "context_hint": "<Brief hint on what technical depth or evidence the candidate needs to provide now>"
}}
"""
    return [
        {"role": "system", "content": get_interviewer_system_prompt()},
        {"role": "user", "content": user_prompt}
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
    """
    Constructs messages for evaluating a candidate's answer across 4 dimensions
    with evidence-based quotes and actionable model answers.
    """
    category_instructions = ""
    if category == "Technical & Domain":
        category_instructions = (
            "- Technical Depth & Correctness is heavily weighted. Verify architectural decisions, algorithms, and syntax accuracy.\n"
            "- Evaluate whether the candidate explained 'why' and 'how', not just high-level buzzwords."
        )
    elif category == "Behavioral (STAR Method)":
        category_instructions = (
            "- Structure & STAR Method is heavily weighted. Verify Situation, Task, Action, and Result.\n"
            "- Check whether the candidate specified their personal role ('I') versus vague team statements ('we'), and if results were quantified."
        )
    else:  # HR & Background
        category_instructions = (
            "- Communication and Relevance are heavily weighted. Verify cultural alignment, career vision, and professionalism."
        )

    user_prompt = f"""
Evaluate the candidate's response to the interview question below.

Context:
- Target Role: {role}
- Experience Level: {experience_level}
- Interview Difficulty: {difficulty}
- Question Category: {category}
- Is Follow-Up Question: {"Yes" if is_follow_up else "No"}

Question:
\"{question_text}\"

Candidate's Submitted Answer:
\"\"\"
{candidate_answer}
\"\"\"

Scoring Rubric (Grade each dimension from 0.0 to 10.0 as a decimal number):
1. relevance_score (0.0 to 10.0): Did the candidate answer the exact question directly without rambling?
2. technical_score (0.0 to 10.0): Are stated facts, technologies, and concepts correct and deep?
3. communication_score (0.0 to 10.0): Is the language concise, professional, articulate, and well-phrased?
4. structure_score (0.0 to 10.0): Is the thought process organized logically (STAR framework for behavioral/projects)?

Category-Specific Assessment Focus:
{category_instructions}

Critical Evidence Citation Rules:
- For EVERY strength and weakness, quote exact words (at least 3 consecutive words) verbatim from the candidate's answer as 'evidence_quote'.
- DO NOT paraphrase or fabricate quotes. If no direct quote applies, state 'Overall answer context'.

Return ONLY a JSON object with this EXACT structure:
{{
  "relevance_score": <float 0.0 - 10.0>,
  "technical_score": <float 0.0 - 10.0>,
  "communication_score": <float 0.0 - 10.0>,
  "structure_score": <float 0.0 - 10.0>,
  "strengths": [
    {{
      "point": "<Clear statement of strength>",
      "evidence_quote": "<Exact verbatim snippet from candidate answer>"
    }}
  ],
  "weaknesses": [
    {{
      "point": "<Identified gap or limitation>",
      "evidence_quote": "<Exact verbatim snippet from candidate answer>",
      "suggestion": "<Specific actionable advice on how to improve this point>"
    }}
  ],
  "actionable_tips": [
    "<Concise bullet point advice for this candidate>"
  ],
  "model_answer": "<A comprehensive, professional model answer demonstrating how a top {experience_level} {role} would answer this exact question>"
}}
"""
    return [
        {"role": "system", "content": get_evaluator_system_prompt()},
        {"role": "user", "content": user_prompt}
    ]
