"""Extract explicit quantities from user turns, never from model responses."""

# Import re.
import re
# Import HTTPException.
from fastapi import HTTPException
# Import ConversationRequest.
from gemini_setup.conversation import ConversationRequest

# Set WORDS.
WORDS = dict(zip(
    "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split(),
    range(1, 21),
))
# Call WORDS.update.
WORDS.update({"a": 1, "an": 1, "half": .5})


# Define requested_quantity.
def requested_quantity(request: ConversationRequest) -> tuple[int | None, int | None]:
    # Set count, duration.
    count = duration = None
    # Process each text in [turn.text for turn in request.history if turn.role == 'user'] + [request.p....
    for text in [turn.text for turn in request.history if turn.role == "user"] + [request.prompt]:
        # Set text.
        text = text.lower()
        # Set text.
        text = re.sub(r'\bhalf\s+(?:an?\s+)?hour\b', '30 minutes', text)
        # Process each (word, number) in WORDS.items().
        for word, number in WORDS.items():
            # Set text.
            text = re.sub(rf'\b{word}\b', str(number), text)
        # Set counts.
        counts = list(re.finditer(r'\b(\d+)\s*[- ]?\s*(?:songs?|tracks?)\b', text))
        # Set times.
        times = list(re.finditer(r'\b(\d+(?:\.\d+)?)\s*[- ]?\s*(hours?|hrs?|h|minutes?|mins?|m)\b', text))
        # A new explicit quantity replaces an older count/time constraint.
        if counts:
            # Set (count, duration).
            count, duration = int(counts[-1][1]), None
        # Check re.search('\\b(?:asked for|make it|wanted|give me)\\s+(\\d+)\\b', text) and....
        elif re.search(r'\b(?:asked for|make it|wanted|give me)\s+(\d+)\b', text) and not times:
            # Set count.
            count = int(re.search(r'\b(?:asked for|make it|wanted|give me)\s+(\d+)\b', text)[1])
            # Set duration.
            duration = None
        # Check times.
        if times:
            # Set duration.
            duration = round(sum(float(match[1]) * (3600 if match[2].startswith("h") else 60) for match in times) * 1000)
            # Check not counts.
            if not counts:
                # Set count.
                count = None
    # Check count is not None and (not 1 <= count <= 200).
    if count is not None and not 1 <= count <= 200:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(422, "Please request between 1 and 200 songs; the requested count was not changed.")
    # Check duration is not None and (not 60000 <= duration <= 8 * 3600000).
    if duration is not None and not 60_000 <= duration <= 8 * 3600_000:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(422, "Please request a duration between 1 minute and 8 hours.")
    # Return the assembled result to the caller.
    return count, duration

# File summary
# - Extracts song counts and listening times from user turns.
# - Allows later explicit requests to replace older quantities.
# - Rejects counts/durations outside supported limits.
