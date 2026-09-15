"""Bounded overlapping lyric contexts. No sentence-boundary claim is made."""
MAX_LINES = 20
OVERLAP_LINES = 2

def natural_boundary(line):
    text = line["text"].rstrip()
    if not text:
        return True
    return text.rstrip('」』”"）)').endswith(("。", "！", "？", ".", "!", "?"))

def split_blocks(lines):
    """Prefer the last natural boundary in the window; hard cuts overlap two lines."""
    result = []
    start = 0
    while start < len(lines):
        limit = min(start + MAX_LINES, len(lines))
        end = limit
        hard_cut = False
        if limit < len(lines):
            boundaries = [i + 1 for i in range(start, limit) if natural_boundary(lines[i])]
            if boundaries:
                end = boundaries[-1]
            else:
                hard_cut = True
        result.append(list(range(start, end)))
        start = end - OVERLAP_LINES if hard_cut else end
    return result
