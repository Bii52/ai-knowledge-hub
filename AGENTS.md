# AI KNOWLEDGE HUB - AGENT GUIDELINES & WORKSPACE RULES

This document serves as the primary system instruction and operational guideline for all AI Agents working within the **AI Knowledge Hub** repository.

---

## 1. Project Overview & Architecture

**AI Knowledge Hub** is an AI-powered Knowledge Management & SaaS Platform utilizing Retrieval-Augmented Generation (RAG).

### Monorepo Structure
```text
AI-KNOWLEDGE-HUB/
├── apps/
│   ├── web/            # Frontend: Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui
│   ├── api/            # Backend: NestJS 12 (ESM/NodeNext), Prisma ORM, BullMQ, Redis
│   └── ai-service/     # AI Core: Python 3.11+, FastAPI, Text Extractors, RAG Pipeline, Embeddings
├── infrastructure/     # Docker Compose, PostgreSQL + pgvector, Redis, MinIO (Object Storage)
├── docs/               # System architecture, PRD, database design, API specs
└── AGENTS.md           # Workspace rules & Agent behavior guidelines
```

---

## 2. Core Business Workflows

### 2.1. Document Ingestion Pipeline
1. **Upload**: User uploads file (`PDF`, `DOCX`, `TXT`) via `apps/web`.
2. **Storage**: `apps/api` saves file to Object Storage (MinIO / S3 / Cloudflare R2).
3. **Queue**: Task is dispatched to Redis via BullMQ (`status: Pending -> Processing`).
4. **Extraction & Chunking**: `apps/ai-service` extracts text, cleans content, and splits into semantic chunks with metadata (page number, chunk position).
5. **Embeddings**: Vector embeddings generated and persisted into PostgreSQL with `pgvector` extension.
6. **Completion**: Update document status to `Completed` (or `Failed` with error log).

### 2.2. RAG Query & Chat Workflow
1. User asks question in a conversation context within a specific Workspace.
2. Embed the user question via Embedding model.
3. Perform **Cosine / L2 Similarity Search** on `document_chunks` table.
4. **Strict Isolation**: Query MUST be strictly scoped by `workspace_id` and authorized `document_id`s.
5. Augment prompt with retrieved chunks + citation metadata.
6. LLM generates streaming response with exact references (filename, page number, excerpt).

---

## 3. Strict Security & Data Isolation Rules

1. **Pre-Retrieval Workspace Scoping**:
   - **MANDATORY**: Always filter by `workspace_id` and verified user permissions **BEFORE** performing vector similarity search.
   - NEVER retrieve vectors globally and filter in-memory afterwards.
   - NEVER inject chunks from one Workspace into another Workspace's LLM context.
2. **Secrets & Credentials**:
   - AI API keys (OpenAI, Gemini, Cohere, etc.), database passwords, and JWT secrets MUST remain in environment variables (`.env`).
   - Never expose API keys or internal service credentials to `apps/web` or commit them to Git.
3. **File Access & Upload Safety**:
   - Validate file MIME types and size limits before saving to storage.
   - Do not allow unauthenticated public URLs to access private documents.

---

## 4. Technology Stack & Coding Standards

### 4.1. Backend (`apps/api` - NestJS 12)
- **Module Format**: NodeNext ECMAScript Modules (`"type": "module"`). Always use `.js` extension for local relative imports in TypeScript (e.g. `import { Service } from './service.js'`).
- **Architecture**: Modular structure (`Controller -> Service -> Repository/Prisma`).
- **Validation**: Use DTOs with `class-validator` and `class-transformer`.
- **Database**: Prisma ORM with strict migrations. Do not use raw unchecked SQL queries for business logic unless required for `pgvector` operators.
- **Testing**: Vitest (`npm run test`) and Oxlint (`npm run lint`).

### 4.2. Frontend (`apps/web` - Next.js)
- **Framework**: Next.js App Router (`src/app/`), React 19.
- **Components**: Default to React Server Components (RSC). Use `'use client'` strictly when client-side hooks, state, or DOM interactions are needed.
- **Styling**: Tailwind CSS with consistent UI component library (`shadcn/ui` / Radix primitives).
- **Type Safety**: Strictly typed TypeScript props and API responses. No arbitrary `any`.

### 4.3. AI Service (`apps/ai-service` - Python / FastAPI)
- **Runtime**: Python 3.11+.
- **Framework**: FastAPI with Pydantic v2 schemas for all request/response models.
- **Code Style**: Async/await endpoints, PEP 8 compliance, type annotations everywhere.
- **RAG Stack**: LangChain / LlamaIndex / native SDKs with chunking strategies respecting document structure.

---

## 5. Agent Approval & Change Management Policy

### 5.1. Mandatory Approval Workflow

The Agent MUST follow this workflow for every development task:

**Phase 1 - Analyze**
- Understand the user's request.
- Inspect relevant source code and project structure.
- Identify dependencies and potential risks.
- Do not modify any files.

**Phase 2 - Propose**
Present a development proposal containing:
- Problem description.
- Root cause (if applicable).
- Proposed solution.
- Files to be created, modified, or deleted.
- Dependencies or packages required.
- Database or API changes.
- Testing strategy.
- Potential risks.

**Phase 3 - Wait for Approval**
- STOP and wait for explicit user approval.
- Do not edit, create, or delete files.
- Do not install packages.
- Do not execute commands that modify project state.
- Silence or ambiguous responses are NOT approval.

**Phase 4 - Implement**
Only after explicit approval:
- Implement the approved plan.
- Do not expand the scope without asking.
- Preserve unrelated code.
- Report unexpected issues before making additional changes.

**Phase 5 - Verify**
- Inspect the Git diff.
- Run relevant tests and lint commands when approved.
- Report actual results.
- Never claim tests passed if they were not executed.

**Phase 6 - Final Report**
Summarize:
- Files changed.
- Changes implemented.
- Tests executed and results.
- Remaining issues.
- Recommended next steps.

### 5.2. Git Safety

- Never commit or push without explicit approval.
- Never overwrite uncommitted user changes.
- Inspect Git status before implementation.
- Recommend a separate feature branch for significant changes.
- Never run destructive Git commands without explicit approval.

### 5.3. Approval Principle

The user is the final decision-maker.

`ANALYZE -> PROPOSE -> WAIT FOR APPROVAL -> IMPLEMENT -> VERIFY -> REPORT`

---

## 6. Agent Operational Guidelines

When acting as an AI developer in this codebase:
1. **Preserve Integrity**: Do not overwrite or modify existing unrelated code or delete comments unless requested.
2. **Verification First**: After writing or modifying code in `apps/api` or `apps/web`, always run linter and test commands (`npm run lint`, `npm run test`) to verify there are no syntax or type breakages.
3. **No Phantom Packages**: Never import or install unverified packages. Check `package.json` or `pyproject.toml` before referencing third-party modules.
4. **Git Discipline**: Ensure temporary files, build artifacts (`dist/`, `.next/`, `__pycache__/`), and `node_modules/` remain ignored in `.gitignore`.


