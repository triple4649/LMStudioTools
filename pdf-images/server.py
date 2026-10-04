from pathlib import Path
from tempfile import mkdtemp

import pymupdf
from fastmcp import FastMCP

mcp = FastMCP("PDF Image Extractor")
ROOT = (Path.home() / "LMStudioFiles").resolve()


@mcp.tool
def extract_pdf_images(pdf_path: str) -> dict:
    """LMStudioFiles内のPDFから埋め込み画像を抽出する。
    pdf_pathには絶対パス、またはLMStudioFilesからの相対パスを指定。
    スキャン内の写真の自動切り抜きやベクター図の抽出は行わない。
    """
    source = Path(pdf_path).expanduser()
    if not source.is_absolute():
        source = ROOT / source
    source = source.resolve()

    if not source.is_relative_to(ROOT):
        raise ValueError("PDFはLMStudioFiles内に置いてください。")
    if not source.is_file():
        raise ValueError("指定したPDFが見つかりません。")

    saved = []
    seen = set()

    with pymupdf.open(source) as doc:
        if not doc.is_pdf:
            raise ValueError("PDFファイルを指定してください。")
        if doc.needs_pass:
            raise ValueError("パスワード付きPDFには未対応です。")

        output = Path(mkdtemp(prefix="pdf-images-", dir=ROOT))

        for page_no, page in enumerate(doc, start=1):
            for item in page.get_images(full=True):
                xref, smask = item[:2]
                if xref in seen:
                    continue
                seen.add(xref)

                data = doc.extract_image(xref)
                if not data:
                    continue

                name = f"page-{page_no:03d}_image-{xref}"

                if smask:
                    # 分離されている透明度情報を合成する
                    pix = pymupdf.Pixmap(data["image"])
                    if pix.colorspace and pix.colorspace.n > 3:
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    if pix.alpha:
                        pix = pymupdf.Pixmap(pix, 0)
                    mask = pymupdf.Pixmap(doc, smask)
                    result = pymupdf.Pixmap(pix, mask)
                    target = output / f"{name}.png"
                    result.save(str(target))
                else:
                    target = output / f"{name}.{data['ext']}"
                    target.write_bytes(data["image"])

                saved.append(target.name)

    return {
        "count": len(saved),
        "output_directory": str(output),
        "first_20_files": saved[:20],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")