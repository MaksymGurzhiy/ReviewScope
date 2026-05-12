"""Low-level ML model wrappers used by the NLP pipeline.

Each class lazy-loads its underlying HuggingFace model the first time it is
asked to do work, so importing this package is cheap.
"""
