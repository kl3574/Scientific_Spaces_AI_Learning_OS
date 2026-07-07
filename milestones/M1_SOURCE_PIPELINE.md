# Milestone 1 - Scientific Spaces Source Pipeline

## Goal

建立可靠知识来源。

## Scope

只处理：

- Scientific Spaces 博客

## Tasks

### TASK-M1-001 Crawler

实现：

- 文章列表发现。

要求：

- 支持分页。
- 支持缓存。
- 支持异常重试。

### TASK-M1-002 Parser

解析：

- 标题
- 正文
- 日期
- 分类
- 图片
- 引用

### TASK-M1-003 Markdown Converter

要求：

- 保持标题结构。
- 保持公式。
- 保持图片引用。

### TASK-M1-004 Storage

保存：

- `Article`

字段：

- `id`
- `title`
- `url`
- `content`
- `metadata`

### TASK-M1-005 Validation

随机 10 篇：

- 检查标题 100%。
- 检查正文 95%。
- 检查图片可显示。

## Acceptance

运行：

- `sync`

成功导入文章。
