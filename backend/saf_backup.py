"""Android Storage Access Framework helpers for database backups.

This module provides functions to export and import the application's
SQLite database using Android's Storage Access Framework (SAF). The
functions are designed to be robust and safe to import on non-Android
platforms; operations will raise :class:`RuntimeError` if the required
Android classes are unavailable.
"""

from __future__ import annotations

from pathlib import Path
import logging


try:  # pragma: no cover - jnius is only available on Android
    from jnius import autoclass, JavaException  # type: ignore
except Exception:  # pragma: no cover - allow import on non-Android
    autoclass = None  # type: ignore

    class JavaException(Exception):
        """Fallback Java exception when running off-device."""

# Request codes identifying export/import operations.
REQ_EXPORT = 1001
REQ_IMPORT = 1002

EXPORT_PATH: Path | None = None

try:  # pragma: no cover - Android-only classes
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Intent = autoclass("android.content.Intent")
    Activity = autoclass("android.app.Activity")
    HAVE_ANDROID = True
except Exception:  # pragma: no cover - running on non-Android platform
    PythonActivity = Intent = Activity = None  # type: ignore
    HAVE_ANDROID = False


def _require_android() -> None:
    """Raise ``RuntimeError`` if Android classes are unavailable."""

    if not HAVE_ANDROID:
        raise RuntimeError("Android APIs unavailable")


def start_export(db_path: Path) -> None:
    """Launch the system folder picker for database export.

    The user selects a destination directory and the database is written using
    an auto-generated filename.
    """

    global EXPORT_PATH
    EXPORT_PATH = db_path

    _require_android()
    act = PythonActivity.mActivity
    intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
    intent.addFlags(
        Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
    )
    act.startActivityForResult(intent, REQ_EXPORT)


def handle_export_result(request_code, result_code, data, on_success, on_error) -> bool:
    """Write ``EXPORT_PATH`` to the folder chosen in the picker.

    The filename is generated automatically. This function should be called
    from the application's global ``on_activity_result`` callback. If
    ``request_code`` does not match an export operation the function returns
    ``False``.
    """

    if (
        request_code != REQ_EXPORT
        or Activity is None
        or result_code != Activity.RESULT_OK
        or data is None
    ):
        return False
    try:
        _require_android()
        uri = data.getData()
        if uri is None:
            raise IOError("No URI returned")

        flags = data.getFlags() & (
            Intent.FLAG_GRANT_READ_URI_PERMISSION
            | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        )
        PythonActivity.mActivity.getContentResolver().takePersistableUriPermission(uri, flags)

        if EXPORT_PATH is None:
            raise IOError("No export source set")

        cr = PythonActivity.mActivity.getContentResolver()
        DocumentsContract = autoclass("android.provider.DocumentsContract")
        name = EXPORT_PATH.name
        mime = "application/json" if EXPORT_PATH.suffix == ".json" else "application/octet-stream"
        doc_uri = DocumentsContract.createDocument(cr, uri, mime, name)
        if doc_uri is None:
            raise IOError("Document creation failed")
        outstream = cr.openOutputStream(doc_uri, "w")
        try:
            with open(EXPORT_PATH, "rb") as f:
                buf = f.read()
            outstream.write(buf)
            outstream.flush()
        finally:
            outstream.close()

        saved_uri = doc_uri.toString()
        logging.info("Exported database to %s", saved_uri)
        on_success(f"Exported to {saved_uri}")
        try:
            Path(EXPORT_PATH).unlink()
        except Exception:
            pass
        EXPORT_PATH = None
        return True
    except JavaException:
        logging.exception("Export failed (Java)")
        on_error("Export failed: Android I/O error.")
        return True
    except Exception as exc:
        logging.exception("Export failed")
        on_error(f"Export failed: {exc}")
        return True


def start_import() -> None:
    """Launch the system file picker to select a database for import."""

    _require_android()
    act = PythonActivity.mActivity
    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("*/*")
    intent.addFlags(
        Intent.FLAG_GRANT_READ_URI_PERMISSION
        | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
    )
    act.startActivityForResult(intent, REQ_IMPORT)


def handle_import_result(
    request_code,
    result_code,
    data,
    dest_db_path: Path,
    validate_and_replace,
    on_success,
    on_error,
) -> bool:
    """Read bytes from the chosen URI and replace ``dest_db_path``.

    Bytes are streamed to a temporary file to avoid high memory usage. The
    ``validate_and_replace`` callable should perform all validation and swap
    in the new database. The temporary file is deleted regardless of success
    or failure.
    """

    if (
        request_code != REQ_IMPORT
        or Activity is None
        or result_code != Activity.RESULT_OK
        or data is None
    ):
        return False
    temp_path = dest_db_path.with_suffix(".incoming.tmp")
    try:
        _require_android()
        uri = data.getData()
        if uri is None:
            raise IOError("No URI returned")

        flags = data.getFlags() & (
            Intent.FLAG_GRANT_READ_URI_PERMISSION
            | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        )
        cr = PythonActivity.mActivity.getContentResolver()
        PythonActivity.mActivity.getContentResolver().takePersistableUriPermission(uri, flags)
        instream = cr.openInputStream(uri)
        dest_db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(temp_path, "wb") as f:
                while True:
                    chunk = instream.read(64 * 1024)
                    if chunk == -1:
                        break
                    if isinstance(chunk, int):
                        f.write(bytes([chunk]))
                    else:
                        f.write(chunk)
        finally:
            instream.close()

        validate_and_replace(temp_path)
        on_success("Import successful.")
        return True
    except JavaException:
        logging.exception("Import failed (Java)")
        on_error("Import failed: Android I/O error.")
        return True
    except Exception as exc:
        logging.exception("Import failed")
        on_error(f"Import failed: {exc}")
        return True
    finally:
        try:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
        except Exception:
            pass
