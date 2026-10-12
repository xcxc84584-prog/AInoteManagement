"""Lossless Markdown source model for the BV-Text v6 migration."""
from dataclasses import dataclass, field
from hashlib import sha256
from uuid import uuid4
import re

# Legacy markers are ordinary text in v6.1; TOC lives in IndexedDB.


def source_digest(source: str) -> str:
    return sha256(source.encode('utf-8')).hexdigest()


def extract_toc(source: str):
    """Legacy compatibility: no longer derives TOC from Markdown."""
    return []


@dataclass
class Document:
    name: str
    source: str = ''
    id: str = field(default_factory=lambda: str(uuid4()))
    kind: str = 'COMPOSITE'
    revision: int = 0
    schema_version: int = 6

    def update(self, source: str):
        if source != self.source:
            self.source = source
            self.revision += 1
        return self

    @property
    def toc(self):
        return extract_toc(self.source)

    @property
    def digest(self):
        return source_digest(self.source)


def split_document(document: Document, offset: int):
    """Split only at line boundaries; no normalization of Markdown or TeX."""
    if not (0 < offset < len(document.source)) or document.source[offset - 1] != '\n':
        raise ValueError('Split offset must start a line and leave both documents nonempty')
    return (Document(name=document.name + '-1', source=document.source[:offset]),
            Document(name=document.name + '-2', source=document.source[offset:]))
