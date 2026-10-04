import re
from typing import List


def extract_tags(text: str) -> List[str]:
    """
    Extracts tags in format #tag or [tag].
    BUG: Unescaped square brackets in regex pattern lead to character class syntax error
    or missed brackets.
    """
    # BUG: [.*] inside unescaped brackets matches single characters instead of bracketed token
    pattern = r"#(\w+)|\[(.*)\]"
    matches = re.findall(pattern, text)
    tags = []
    for tag_hash, tag_bracket in matches:
        if tag_hash:
            tags.append(tag_hash)
        elif tag_bracket:
            tags.append(tag_bracket)
    return tags
