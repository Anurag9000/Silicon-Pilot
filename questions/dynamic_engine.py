"""
LLM-Driven Dynamic Question Engine

Intelligently selects which questions to ask based on:
1. Information gain (which question reduces uncertainty most)
2. User's previous answers
3. Template requirements
4. Confidence in current understanding
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel
import json
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================================
# Question Models
# ============================================================================

class QuestionPriority(BaseModel):
    """Priority score for a question"""
    question_id: str
    question_text: str
    priority_score: float  # 0-100
    reasoning: str
    information_gain: float  # Expected reduction in uncertainty
    dependencies: List[str]  # Questions that should be asked first


class QuestionBatch(BaseModel):
    """Batch of questions to ask together"""
    tier: int  # 1=critical, 2=important, 3=optional
    questions: List[QuestionPriority]
    stop_reason: Optional[str] = None  # Why we stopped asking


# ============================================================================
# Dynamic Question Engine
# ============================================================================

class DynamicQuestionEngine:
    """
    LLM-driven question selection engine.
    
    Decides which questions to ask based on:
    - Current uncertainty
    - Information gain
    - User's previous answers
    - Template requirements
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if OpenAI and self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def select_next_questions(
        self,
        template: Dict[str, Any],
        answered_questions: Dict[str, Any],
        current_architecture: Optional[Dict[str, Any]] = None,
        max_questions: int = 5
    ) -> QuestionBatch:
        """
        Select next batch of questions to ask.
        
        Args:
            template: Device template with all questions
            answered_questions: Questions already answered
            current_architecture: Current architecture state
            max_questions: Maximum questions to ask in this batch
            
        Returns:
            QuestionBatch with prioritized questions
        """
        
        # Get unanswered questions
        all_questions = template.get("questions", [])
        unanswered = [
            q for q in all_questions
            if q["id"] not in answered_questions
        ]
        
        if not unanswered:
            return QuestionBatch(
                tier=0,
                questions=[],
                stop_reason="All questions answered"
            )
        
        if not self.client:
            # Fallback: priority-based selection
            return self._fallback_select_questions(
                unanswered, answered_questions, max_questions
            )
        
        # Use LLM to intelligently select questions
        return self._llm_select_questions(
            template, unanswered, answered_questions,
            current_architecture, max_questions
        )
    
    def _llm_select_questions(
        self,
        template: Dict[str, Any],
        unanswered: List[Dict[str, Any]],
        answered: Dict[str, Any],
        architecture: Optional[Dict[str, Any]],
        max_questions: int
    ) -> QuestionBatch:
        """Use LLM to select most valuable questions"""
        
        prompt = self._build_question_selection_prompt(
            template, unanswered, answered, architecture
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Parse LLM response into QuestionBatch
            priorities = []
            for q in result.get("selected_questions", [])[:max_questions]:
                priorities.append(QuestionPriority(
                    question_id=q["question_id"],
                    question_text=q["question_text"],
                    priority_score=q["priority_score"],
                    reasoning=q["reasoning"],
                    information_gain=q.get("information_gain", 50.0),
                    dependencies=q.get("dependencies", [])
                ))
            
            return QuestionBatch(
                tier=result.get("tier", 1),
                questions=priorities,
                stop_reason=result.get("stop_reason")
            )
            
        except Exception as e:
            print(f"LLM question selection failed: {e}")
            return self._fallback_select_questions(
                unanswered, answered, max_questions
            )
    
    def _get_system_prompt(self) -> str:
        """System prompt for question selection"""
        return """You are an expert hardware engineer assistant. Your task is to intelligently select which questions to ask the user to gather the most critical information for their hardware design.

Prioritize questions based on:
1. **Information Gain**: Which question will most reduce uncertainty about the design?
2. **Dependencies**: Ask foundational questions before detail questions
3. **User Context**: Consider what they've already told you
4. **Design Impact**: Questions that affect major architectural decisions come first

Tier definitions:
- Tier 1 (Critical): Must answer to proceed - affects core architecture
- Tier 2 (Important): Significantly improves design quality
- Tier 3 (Optional): Nice-to-have refinements

Respond with JSON:
{
    "tier": 1,
    "selected_questions": [
        {
            "question_id": "motor_type",
            "question_text": "What type of motor?",
            "priority_score": 95,
            "reasoning": "Motor type determines PWM requirements, current sensing, and control algorithms",
            "information_gain": 80,
            "dependencies": []
        }
    ],
    "stop_reason": null
}

Stop asking when:
- Top design choices are stable
- Remaining questions only affect minor details
- User has provided enough for a good recommendation"""
    
    def _build_question_selection_prompt(
        self,
        template: Dict[str, Any],
        unanswered: List[Dict[str, Any]],
        answered: Dict[str, Any],
        architecture: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for question selection"""
        
        prompt = f"""Template: {template.get('name', 'Unknown')}
Device Type: {template.get('device_type', 'Unknown')}

Already Answered:
"""
        for q_id, answer in answered.items():
            prompt += f"- {q_id}: {answer}\n"
        
        prompt += f"\nUnanswered Questions ({len(unanswered)}):\n"
        for q in unanswered:
            prompt += f"- {q['id']}: {q['text']}"
            if q.get('priority'):
                prompt += f" (priority: {q['priority']})"
            prompt += "\n"
        
        if architecture:
            prompt += f"\nCurrent Architecture:\n{json.dumps(architecture, indent=2)}\n"
        
        prompt += "\nSelect the most valuable questions to ask next (max 5). Consider information gain and dependencies."
        
        return prompt
    
    def _fallback_select_questions(
        self,
        unanswered: List[Dict[str, Any]],
        answered: Dict[str, Any],
        max_questions: int
    ) -> QuestionBatch:
        """Fallback: priority-based selection when LLM unavailable"""
        
        # Sort by priority
        priority_map = {"high": 3, "medium": 2, "low": 1}
        sorted_questions = sorted(
            unanswered,
            key=lambda q: priority_map.get(q.get("priority", "medium"), 2),
            reverse=True
        )
        
        # Select top questions
        selected = []
        for q in sorted_questions[:max_questions]:
            selected.append(QuestionPriority(
                question_id=q["id"],
                question_text=q["text"],
                priority_score=priority_map.get(q.get("priority", "medium"), 2) * 30,
                reasoning=f"Priority: {q.get('priority', 'medium')}",
                information_gain=50.0,
                dependencies=[]
            ))
        
        # Determine tier
        if selected and selected[0].priority_score >= 90:
            tier = 1
        elif selected and selected[0].priority_score >= 60:
            tier = 2
        else:
            tier = 3
        
        return QuestionBatch(
            tier=tier,
            questions=selected,
            stop_reason=None
        )
    
    def should_stop_asking(
        self,
        answered_count: int,
        total_count: int,
        current_confidence: float,
        top_n_stable: bool = False
    ) -> Tuple[bool, str]:
        """
        Determine if we should stop asking questions.
        
        Returns:
            (should_stop, reason)
        """
        
        # Stop if all questions answered
        if answered_count >= total_count:
            return True, "All questions answered"
        
        # Stop if high confidence and top recommendations stable
        if current_confidence > 0.85 and top_n_stable:
            return True, "High confidence, top recommendations stable"
        
        # Stop if answered enough critical questions
        if answered_count >= total_count * 0.7 and current_confidence > 0.75:
            return True, "Sufficient information gathered"
        
        return False, ""


# ============================================================================
# Information Gain Calculator
# ============================================================================

class InformationGainCalculator:
    """Calculate expected information gain from asking a question"""
    
    def calculate_gain(
        self,
        question: Dict[str, Any],
        current_candidates: List[Dict[str, Any]],
        answered_questions: Dict[str, Any]
    ) -> float:
        """
        Calculate expected information gain.
        
        Returns:
            Score 0-100 indicating expected reduction in uncertainty
        """
        
        # Simple heuristic: questions that affect more constraints have higher gain
        gain = 0.0
        
        # Check if question affects critical constraints
        critical_keywords = ["voltage", "current", "power", "temperature", "protocol"]
        if any(kw in question.get("text", "").lower() for kw in critical_keywords):
            gain += 30.0
        
        # Check if question has many choices (more information)
        choices = question.get("choices", [])
        if len(choices) > 5:
            gain += 20.0
        elif len(choices) > 2:
            gain += 10.0
        
        # Check priority
        if question.get("priority") == "high":
            gain += 40.0
        elif question.get("priority") == "medium":
            gain += 20.0
        
        return min(gain, 100.0)


# ============================================================================
# Example Usage
# ============================================================================

def example_usage():
    """Demonstrate dynamic question selection"""
    
    # Sample template
    template = {
        "name": "CAN Motor Controller",
        "device_type": "motor_controller",
        "questions": [
            {
                "id": "motor_type",
                "text": "What type of motor?",
                "type": "choice",
                "choices": ["BLDC", "DC", "Stepper"],
                "priority": "high"
            },
            {
                "id": "supply_voltage",
                "text": "Supply voltage?",
                "type": "choice",
                "choices": ["12V", "24V", "48V"],
                "priority": "high"
            },
            {
                "id": "peak_current",
                "text": "Peak current?",
                "type": "choice",
                "choices": ["5A", "10A", "20A"],
                "priority": "high"
            },
            {
                "id": "control_mode",
                "text": "Control mode?",
                "type": "choice",
                "choices": ["Open-loop", "Closed-loop"],
                "priority": "medium"
            },
            {
                "id": "enclosure",
                "text": "Enclosure type?",
                "type": "choice",
                "choices": ["IP20", "IP65"],
                "priority": "low"
            }
        ]
    }
    
    # User has answered some questions
    answered = {
        "motor_type": "BLDC"
    }
    
    # Create engine
    engine = DynamicQuestionEngine(use_llm=False)
    
    # Select next questions
    batch = engine.select_next_questions(
        template=template,
        answered_questions=answered,
        max_questions=3
    )
    
    print(f"Tier: {batch.tier}")
    print(f"Questions to ask:")
    for q in batch.questions:
        print(f"  - {q.question_text} (score: {q.priority_score:.0f})")
        print(f"    Reasoning: {q.reasoning}")


if __name__ == "__main__":
    example_usage()
