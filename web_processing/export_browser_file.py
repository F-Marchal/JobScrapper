import os
import shutil
import zipfile
from enum import Enum
from tools.secondary_logger_user import SecondaryLoggerUser, logging
from web_processing.enhanced_chrome_browser import EnhancedChrome
from tools.turn_file_to_text import FileToText

class ExportBrowserPage(SecondaryLoggerUser):
    class SaveTypes(Enum):
        DISABLED = "Disabled"
        TEXT = "Text"
        HTML = "HTML or file"
        MHTML = "MHTML or file"

    def __init__(
            self,
            save_type: 'SaveTypes',
            logger: logging.Logger | None = None,
            compress: bool = True,
    ):
        super().__init__(logger)
        self.compress = compress
        self.save_type = save_type

    def export(
            self,
            browser: EnhancedChrome,
            final_dir: str,
            new_name: str,
            raw_file: str | None = None,
            text_file: str | None = None,
    ) -> None: # DO NOT USE raw_file=None IF URL POINT TO FILE.
        raw_has_been_generated_here = False
        if not raw_file:
            raw_file = browser.save_raw_html()
            raw_has_been_generated_here = True

        if self.save_type == self.SaveTypes.DISABLED:
            self.save_disabled()

        elif self.save_type == self.SaveTypes.TEXT:
            self.save_as_text(
                raw_file=raw_file,
                final_dir=final_dir,
                new_name=new_name,
                text_file=text_file,
            )

        elif self.save_type == self.SaveTypes.HTML:
            self.save_as_html(
                raw_file=raw_file,
                final_dir=final_dir,
                new_name=new_name,
            )

        elif self.save_type == self.SaveTypes.MHTML:
            self.save_mhtml_file(
            browser=browser,
            final_dir=final_dir,
            new_name=new_name,
            raw_file=raw_file,
            )

        else:
            raise ValueError(f"Can not use '{self.save_type}' as SaveTypes")

        if raw_has_been_generated_here:
            os.remove(raw_file)

    def save_disabled(self):
        return

    def save_as_html(
            self,
            raw_file: str,
            final_dir: str,
            new_name: str,
    ):
        self.export_file(raw_file, final_dir, new_name)

    def save_as_text(
            self,
            raw_file: str,
            final_dir: str,
            new_name: str,
            text_file: str = None,
    ):
        if text_file:
            self.export_file(text_file, final_dir, new_name)
            return

        # Generate, Export, Delete
        text_file= f"{raw_file}.txt"
        FileToText.convert_to_text_file(text_file, text_file)
        self.export_file(text_file, final_dir, new_name)
        os.remove(text_file)

    def save_mhtml_file(
            self,
            browser: EnhancedChrome,
            final_dir: str,
            new_name: str,
            raw_file: str | None = None,
    ):
        if os.path.splitext(raw_file)[1].lower() != ".html":
            # This a .pdf or somthing else, the complete is supposed
            # to be raw_file. No need to snapshot the website.
            self.export_file(raw_file, final_dir, new_name)
            return

        snapshot = browser.save_snapshot()
        self.export_file(snapshot, final_dir, new_name)
        os.remove(snapshot)

    def export_file(
            self,
            target_file: str,
            to: str,
            new_name: str,
    ) -> None:
        _, ext = os.path.splitext(target_file)
        new_name = new_name.removesuffix(ext)
        file_name = os.path.join(to, f"{new_name}{ext}")

        if not self.compress:
            shutil.copy(target_file, file_name)
            return

        with zipfile.ZipFile(file_name + ".zip", "w", zipfile.ZIP_DEFLATED) as z:
            z.write(target_file)
