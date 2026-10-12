"""BV-Text v6.1 line-based TOC model; no source-text markers."""
from dataclasses import dataclass, asdict
from uuid import uuid4
import re

@dataclass
class TocEntry:
    document_id: str
    title: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    selected_text: str
    context: str = ''
    id: str = ''
    def __post_init__(self):
        if not self.id: self.id = str(uuid4())
        if self.line_start < 1 or self.line_end < self.line_start: raise ValueError('Invalid line')
        if self.column_start < 0 or self.column_end < 0: raise ValueError('Invalid column')
    def to_dict(self): return asdict(self)

def line_column(source, offset):
    if not 0 <= offset <= len(source): raise ValueError('Offset out of range')
    return source.count('\n', 0, offset) + 1, offset - (source.rfind('\n', 0, offset) + 1)

def create_entry(document_id, source, start, end, title=None):
    if not (0 <= start < end <= len(source)): raise ValueError('Invalid selection')
    selected = source[start:end]
    a, ca = line_column(source, start)
    b, cb = line_column(source, end)
    return TocEntry(document_id, (title or selected.strip())[:300], a, b, ca, cb, selected, source[max(0,start-40):min(len(source),end+40)])

def locate_entry(source, entry):
    """Return (line, column), or None on ambiguity; never silently jump to wrong text."""
    lines = source.split('\n')
    idx = entry.line_start - 1
    if 0 <= idx < len(lines) and lines[idx][entry.column_start:].startswith(entry.selected_text.split('\n')[0]):
        return entry.line_start, entry.column_start
    needle = entry.selected_text
    if not needle: return None
    matches = [m.start() for m in re.finditer(re.escape(needle), source)]
    if len(matches) == 1: return line_column(source, matches[0])
    return None
