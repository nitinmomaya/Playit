"""Extract explicit quantities from user turns, never from model responses."""

import re
from fastapi import HTTPException
from gemini_setup.conversation import ConversationRequest

WORDS = dict(zip(
    "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split(),
    range(1, 21),
))
WORDS.update({"a": 1, "an": 1, "half": .5})


def requested_quantity(request: ConversationRequest) -> tuple[int | None, int | None]:
    count = duration = None
    for text in [turn.text for turn in request.history if turn.role == "user"] + [request.prompt]:
        text = text.lower()
        text = re.sub(r'\bhalf\s+(?:an?\s+)?hour\b', '30 minutes', text)
        for word, number in WORDS.items():
            text = re.sub(rf'\b{word}\b', str(number), text)
        counts = list(re.finditer(r'\b(\d+)\s*[- ]?\s*(?:songs?|tracks?)\b', text))
        times = list(re.finditer(r'\b(\d+(?:\.\d+)?)\s*[- ]?\s*(hours?|hrs?|h|minutes?|mins?|m)\b', text))
        # A new explicit quantity replaces an older count/time constraint.
        if counts:
            count, duration = int(counts[-1][1]), None
        elif re.search(r'\b(?:asked for|make it|wanted|give me)\s+(\d+)\b', text) and not times:
            count = int(re.search(r'\b(?:asked for|make it|wanted|give me)\s+(\d+)\b', text)[1])
            duration = None
        if times:
            duration = round(sum(float(match[1]) * (3600 if match[2].startswith("h") else 60) for match in times) * 1000)
            if not counts:
                count = None
    if count is not None and not 1 <= count <= 200:
        raise HTTPException(422, "Please request between 1 and 200 songs; the requested count was not changed.")
    if duration is not None and not 60_000 <= duration <= 8 * 3600_000:
        raise HTTPException(422, "Please request a duration between 1 minute and 8 hours.")
    return count, duration