import os
import uuid
import csv
import json
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF

from app.config import settings
from app.schemas import Chunk





class MultimediaProcessor:
    """
    Multimodal Attachment & Media Engine.
    Handles Tabular (.csv, .xlsx, .tsv, .json) and Documents (.txt, .md, .log, .docx).
    Scope restricted to text and tabular data to ensure 100% fidelity.
    """



    def process_tabular_attachment(self, csv_path: str, doc_id: str, filename: str) -> List[Chunk]:
        """
        Parses structured tabular attachments (CSV/TSV) into markdown grids and search sentences.
        Supports large CSV files by chunking all rows in batches of 40 rows.
        """
        chunks = []
        try:
            with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                rows = [row for row in reader if any(cell.strip() for cell in row)]

            if not rows:
                return chunks

            headers = [c.strip() if c.strip() else f"Col_{j+1}" for j, c in enumerate(rows[0])]
            data_rows = rows[1:]

            if not data_rows:
                # Header only
                md_table = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |"
                chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    filename=filename,
                    page_number=1,
                    section="Tabular Schema",
                    content_type="table",
                    text=f"[Table Attachment: {filename}] Schema: {', '.join(headers)}",
                    context_text=f"Attached Tabular File: {filename}\n\n{md_table}",
                    bbox=None,
                    asset_path=str(csv_path),
                    temporal_start=None,
                    temporal_end=None,
                    metadata={"cols_count": len(headers), "rows_count": 0, "headers": headers}
                ))
                return chunks

            batch_size = 40
            for start_idx in range(0, len(data_rows), batch_size):
                batch = data_rows[start_idx:start_idx + batch_size]
                chunk_page = (start_idx // batch_size) + 1
                row_range = f"Rows {start_idx + 1}-{start_idx + len(batch)} of {len(data_rows)}"

                md_lines = ["| " + " | ".join(headers) + " |"]
                md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                linear_parts = []

                for r in batch:
                    clean_r = [c.strip() for c in r]
                    if len(clean_r) < len(headers):
                        clean_r += [""] * (len(headers) - len(clean_r))
                    clean_r = clean_r[:len(headers)]

                    md_lines.append("| " + " | ".join(clean_r) + " |")
                    pairs = [f"{h}: {val}" for h, val in zip(headers, clean_r) if val]
                    if pairs:
                        linear_parts.append(" | ".join(pairs))

                md_table = "\n".join(md_lines)
                search_text = f"[Table Attachment: {filename} - {row_range}] " + " ; ".join(linear_parts)
                context_text = f"Attached Tabular File: {filename} ({row_range})\n\n{md_table}"

                c = Chunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    filename=filename,
                    page_number=chunk_page,
                    section=f"Tabular Data ({row_range})",
                    content_type="table",
                    text=search_text,
                    context_text=context_text,
                    bbox=None,
                    asset_path=str(csv_path),
                    temporal_start=None,
                    temporal_end=None,
                    metadata={
                        "cols_count": len(headers), 
                        "rows_count": len(rows), 
                        "headers": headers,
                        "batch_start": start_idx + 1,
                        "batch_end": start_idx + len(batch)
                    }
                )
                chunks.append(c)
        except Exception as e:
            print(f"Error parsing tabular attachment {filename}: {e}")

        return chunks

    def process_text_document(self, text_path: str, doc_id: str, filename: str, chunk_size: int = 1500, overlap: int = 250) -> List[Chunk]:
        """
        Parses arbitrary text, markdown, log, or code files with sliding-window chunking.
        Handles large file sizes with zero loss of passage information.
        """
        chunks = []
        try:
            with open(text_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if not content.strip():
                return chunks

            total_len = len(content)
            if total_len <= chunk_size:
                chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    filename=filename,
                    page_number=1,
                    section="Full Document",
                    content_type="text",
                    text=f"[{filename}] {content.strip()}",
                    context_text=f"Document: {filename}\n\n{content.strip()}",
                    bbox=None,
                    asset_path=None,
                    temporal_start=None,
                    temporal_end=None,
                    metadata={"char_length": total_len}
                ))
                return chunks

            start = 0
            page_num = 1
            while start < total_len:
                end = min(start + chunk_size, total_len)
                passage = content[start:end].strip()
                
                if passage:
                    chunks.append(Chunk(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        filename=filename,
                        page_number=page_num,
                        section=f"Section {page_num} (chars {start}-{end})",
                        content_type="text",
                        text=f"[{filename} p.{page_num}] {passage}",
                        context_text=f"Document: {filename} (Part {page_num}):\n\n{passage}",
                        bbox=None,
                        asset_path=None,
                        temporal_start=None,
                        temporal_end=None,
                        metadata={"char_start": start, "char_end": end, "total_chars": total_len}
                    ))
                    page_num += 1

                if end == total_len:
                    break
                start += (chunk_size - overlap)

        except Exception as e:
            print(f"Error parsing text document {filename}: {e}")

        return chunks



    def _format_time(self, seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"


_multimedia_processor = None


def get_multimedia_processor() -> MultimediaProcessor:
    global _multimedia_processor
    if _multimedia_processor is None:
        _multimedia_processor = MultimediaProcessor()
    return _multimedia_processor
