def serialize_pdf_textdata(obj):
    return {
        'id': str(obj.id),
        'filename': obj.filename,
        'created_at': obj.created_at.isoformat() if obj.created_at else None,
        'text_file_path': obj.text_file_path,
        'is_processed': obj.is_processed,
        'file_hash': obj.file_hash,
        'content_hash': obj.content_hash,
        'file_size': obj.file_size,
        'original_filename': obj.original_filename,
        # Do not include extracted_text unless needed
    } 