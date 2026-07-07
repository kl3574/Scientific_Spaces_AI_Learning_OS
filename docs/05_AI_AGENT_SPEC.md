# 05 AI Agent Spec

## Purpose

Define expected AI behavior for future assistant and tutor capabilities.

## Agent Responsibilities

- Explain concepts with source grounding.
- Derive mathematical content when requested.
- Ask quiz questions to check understanding.
- Explore related papers.
- Cite article title, URL, and section when answering from indexed content.

## Tutor Modes

- Explain
- Derive
- Quiz
- Research

## Grounding Requirement

Answers that depend on source content must include citations.

## Bootstrap Constraint

No prompts, model calls, providers, or agent runtime are implemented in Bootstrap.
