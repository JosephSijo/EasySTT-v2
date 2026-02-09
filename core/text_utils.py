import re
from typing import List

# ============================================================================
# STERILIZATION LAYER - Ported from EasySTT v1
# ============================================================================

# Professional filler words
FILLER_WORDS = [
    r'\bum+\b', r'\buh+\b', r'\bah+\b', r'\ber+\b',
    r'\blike\b', r'\byou know\b', r'\bi mean\b', r'\bso+\b',
    r'\bbasically\b', r'\bliterally\b', r'\bactually\b',
    r'\bkind of\b', r'\bsort of\b'
]
FILLER_REGEX = re.compile('|'.join(FILLER_WORDS), re.IGNORECASE)
MULTISPACE_REGEX = re.compile(r'\s+')

def remove_hallucinations(text: str, max_repeats: int = 3) -> str:
    """
    Hallucination Filter: Remove phrases repeated more than max_repeats times.
    Whisper can loop on "Thank you", "Subtitles by...", etc. during silence.
    """
    if not text:
        return text
    
    words = text.split()
    if len(words) < max_repeats:
        return text
    
    cleaned_words = []
    i = 0
    while i < len(words):
        found_repeat = False
        # Check patterns of length 1-5 words
        for pattern_len in range(1, min(6, len(words) - i)):
            pattern = words[i:i + pattern_len]
            count = 1
            j = i + pattern_len
            while j + pattern_len <= len(words):
                if words[j:j + pattern_len] == pattern:
                    count += 1
                    j += pattern_len
                else:
                    break
            
            if count > max_repeats:
                cleaned_words.extend(pattern)
                i = j  # Skip all repeats
                found_repeat = True
                break
        
        if not found_repeat:
            cleaned_words.append(words[i])
            i += 1
    
    return ' '.join(cleaned_words)

def remove_fillers(text: str) -> str:
    """
    Filler Filter: Remove disfluencies (um, uh, like, you know, etc.)
    """
    if not text:
        return text
    
    result = FILLER_REGEX.sub('', text)
    result = MULTISPACE_REGEX.sub(' ', result).strip()
    return result

def auto_punctuate_and_capitalize(text: str) -> str:
    """
    Auto-Punctuation & Casing: Ensure proper sentence formatting.
    """
    if not text or not text.strip():
        return text
    
    text = text.strip()
    if text[0].islower():
        text = text[0].upper() + text[1:]
    
    end_punctuation = {'.', '!', '?', ':', ';', '…', '"', "'", ')', ']', '}'}
    if text[-1] not in end_punctuation:
        text = text + '.'
    
    return text

# ============================================================================
# SMART FORMATTING LAYER
# ============================================================================

FORMATTING_COMMANDS = [
    (r'\bnew line\b', '\n'),
    (r'\bnewline\b', '\n'),
    (r'\bnext line\b', '\n'),
    (r'\bline break\b', '\n'),
    (r'\benter\b', '\n'),
    (r'\bnew paragraph\b', '\n\n'),
    (r'\bparagraph break\b', '\n\n'),
    (r'\bbullet point\b', '\n• '),
    (r'\bbullet\b', '\n• '),
    (r'\bdash point\b', '\n- '),
    (r'\blist item\b', '\n• '),
    (r'\bnumber one\b', '\n1. '),
    (r'\bnumber two\b', '\n2. '),
    (r'\bnumber three\b', '\n3. '),
    (r'\bnumber four\b', '\n4. '),
    (r'\bnumber five\b', '\n5. '),
    (r'\bopen quote\b', '"'),
    (r'\bclose quote\b', '"'),
    (r'\bquote\b', '"'),
    (r'\bunquote\b', '"'),
    (r'\bend quote\b', '"'),
    (r'\bperiod\b', '.'),
    (r'\bfull stop\b', '.'),
    (r'\bcomma\b', ','),
    (r'\bquestion mark\b', '?'),
    (r'\bexclamation mark\b', '!'),
    (r'\bexclamation point\b', '!'),
    (r'\bcolon\b', ':'),
    (r'\bsemicolon\b', ';'),
    (r'\btab\b', '\t'),
    (r'\bhyphen\b', '-'),
    (r'\bdash\b', ' — '),
]

FORMATTING_MAP = {re.compile(pattern, re.IGNORECASE): replacement for pattern, replacement in FORMATTING_COMMANDS}
MULTI_NEWLINE_REGEX = re.compile(r'\n{3,}')

def apply_formatting_commands(text: str) -> str:
    """
    Smart Formatting: Convert spoken formatting cues to actual formatting.
    """
    if not text:
        return text
    
    result = text
    for pattern_re, replacement in FORMATTING_MAP.items():
        result = pattern_re.sub(replacement, result)
    
    lines = [line.strip() for line in result.split('\n')]
    result = '\n'.join(lines)
    result = MULTI_NEWLINE_REGEX.sub('\n\n', result)
    
    return result.strip()

def sterilize_transcript(text: str, remove_filler: bool = True) -> str:
    """
    Full sterilization pipeline.
    """
    if not text:
        return text
    
    text = remove_hallucinations(text)
    if remove_filler:
        text = remove_fillers(text)
    
    return text.strip()
