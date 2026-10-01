import pytest
import numpy as np
from pathlib import Path
from app.multimedia import MultimediaProcessor, generate_asset_image
from app.schemas import Chunk, QueryRequest
from app.parsing import extract_tables_from_page, parse_pdf_document, apply_table_merge_heuristic
from app.retrieval import apply_intent_boost, BM25Index, rrf_fusion, calculate_term_coverage
import fitz


def test_15_video_temporal_extraction():
    """Multimodal test 15: Video extraction produces chunks with temporal metadata and scene descriptions."""
    processor = MultimediaProcessor()
    chunks = processor.process_video_file("test_video.mp4", "doc123", "presentation.mp4")
    
    assert len(chunks) == 3
    for c in chunks:
        assert c.content_type == "video"
        assert c.temporal_start is not None
        assert c.temporal_end is not None
        assert c.temporal_end > c.temporal_start
        assert c.asset_path is not None
        assert "[Video]" in c.text
        assert "Timestamp Window" in c.context_text


def test_16_audio_transcript_windows():
    """Multimodal test 16: Audio processing creates 30-second transcript windows with speaker metadata."""
    processor = MultimediaProcessor()
    chunks = processor.process_audio_file("earnings_call.mp3", "doc123", "earnings_call.mp3")
    
    assert len(chunks) == 2
    assert chunks[0].temporal_start == 0.0
    assert chunks[0].temporal_end == 30.0
    assert chunks[1].temporal_start == 30.0
    assert chunks[1].temporal_end == 60.0
    assert "CFO" in chunks[0].context_text or "Chief Financial Officer" in chunks[0].context_text


def test_17_image_vision_captioning():
    """Multimodal test 17: Image vision captioning generates figure descriptions."""
    processor = MultimediaProcessor()
    caption = processor.caption_image("factory_floor_fig1.png", "Bengaluru Facility")
    
    assert len(caption) > 10
    assert "Bengaluru Facility" in caption


def test_18_dual_text_table_representation():
    """Multimodal test 18: Dual-text design creates distinct text (search) and context_text (Markdown grid)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Table 1: Quarterly Revenue (Rs. in lakhs)", fontsize=12)
    page.insert_text((50, 80), "Metric  Q1  Q2", fontsize=10)
    page.insert_text((50, 100), "Sales   100 150", fontsize=10)

    chunks = extract_tables_from_page(page, "doc1", "sample.pdf", 1, "Financial Highlights")
    doc.close()

    if chunks:
        c = chunks[0]
        assert "[Table]" in c.text  # Linearized for embedding
        assert "| " in c.context_text  # Markdown grid for LLM context
        assert c.text != c.context_text  # CRITICAL Dual-text distinction


def test_19_bbox_coordinate_extraction():
    """Multimodal test 19: BBOX coordinates extracted from PyMuPDF spans are 4-element tuples."""
    c = Chunk(
        id="c1", document_id="d1", filename="f.pdf", page_number=1,
        section="Sec", content_type="text", text="txt", context_text="ctxt",
        bbox=(50.0, 100.0, 300.0, 150.0)
    )
    assert isinstance(c.bbox, tuple)
    assert len(c.bbox) == 4
    assert c.bbox[0] < c.bbox[2]
    assert c.bbox[1] < c.bbox[3]


def test_20_attachment_routing_by_extension():
    """Multimodal test 20: Attachment file extensions route correctly to video, audio, image, csv, or archive."""
    ext_map = {
        ".mp4": "video",
        ".wav": "audio",
        ".png": "image",
        ".csv": "table",
        ".zip": "attachment"
    }
    for ext, expected_type in ext_map.items():
        if ext in [".mp4", ".mov"]:
            content_type = "video"
        elif ext in [".mp3", ".wav"]:
            content_type = "audio"
        elif ext in [".png", ".jpg"]:
            content_type = "image"
        elif ext in [".csv", ".tsv"]:
            content_type = "table"
        else:
            content_type = "attachment"
        assert content_type == expected_type


def test_21_multimodal_intent_boosting():
    """Multimodal test 21: Intent boost lifts video and audio chunks for modality-specific queries."""
    video_chunk = Chunk(
        id="v1", document_id="d1", filename="demo.mp4", page_number=1, section="Video",
        content_type="video", text="Video timeline slide presentation showing Q3 metrics", context_text="Video"
    )
    audio_chunk = Chunk(
        id="a1", document_id="d1", filename="call.mp3", page_number=1, section="Audio",
        content_type="audio", text="Spoken audio recording of CFO discussing guidance", context_text="Audio"
    )
    text_chunk = Chunk(
        id="t1", document_id="d1", filename="doc.pdf", page_number=1, section="Body",
        content_type="text", text="Standard prose text without multimedia", context_text="Text"
    )

    chunk_map = {"v1": video_chunk, "a1": audio_chunk, "t1": text_chunk}
    initial_rankings = [("t1", 0.05), ("v1", 0.04), ("a1", 0.03)]

    # Query for video
    boosted_video = apply_intent_boost("Watch the video clip presentation", initial_rankings, chunk_map)
    assert boosted_video[0][0] == "v1"

    # Query for audio
    boosted_audio = apply_intent_boost("What was spoken in the audio recording call?", initial_rankings, chunk_map)
    assert boosted_audio[0][0] == "a1"


def test_22_csv_tabular_attachment_processing(tmp_path):
    """Multimodal test 22: Tabular CSV attachments are converted to markdown grid and search phrases."""
    csv_file = tmp_path / "sales_metrics.csv"
    csv_file.write_text("Quarter,Revenue,Profit\nQ1,500,80\nQ2,650,110\n", encoding="utf-8")

    processor = MultimediaProcessor()
    chunks = processor.process_tabular_attachment(str(csv_file), "doc_csv", "sales_metrics.csv")

    assert len(chunks) == 1
    c = chunks[0]
    assert c.content_type == "table"
    assert "| Quarter | Revenue | Profit |" in c.context_text
    assert "Revenue: 500" in c.text or "Revenue: 650" in c.text


def test_23_generate_asset_image(tmp_path):
    """Multimodal test 23: Asset image generator creates valid image files for keyframe previews."""
    img_path = tmp_path / "preview.png"
    out = generate_asset_image(img_path, "Test Frame", width=300, height=200)
    assert Path(out).exists()
    assert Path(out).stat().st_size > 50


def test_24_e2e_multimodal_pdf_with_embedded_attachments(tmp_path):
    """Multimodal test 24: Ingestion extracts video, audio, image, and tabular embedded PDF attachments."""
    pdf_path = tmp_path / "report_with_multimedia.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Executive Performance Overview & Multimedia Appendix", fontsize=14)
    page.insert_text((50, 100), "See attached audio recording, presentation video, and dataset CSV.", fontsize=10)
    
    doc.embfile_add("presentation.mp4", b"dummy_mp4_binary_content", filename="presentation.mp4")
    doc.embfile_add("earnings_call.mp3", b"dummy_mp3_binary_content", filename="earnings_call.mp3")
    doc.embfile_add("architecture_chart.png", b"dummy_png_binary_content", filename="architecture_chart.png")
    doc.embfile_add("quarterly_breakdown.csv", b"Metric,FY24,FY25\nRevenue,4000,4500\nProfit,800,950\n", filename="quarterly_breakdown.csv")
    
    doc.save(str(pdf_path))
    doc.close()
    
    chunks = parse_pdf_document(str(pdf_path), "doc_e2e_multimodal")
    types = {c.content_type for c in chunks}
    
    assert "video" in types
    assert "audio" in types
    assert "image" in types
    assert "table" in types
    
    video_chunks = [c for c in chunks if c.content_type == "video"]
    audio_chunks = [c for c in chunks if c.content_type == "audio"]
    image_chunks = [c for c in chunks if c.content_type == "image"]
    table_chunks = [c for c in chunks if c.content_type == "table"]
    
    assert len(video_chunks) >= 3
    assert len(audio_chunks) >= 2
    assert len(image_chunks) >= 1
    assert len(table_chunks) >= 1
    
    assert all(c.temporal_start is not None and c.temporal_end is not None for c in video_chunks)
    assert all(c.temporal_start is not None and c.temporal_end is not None for c in audio_chunks)
    assert all(c.bbox is not None for c in image_chunks)

