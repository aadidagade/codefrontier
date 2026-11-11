from datetime import datetime, timezone


def utc_now() -> datetime:
    """Returns current datetime in UTC timezone."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Returns ISO 8601 formatted string of current UTC datetime."""
    return datetime.now(timezone.utc).isoformat()


def format_file_size(size_in_bytes: int) -> str:
    """Formats file size into human-readable string (KB, MB, GB)."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"
