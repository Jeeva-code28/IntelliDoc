import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import settings
from app.schemas import DocumentStatusResponse, MessageSchema, Chunk


def slugify(text: str, max_len: int = 30) -> str:
    """Creates a filesystem-safe slug from a conversation title."""
    clean = re.sub(r'[^a-zA-Z0-9_\- ]+', '', text or "conversation").strip().lower()
    clean = re.sub(r'\s+', '_', clean)
    return clean[:max_len] or "archive"


class HistoryManager:
    """
    Autonomous Manager for Conversation Archiving & History Generation.
    When a conversation is deleted, compiles all user prompts, assistant replies,
    verification badges, and full multimodal citations into structured Markdown (.md)
    and JSON (.json) files, persisting them to the data/history storage directory.
    """

    def __init__(self, history_dir: Optional[Path] = None):
        self.history_dir = history_dir or settings.HISTORY_DIR
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def generate_archive(
        self,
        conv_id: str,
        title: str,
        created_at: str,
        documents: List[DocumentStatusResponse],
        messages: List[MessageSchema],
        chunks_map: Dict[str, Chunk]
    ) -> Dict[str, Any]:
        """
        Compiles the conversation into Markdown and JSON export files and saves them to disk.
        Returns the history archive metadata dictionary.
        """
        archive_id = str(uuid.uuid4())
        deleted_at = datetime.now(timezone.utc).isoformat()
        clean_title = title or "Archived Conversation"
        slug = slugify(clean_title)

        # 1. Structure transcript turns
        structured_transcript = []
        turn_number = 1

        for msg in messages:
            msg_dict = {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at or deleted_at,
                "sources": []
            }

            if msg.role == "assistant" and msg.sources:
                for idx, src_id in enumerate(msg.sources, start=1):
                    chunk = chunks_map.get(src_id)
                    if chunk:
                        msg_dict["sources"].append({
                            "source_tag": f"[S{idx}]",
                            "chunk_id": chunk.id,
                            "filename": chunk.filename,
                            "page_number": chunk.page_number,
                            "section": chunk.section or "General",
                            "content_type": chunk.content_type,
                            "snippet": chunk.context_text,
                            "bbox": list(chunk.bbox) if chunk.bbox else None,
                            "temporal_start": chunk.temporal_start,
                            "temporal_end": chunk.temporal_end,
                            "asset_path": chunk.asset_path
                        })
                    else:
                        msg_dict["sources"].append({
                            "source_tag": f"[S{idx}]",
                            "chunk_id": src_id,
                            "filename": "Unknown",
                            "page_number": 0,
                            "section": "General",
                            "content_type": "text",
                            "snippet": "Source details archived."
                        })

            structured_transcript.append(msg_dict)

        # 2. Build Markdown content
        md_lines = [
            f"# 📜 Conversation Archive: {clean_title}",
            "",
            f"> **Archive ID**: `{archive_id}`  ",
            f"> **Original Conversation ID**: `{conv_id}`  ",
            f"> **Created At**: {created_at or 'N/A'}  ",
            f"> **Deleted & Archived At**: {deleted_at}  ",
            f"> **Total Messages**: {len(messages)} | **Attached Documents**: {len(documents)}  ",
            "",
            "---",
            "",
            "## 📁 Attached Knowledge Base Documents",
            ""
        ]

        if not documents:
            md_lines.append("*No documents were attached to this conversation.*")
            md_lines.append("")
        else:
            for d in documents:
                fn = getattr(d, "filename", "Unknown")
                st = getattr(d, "status", "ready")
                ft = getattr(d, "file_type", "document")
                pc = getattr(d, "page_count", 1)
                md_lines.append(f"- **{fn}** (Status: `{st}`, Type: `{ft}`, Pages: {pc})")
            md_lines.append("")

        md_lines.extend([
            "---",
            "",
            "## 💬 Conversation Transcript & Multimodal Evidence Citations",
            ""
        ])

        if not messages:
            md_lines.append("*No messages recorded in this conversation.*")
            md_lines.append("")
        else:
            turn_idx = 1
            for msg in structured_transcript:
                if msg["role"] == "user":
                    md_lines.extend([
                        f"### 👤 [Prompt #{turn_idx}]",
                        f"*Timestamp: {msg['created_at']}*",
                        "",
                        f"> {msg['content'].replace(chr(10), chr(10) + '> ')}",
                        ""
                    ])
                else:
                    md_lines.extend([
                        f"### 🤖 [Assistant Reply #{turn_idx}]",
                        f"*Timestamp: {msg['created_at']}*",
                        "",
                        msg["content"],
                        ""
                    ])

                    if msg["sources"]:
                        md_lines.append("#### 📌 Citations & Multimodal Evidence Proofs:")
                        for src in msg["sources"]:
                            s_tag = src.get("source_tag", "[SOURCE]")
                            fn = src.get("filename", "Unknown")
                            pg = src.get("page_number", 1)
                            sec = src.get("section", "General")
                            ctype = src.get("content_type", "text").upper()
                            snip = src.get("snippet", "").strip()

                            coord_info = []
                            if src.get("bbox"):
                                coord_info.append(f"Spatial BBox: `{src['bbox']}`")
                            if src.get("temporal_start") is not None:
                                coord_info.append(f"Video/Audio Timestamp: `{src['temporal_start']}s - {src['temporal_end']}s`")
                            coord_str = f" | {', '.join(coord_info)}" if coord_info else ""

                            md_lines.extend([
                                f"- **{s_tag} {fn}** (Page {pg}, Section: {sec}, Modality: `{ctype}`){coord_str}",
                                "  - **Evidence Context Snippet**:",
                                "    ```text",
                                f"    {snip}",
                                "    ```"
                            ])
                        md_lines.append("")
                    turn_idx += 1

        md_text = "\n".join(md_lines)

        # 3. Build JSON payload
        doc_list = [
            {
                "id": getattr(d, "id", str(uuid.uuid4())),
                "filename": getattr(d, "filename", "Unknown"),
                "file_type": getattr(d, "file_type", "document"),
                "page_count": getattr(d, "page_count", 1),
                "status": getattr(d, "status", "ready"),
                "created_at": getattr(d, "created_at", "")
            }
            for d in documents
        ]

        json_payload = {
            "archive_id": archive_id,
            "conversation_id": conv_id,
            "title": clean_title,
            "created_at": created_at,
            "deleted_at": deleted_at,
            "documents": doc_list,
            "messages": structured_transcript,
            "summary": {
                "total_messages": len(messages),
                "total_documents": len(documents),
                "user_prompts_count": sum(1 for m in messages if m.role == "user"),
                "assistant_replies_count": sum(1 for m in messages if m.role == "assistant")
            }
        }

        # 4. Save to files
        md_filename = f"{archive_id}_{slug}.md"
        json_filename = f"{archive_id}_{slug}.json"
        md_path = self.history_dir / md_filename
        json_path = self.history_dir / json_filename

        md_path.write_text(md_text, encoding="utf-8")
        json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        # First prompt preview for summary
        first_prompt = next((m.content for m in messages if m.role == "user"), "Empty conversation")
        summary_preview = (first_prompt[:120] + "...") if len(first_prompt) > 120 else first_prompt

        return {
            "id": archive_id,
            "conversation_id": conv_id,
            "title": clean_title,
            "created_at": created_at or deleted_at,
            "deleted_at": deleted_at,
            "message_count": len(messages),
            "document_count": len(documents),
            "md_file_path": str(md_path),
            "json_file_path": str(json_path),
            "transcript_summary": summary_preview
        }


_history_manager = None


def get_history_manager() -> HistoryManager:
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager
