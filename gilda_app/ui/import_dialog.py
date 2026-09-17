from PySide6.QtWidgets import QButtonGroup, QLabel
from qfluentwidgets import MessageBoxBase, RadioButton, SubtitleLabel

from gilda_app.importer.excel_import import ImportPreview
from gilda_app.models.member import STATUS_LABELS


class ImportPreviewDialog(MessageBoxBase):
    """Anteprima import: conteggi per foglio e scelta della policy sui duplicati."""

    def __init__(self, parent, preview: ImportPreview, duplicate_count: int):
        super().__init__(parent)
        self.preview = preview

        self.titleLabel = SubtitleLabel("Anteprima import", self)
        self.viewLayout.addWidget(self.titleLabel)

        for report in preview.sheet_reports:
            text = (
                f"{report.sheet_name} → {STATUS_LABELS[report.status]}: "
                f"{report.imported_rows} righe valide, {report.skipped_blank} righe vuote scartate"
            )
            self.viewLayout.addWidget(QLabel(text, self))

        self.viewLayout.addWidget(QLabel(f"\nTotale righe da importare: {len(preview.rows)}", self))

        if duplicate_count > 0:
            self.viewLayout.addWidget(
                QLabel(
                    f"⚠ {duplicate_count} nominativi risultano già presenti nel database "
                    "(stesso Family Name + Main Name). Cosa vuoi fare con questi duplicati?",
                    self,
                )
            )
            self.button_group = QButtonGroup(self)
            self.skip_radio = RadioButton("Salta i duplicati (non modificarli)", self)
            self.update_radio = RadioButton("Aggiorna i duplicati esistenti con i nuovi dati", self)
            self.insert_radio = RadioButton("Inserisci comunque come nuove voci separate", self)
            self.skip_radio.setChecked(True)
            for rb in (self.skip_radio, self.update_radio, self.insert_radio):
                self.button_group.addButton(rb)
                self.viewLayout.addWidget(rb)
        else:
            self.skip_radio = self.update_radio = self.insert_radio = None

        self.widget.setMinimumWidth(420)
        self.yesButton.setText("Conferma import")
        self.cancelButton.setText("Annulla")

    def duplicate_policy(self) -> str:
        if self.update_radio is not None and self.update_radio.isChecked():
            return "update"
        if self.insert_radio is not None and self.insert_radio.isChecked():
            return "insert"
        return "skip"
