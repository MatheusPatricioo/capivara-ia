"""Evals: measure the capybara with fixed cases and a real model, instead of by hand.

Unlike the tests (brain/tests), evals call the real Ollama models, so they never run in
pytest or CI. Run them with: python -m src.run_evals
"""
