# EasySTT v2.0 - Onboarding Manager
# Handles voice-based vocabulary training for personalized transcription

from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from core.personalization import PersonalizationManager


class OnboardingStep(Enum):
    NAME = "names"
    JARGON = "jargon"
    PHRASE = "phrases"


@dataclass
class StepConfig:
    """Configuration for each onboarding step."""
    category: str
    title: str
    prompt: str
    instruction: str


class OnboardingManager:
    """
    Manages the voice onboarding flow.
    Extracted from HeadlessSTT for reuse in GUI context.
    """
    
    STEPS: List[StepConfig] = [
        StepConfig(
            category="names",
            title="Step 1/3: Teach me your name",
            prompt="Please say: 'My name is [Your Name]'",
            instruction="Speak your full name clearly."
        ),
        StepConfig(
            category="jargon",
            title="Step 2/3: Technical vocabulary",
            prompt="Say some technical words or slang you use daily.",
            instruction="Speak any specialized terms from your work or hobbies."
        ),
        StepConfig(
            category="phrases",
            title="Step 3/3: Common phrases",
            prompt="Say a phrase you frequently dictate.",
            instruction="Speak a sentence you often use when taking notes."
        )
    ]
    
    def __init__(self):
        self.personalization = PersonalizationManager()
        self.current_step_index = 0
        self.is_complete = False
    
    @property
    def current_step(self) -> Optional[StepConfig]:
        """Get the current step configuration."""
        if self.current_step_index < len(self.STEPS):
            return self.STEPS[self.current_step_index]
        return None
    
    @property
    def total_steps(self) -> int:
        return len(self.STEPS)
    
    @property
    def progress(self) -> float:
        """Progress as percentage (0.0 to 1.0)."""
        return self.current_step_index / len(self.STEPS)
    
    def save_transcript(self, text: str) -> bool:
        """
        Save the transcribed text to vocabulary.
        Returns True if saved successfully.
        """
        step = self.current_step
        if not step or not text.strip():
            return False
        
        # Extract meaningful terms from the transcript
        terms = self._extract_terms(text, step.category)
        
        for term in terms:
            self.personalization.add_term(step.category, term)
        
        return len(terms) > 0
    
    def save_correction(self, correction: str) -> bool:
        """
        Save a user-provided correction instead of auto-extracted terms.
        """
        step = self.current_step
        if not step or not correction.strip():
            return False
        
        self.personalization.add_term(step.category, correction.strip())
        return True
    
    def advance(self) -> bool:
        """
        Move to the next step.
        Returns True if there are more steps, False if complete.
        """
        self.current_step_index += 1
        if self.current_step_index >= len(self.STEPS):
            self.is_complete = True
            return False
        return True
    
    def go_back(self) -> bool:
        """
        Move to the previous step.
        Returns True if successful, False if already at start.
        """
        if self.current_step_index > 0:
            self.current_step_index -= 1
            return True
        return False
    
    def reset(self) -> None:
        """Reset the onboarding flow to the beginning."""
        self.current_step_index = 0
        self.is_complete = False
    
    def _extract_terms(self, text: str, category: str) -> List[str]:
        """
        Extract meaningful terms from transcribed text.
        Uses simple heuristics based on category.
        """
        words = text.split()
        terms = []
        
        if category == "names":
            # Look for "my name is X" pattern or just take capitalized words
            text_lower = text.lower()
            if "my name is" in text_lower:
                idx = text_lower.find("my name is") + len("my name is")
                name_part = text[idx:].strip()
                # Take first 1-3 words as name
                name_words = name_part.split()[:3]
                name = " ".join(name_words).strip(".,!?")
                if name:
                    terms.append(name)
            else:
                # Just take words that look like names (capitalized)
                for word in words:
                    clean = word.strip(".,!?\"'")
                    if clean and clean[0].isupper() and len(clean) > 1:
                        terms.append(clean)
        
        elif category == "jargon":
            # Keep words that are technical-looking (mixed case, numbers, abbreviations)
            for word in words:
                clean = word.strip(".,!?\"'")
                if len(clean) > 2:
                    # Keep if: all caps, has numbers, mixed case
                    is_acronym = clean.isupper() and len(clean) <= 5
                    has_numbers = any(c.isdigit() for c in clean)
                    is_camel = any(c.isupper() for c in clean[1:])
                    
                    if is_acronym or has_numbers or is_camel or len(clean) > 5:
                        terms.append(clean)
        
        elif category == "phrases":
            # Keep the whole phrase (cleaned up)
            clean_phrase = " ".join(words).strip(".,!?\"'")
            if clean_phrase:
                terms.append(clean_phrase)
        
        return terms
