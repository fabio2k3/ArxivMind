from backend.crawler.chunker import clean_text, make_chunks


def test_clean_text_collapses_blank_lines_and_page_numbers():
    raw = "Párrafo uno.\n\n\n\n12\n\nPárrafo dos.   con   espacios  extra."
    cleaned = clean_text(raw)
    assert "\n\n\n" not in cleaned
    assert "\n12\n" not in cleaned
    assert "  " not in cleaned


def test_make_chunks_respects_paragraph_boundaries():
    text = (
        "Esta es la primera oración del primer párrafo. "
        "Esta es la segunda oración del primer párrafo.\n\n"
        "Esta es la primera oración del segundo párrafo. "
        "Esta es la segunda oración del segundo párrafo."
    )
    chunks = make_chunks(text, chunk_size=10_000, min_chunk_chars=10)
    # con chunk_size enorme, cada párrafo debería terminar en su propio chunk
    assert len(chunks) == 2
    assert "primer párrafo" in chunks[0]
    assert "segundo párrafo" in chunks[1]


def test_make_chunks_applies_overlap_between_consecutive_chunks():
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]
    sentences = [f"This sentence contains the word {w} today." for w in words]
    text = " ".join(sentences)

    chunks = make_chunks(text, chunk_size=180, overlap_sentences=2, min_chunk_chars=10, min_sent_chars=5)

    assert len(chunks) >= 2
    # al menos una oración (palabra marcador) debe repetirse en dos chunks
    # consecutivos — eso es el overlap funcionando.
    shared_words = [w for w in words if sum(w in c for c in chunks) >= 2]
    assert shared_words, "se esperaba overlap: ninguna oración se repite entre chunks"


def test_make_chunks_discards_too_short_fragments():
    chunks = make_chunks("Corto.", chunk_size=1000, min_chunk_chars=100)
    assert chunks == []


def test_make_chunks_does_not_split_on_abbreviations():
    text = "El modelo de Vaswani et al. propone self-attention. Ver Fig. 3 para más detalles."
    chunks = make_chunks(text, chunk_size=10_000, min_chunk_chars=10)
    assert len(chunks) == 1
    assert "et al." in chunks[0]
    assert "Fig. 3" in chunks[0]
