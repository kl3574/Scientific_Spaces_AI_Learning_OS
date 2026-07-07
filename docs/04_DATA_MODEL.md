# 04 Data Model

## Purpose

This document records conceptual data entities for future implementation.

## Conceptual Entities

- `Article`
- `Paper`
- `Concept`
- `Theory`
- `Experiment`
- `LearningState`
- `Bookmark`
- `Conversation`
- `Citation`

## Initial Article Shape

- `id`
- `title`
- `url`
- `content`
- `metadata`

## Knowledge Relationships

- `explained_by`
- `supported_by`
- `verified_by`

## Bootstrap Constraint

This is not a database schema. No persistence layer is implemented in Bootstrap.
