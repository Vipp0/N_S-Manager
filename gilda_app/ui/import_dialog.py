from PySide6.QtWidgets import QButtonGroup, QLabel
from qfluentwidgets import MessageBoxBase, RadioButton, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.importer.excel_import import ImportPreview
from gilda_app.models.member import status_label


class ImportPreviewDialog(MessageBoxBase):
    """Anteprima import: conteggi per foglio e scelta della policy sui duplicati."""

    def __init__(self, parent, preview: ImportPreview, duplicate_count: int):
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

        if duplicate_count > 0:
            self.viewLayout.addWidget(QLabel(tr("import.duplicate_warning", count=duplicate_count), self))
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

        self.widget.setMinimumWidth(420)
        self.yesButton.setText(tr("button.confirm_import"))
        self.cancelButton.setText(tr("button.cancel"))

    def duplicate_policy(self) -> str:
        if self.update_radio is not None and self.update_radio.isChecked():
            return "update"
        if self.insert_radio is not None and self.insert_radio.isChecked():
            return "insert"
        return "skip"
