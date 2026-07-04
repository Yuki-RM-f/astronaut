from zipfile import ZipFile

from app.services.material_extractors import extract_text_from_material_path


def test_extracts_docx_text_from_word_document_xml(tmp_path):
    docx_path = tmp_path / "memory.docx"
    document_xml = """
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p><w:r><w:t>外婆喜欢包馄饨。</w:t></w:r></w:p>
        <w:p><w:r><w:t>她常说慢慢来。</w:t></w:r></w:p>
      </w:body>
    </w:document>
    """
    with ZipFile(docx_path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)

    extracted = extract_text_from_material_path(
        docx_path,
        file_name="memory.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert "外婆喜欢包馄饨" in extracted.text
    assert "她常说慢慢来" in extracted.text
    assert extracted.metadata["extractor"] == "docx"
    assert extracted.metadata["source_location"] == "text:memory.docx"


def test_extracts_pdf_text_without_ocr(tmp_path):
    pdf_path = tmp_path / "memory.pdf"
    pdf_path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 74>>stream\n"
        b"BT /F1 18 Tf 50 100 Td (Grandmother liked warm soup.) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n0000000241 00000 n \n"
        b"0000000365 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n433\n%%EOF\n"
    )

    extracted = extract_text_from_material_path(
        pdf_path,
        file_name="memory.pdf",
        mime_type="application/pdf",
    )

    assert "Grandmother liked warm soup" in extracted.text
    assert str(extracted.metadata["extractor"]).startswith("pdf")
    assert "OCR" not in str(extracted.metadata)


def test_extracts_doc_best_effort_text_when_external_tools_missing(tmp_path, monkeypatch):
    doc_path = tmp_path / "memory.doc"
    doc_path.write_text("Grandmother said take your time.", encoding="utf-8")
    monkeypatch.setattr("app.services.material_extractors.shutil.which", lambda _: None)

    extracted = extract_text_from_material_path(
        doc_path,
        file_name="memory.doc",
        mime_type="application/msword",
    )

    assert "Grandmother said take your time" in extracted.text
    assert extracted.metadata["extractor"] == "doc_best_effort"
    assert "OCR" not in str(extracted.metadata)
