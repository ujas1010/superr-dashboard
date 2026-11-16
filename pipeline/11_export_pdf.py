"""Phase 11 - Clean the PPTX zip and export the deck to PDF with PowerPoint (Windows).

Output: submission/SupeRR_Selector_R1_Submission.pdf (+ slide PNGs in outputs/deck_preview with --preview)
"""
import shutil
import sys
import zipfile

import config as C

PPTX = C.SUBMISSION / "SupeRR_Selector_R1_Submission.pptx"
PDF = C.SUBMISSION / "SupeRR_Selector_R1_Submission.pdf"


def strip_folder_entries(path):
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if not item.filename.endswith("/"):
                zout.writestr(item, zin.read(item.filename))
    shutil.move(tmp, path)


def export_pdf():
    import win32com.client
    app = win32com.client.Dispatch("PowerPoint.Application")
    pres = app.Presentations.Open(str(PPTX), ReadOnly=True, Untitled=False, WithWindow=False)
    try:
        pres.SaveAs(str(PDF), 32)  # 32 = ppSaveAsPDF
    finally:
        pres.Close()


def preview():
    import fitz
    out = C.OUT / "deck_preview"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    for i, page in enumerate(fitz.open(PDF), 1):
        page.get_pixmap(dpi=80).save(out / f"slide-{i:02d}.png")


if __name__ == "__main__":
    strip_folder_entries(PPTX)
    export_pdf()
    if "--preview" in sys.argv:
        preview()
    print("PDF written:", PDF)
