"""Validate a user-supplied disease master ZIP without extracting paths."""
import hashlib
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from .disease_master import MASTER_FILENAME_PATTERN


def read_disease_archive(path: Path) -> tuple[str, bytes, str]:
    """Return one full disease-master member, its bytes and archive fingerprint."""
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("master_archive_too_large")
    with ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > 100:
            raise ValueError("master_archive_too_many_members")
        selected = []
        for member in members:
            name = PurePosixPath(member.filename.replace("\\", "/"))
            if name.is_absolute() or ".." in name.parts or ":" in member.filename:
                raise ValueError("master_archive_unsafe_path")
            if member.file_size > 64 * 1024 * 1024:
                raise ValueError("master_archive_member_too_large")
            if not member.is_dir() and MASTER_FILENAME_PATTERN.fullmatch(name.name):
                selected.append(member)
        if len(selected) != 1:
            raise ValueError("master_archive_requires_one_full_disease_master")
        member = selected[0]
        data = archive.read(member)
    return PurePosixPath(member.filename.replace("\\", "/")).name, data, hashlib.sha256(path.read_bytes()).hexdigest()
