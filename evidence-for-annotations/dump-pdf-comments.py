import os
import popplerqt5
import PyQt5
import re


PDF_DIR = "highlighted-pdfs/"


def main(filepath):
    doc = popplerqt5.Poppler.Document.load(filepath)
    total_annotations = 0
    image_count = 0
    for i in range(doc.numPages()):
        #print("========= PAGE {} =========".format(i+1))
        page = doc.page(i)
        annotations = page.annotations()
        (pwidth, pheight) = (page.pageSize().width(), page.pageSize().height())
        if len(annotations) > 0:
            for annotation in annotations:
                if  isinstance(annotation, popplerqt5.Poppler.Annotation):
                    total_annotations += 1
                    if(isinstance(annotation, popplerqt5.Poppler.HighlightAnnotation)):
                        quads = annotation.highlightQuads()
                        txt = ""
                        for quad in quads:
                            rect = (quad.points[0].x() * pwidth,
                                    quad.points[0].y() * pheight,
                                    quad.points[2].x() * pwidth,
                                    quad.points[2].y() * pheight)
                            bdy = PyQt5.QtCore.QRectF()
                            bdy.setCoords(*rect)
                            txt = txt + str(page.text(bdy)) + ' '

                        print("========= TEXT HIGHLIGHT =========")
                        NEWLINE_RE = re.compile("\n")
                        print(f"pg{i + 1} - {re.sub(NEWLINE_RE, ',', annotation.contents())} ({annotation.author()})")
                        print(txt)
                    elif isinstance(annotation, popplerqt5.Poppler.TextAnnotation):
                        print("========= TEXTBOX =========")
                        NEWLINE_RE = re.compile("\n")
                        print(f"pg{i + 1} - {re.sub(NEWLINE_RE, ',', annotation.contents())} ({annotation.author()})")
                    elif isinstance(annotation, popplerqt5.Poppler.GeomAnnotation):
                        print("========= REGION HIGHLIGHT =========")
                        NEWLINE_RE = re.compile("\n")
                        print(f"pg{i + 1} - {re.sub(NEWLINE_RE, ',', annotation.contents())} ({annotation.author()})")
                        boundary = annotation.boundary()
                        x1 = boundary.left()
                        y1 = boundary.top()
                        x2 = boundary.right()
                        y2 = boundary.bottom()
                        qimage = page.renderToImage(72 * 4, 72 * 4,
                                                    x1 * pwidth * 4, y1 * pheight * 4,
                                                    pwidth * (x2 - x1) * 4, pheight * (y2 - y1) * 4)
                        image_path = f"{os.path.basename(filepath)}.extracted_image{image_count}.png"
                        write_success = qimage.save(image_path)
                        if write_success:
                            image_count += 1
                            print(f"Region written to {image_path}")
                        else:
                            print(f"Could not save image!")

    if total_annotations > 0:
        print(str(total_annotations) + " annotation(s) found")
    else:
        print("no annotations found")


if __name__ == "__main__":
    for fn in sorted([fn for fn in os.listdir(PDF_DIR) if fn.endswith(".pdf")]):
        print(fn)
        main(os.path.join(PDF_DIR, fn))
        print()
        print("----------------------------------------------------------------------------------------------")
        print()
