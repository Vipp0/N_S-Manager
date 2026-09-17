from PySide6.QtWidgets import QButtonGroup, QLabel
from qfluentwidgets import MessageBoxBase, RadioButton, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.importer.excel_import import DuplicateEntry, ImportPreview
from gilda_app.models.member import status_label

# Oltre questo numero i doppioni vengono riassunti ("... e altri N") invece di essere
# elencati uno per uno, per non far diventare il dialogo enorme in un file con molti
# doppioni.
MAX_DUPLICATES_SHOWN = 8


class ImportPreviewDialog(MessageBoxBase):
    """Anteprima import: conteggi per foglio e scelta della policy sui duplicati (sia
    quelli già nel database, sia quelli ripetuti due volte all'interno dello stesso
    file: prima venivano scartati alla cieca con la policy di default senza che
    l'utente lo sapesse in anticipo)."""

    def __init__(self, parent, preview: ImportPreview, duplicate_count: int, intra_duplicates: list[DuplicateEntry]):
        super().__init__(parent)
        self.preview = preview

        self.titleLabel = SubtitleLabel(tr("dialog.import_preview.title"), self)
        self.viewLayout.addWidget(self.titleLabel)

        for report in preview.sheet_reports:
            text = tr(
                "import.sheet_summary",
                sheet=report.sheet_name,
                status=status_label(report.status),
                imported=report.imported_rows,
                skipped=report.skipped_blank,
            )
            self.viewLayout.addWidget(QLabel(text, self))

        self.viewLayout.addWidget(QLabel(tr("import.total_rows", total=len(preview.rows)), self))

        if intra_duplicates:
            self.viewLayout.addWidget(
                QLabel(tr("import.intra_duplicate_warning", count=len(intra_duplicates)), self)
            )
            for entry in intra_duplicates[:MAX_DUPLICATES_SHOWN]:
                line = tr(
                    "import.intra_duplicate_line",
                    family=entry.duplicate.family_name,
                    main=entry.duplicate.main_name,
                    sheet1=entry.first.sheet_name,
                    row1=entry.first.row_number,
                    sheet2=entry.duplicate.sheet_name,
                    row2=entry.duplicate.row_number,
                )
                if entry.fields_differ:
                    line += " " + tr("import.intra_duplicate_fields_differ")
                label = QLabel(line, self)
                if entry.fields_differ:
                    label.setStyleSheet("color: #c42b1c;")
                self.viewLayout.addWidget(label)
            if len(intra_duplicates) > MAX_DUPLICATES_SHOWN:
                remaining = len(intra_duplicates) - MAX_DUPLICATES_SHOWN
                self.viewLayout.addWidget(QLabel(tr("import.intra_duplicate_more", count=remaining), self))

        total_duplicates = duplicate_count + len(intra_duplicates)
        if total_duplicates > 0:
            self.viewLayout.addWidget(QLabel(tr("import.duplicate_warning", count=total_duplicates), self))
            self.button_group = QButtonGroup(self)
            self.skip_radio = RadioButton(tr("import.policy_skip"), self)
            self.update_radio = RadioButton(tr("import.policy_update"), self)
            self.insert_radio = RadioButton(tr("import.policy_insert"), self)
            self.skip_radio.setChecked(True)
            for rb in (self.skip_radio, self.update_radio, self.insert_radio):
                self.button_group.addButton(rb)
                self.viewLayout.addWidget(rb)
        else:
            self.skip_radio = self.update_radio = self.insert_radio = None

        self.widget.setMinimumWidth(520)
        self.yesButton.setText(tr("button.confirm_import"))
        self.cancelButton.setText(tr("button.cancel"))

    def duplicate_policy(self) -> str:
        if self.update_radio is not None and self.update_radio.isChecked():
            return "update"
        if self.insert_radio is not None and self.insert_radio.isChecked():
            return "insert"
        return "skip"
