# E2E Test Infra: Project NPN Local-First Multimodal RAG

## Test Philosophy
- Opaque-box, requirement-driven testing derived strictly from `ORIGINAL_REQUEST.md` and `ARCHITECTURE.md`.
- Systematic 4-tier methodology:
  - **Tier 1**: Feature Coverage (Equivalence Class Representatives, isolated feature testing, >=5 test cases per feature).
  - **Tier 2**: Boundary & Corner Cases (Limits, empty files, huge inputs, missing sections, corrupted headers, boundary digit ratios).
  - **Tier 3**: Cross-Feature Combinations (Pairwise interactions: tables + multimedia, video + audio + vector search, BM25 + intent boost, relevance gate + LLM verification).
  - **Tier 4**: Real-World Application Scenarios (94-page annual reports, financial 10-K statements, multi-document cross-referencing, multi-turn Q&A).
  - **Tier 5**: Adversarial Coverage Hardening (White-box edge case testing, race condition tests, failure injection, zero-tolerance integrity audit).

## Feature Inventory
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 |
|---|---------|--------|:------:|:------:|:------:|
| 1 | Font Profiling & Heading Detection | ARCHITECTURE §3 | 5 | 5 | ✓ |
| 2 | Table Triage Filter | ARCHITECTURE §3.1 | 5 | 5 | ✓ |
| 3 | Table Triple-Representation | ARCHITECTURE §3.2 | 5 | 5 | ✓ |
| 4 | Dual-Text Chunk Abstraction | ARCHITECTURE §2.3 | 5 | 5 | ✓ |
| 5 | Video Attachment Processing | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ |
| 6 | Audio Attachment Processing | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ |
| 7 | Image & Figure Captioning | ARCHITECTURE §3, R1 | 5 | 5 | ✓ |
| 8 | Bounding Box Coordinate Extraction | ARCHITECTURE §2.3, R1 | 5 | 5 | ✓ |
| 9 | SQLite float32 BLOB Vector Storage | ARCHITECTURE §2.4 | 5 | 5 | ✓ |
| 10 | Exact Dense Vector Search | ARCHITECTURE §4 | 5 | 5 | ✓ |
| 11 | In-Memory BM25 Sparse Index | ARCHITECTURE §4, §1.1 | 5 | 5 | ✓ |
| 12 | Reciprocal Rank Fusion (RRF) | ARCHITECTURE §4.2 | 5 | 5 | ✓ |
| 13 | Cross-Modal Intent Boosting | ARCHITECTURE §4, R2 | 5 | 5 | ✓ |
| 14 | Dual Relevance Gating | ARCHITECTURE §4.3 | 5 | 5 | ✓ |
| 15 | Document Ingestion Pipeline | ARCHITECTURE §3 | 5 | 5 | ✓ |
| 16 | Integrity Gate Verification | ARCHITECTURE §3, §5.1 | 5 | 5 | ✓ |
| 17 | Grounded Multi-Source Generation | ARCHITECTURE §4, R3 | 5 | 5 | ✓ |
| 18 | Claim Verification Engine | ARCHITECTURE §4, R3 | 5 | 5 | ✓ |
| 19 | REST API Endpoints | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ |
| 20 | Web Upload Dropzone & Progress | ORIGINAL_REQUEST R4 | 5 | 5 | ✓ |
| 21 | Interactive Chat Interface | ORIGINAL_REQUEST R4 | 5 | 5 | ✓ |
| 22 | Citation Drawer & Modal Preview | ORIGINAL_REQUEST R4 | 5 | 5 | ✓ |
| 23 | Multimodal Media Cards & Timestamps | ORIGINAL_REQUEST R4 | 5 | 5 | ✓ |
| 24 | E2E Test Suite Execution & Passing | ORIGINAL_REQUEST R5 | 5 | 5 | ✓ |

## Test Architecture
- Test Runner: `pytest -v tests/`
- Test Case Files:
  - `tests/test_unit.py`: Algorithmic & unit tests
  - `tests/test_integration.py`: End-to-end component integration tests
  - `tests/test_multimodal.py`: Multimodal attachments, temporal windows, and vision tests
  - `tests/test_security_and_contracts.py`: Security, injection defense, and API contract tests
  - `tests/chaos/`: Chaos & fault tolerance tests
- Pass/Fail Criteria: 100% test pass rate with exit code 0.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | 94-Page Annual Report Ingestion & Multi-Year Revenue Query | F1, F2, F3, F4, F10, F11, F12, F13, F15, F16, F17, F18 | High |
| 2 | Financial Statement "Note 17" Bare Identifier Exact Match Query | F4, F11, F12, F14, F17, F18, F19 | High |
| 3 | Multimodal Earnings Call Video & Audio Attachment Synthesis | F5, F6, F7, F8, F10, F12, F13, F17, F22, F23 | High |
| 4 | Off-Topic Question Triggering Dual-Threshold Relevance Refusal | F10, F11, F14, F17, F19 | Medium |
| 5 | Cross-Page Table Financial Metrics Extraction & Verification | F1, F3, F4, F8, F10, F12, F13, F17, F18 | High |

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature
- Tier 2: ≥5 test cases per feature (where boundaries exist)
- Tier 3: Pairwise coverage of major feature interactions
- Tier 4: ≥5 realistic application scenarios
- Tier 5: Adversarial hardening and coverage validation
