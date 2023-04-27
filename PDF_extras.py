import xml.etree.ElementTree as ET

from RPA.PDF import PDF
import fitz
import imagehash
import io
from PIL import Image

FIELDS = {
    "Yrityksen nimi",
    "Muu tunnuksen tyyppi",
    "Allekirjoittajan nimi",
    "Valtuutetun nimi",
    "Puhelinnumero",
    "Yrityksen tunnus",
    "Allekirjoittajan sähköpostiosoite",
    "Sähköpostiosoite (käyttäjätunnus)",
    "Valtuutuksen laajuus",
}
CHECKBOX_FIELDS = [
    "DNA Palvelutasot (Laitteiden valvontajärjestelmä)",
    "Liittymien hallinta ja raportointi (Sähköiset itsepalvelukanavat)",
]
REFERENCE_CHECKED_IMAGE = "resources/checkbox_checked.png"


class PDF_extras:
    def get_fields(self, filename_pdf):
        return self.get_text_fields(filename_pdf) | self.get_checkbox_fields(
            filename_pdf
        )

    def get_text_fields(self, filename_pdf):
        pdf = PDF()
        pdf.open_pdf(filename_pdf)
        xml = pdf.dump_pdf_as_xml()

        current_field = None
        fields = {}

        for line in self.get_lines(xml):
            if line in FIELDS:
                current_field = line
                continue

            if current_field:
                fields[current_field] = line

            current_field = None

        return fields

    def get_lines(self, xml):
        pages = ET.fromstring(xml)
        for page in pages:
            for textbox in [_textbox for _textbox in page if _textbox.tag == "textbox"]:
                for textline in [
                    _textline for _textline in textbox if _textline.tag == "textline"
                ]:
                    yield self.parse_textline(textline)

    def parse_textline(self, textline):
        data = []
        for text in [_text for _text in textline if _text.tag == "text"]:
            data.append(text.text)
        return "".join(data).strip()

    def get_checkbox_fields(self, filename: str):
        blocks = self.get_blocks_from_pdf(filename)

        checkboxes = {}
        for _, page_blocks in blocks.items():
            for block in page_blocks:
                block_text = self.get_text_from_block(block)
                if block_text and block_text in CHECKBOX_FIELDS:
                    img_number = block["number"] - 1
                    previous_block = page_blocks[img_number]
                    if previous_block["type"] == 1:
                        checkboxes[img_number] = {
                            "image": previous_block,
                            "text": block_text,
                            "checked": None,
                        }
        return {
            v["text"]: v["checked"]
            for v in self.get_status_of_checkboxes(checkboxes).values()
        }

    def get_status_of_checkboxes(self, checkboxes):
        hash0 = imagehash.average_hash(Image.open(REFERENCE_CHECKED_IMAGE))
        cutoff = 5  # maximum bits that could be different between the hashes.
        for checkbox_number, checkbox in checkboxes.items():
            hash1 = imagehash.average_hash(
                Image.open(io.BytesIO(checkbox["image"]["image"]))
            )
            if hash0 - hash1 < cutoff:
                checkboxes[checkbox_number]["checked"] = True
            else:
                checkboxes[checkbox_number]["checked"] = False
        return checkboxes

    def get_blocks_from_pdf(self, filename: str):
        doc = fitz.open(filename)
        page_blocks = {}
        for page in doc:
            page_text = page.get_text("dict")
            page_blocks[page.number + 1] = page_text["blocks"]
        return page_blocks

    def get_text_from_block(self, block):
        if block["type"] != 0:
            return None
        text = ""
        for line in block["lines"]:
            for span in line["spans"]:
                text += span["text"]
        return text
