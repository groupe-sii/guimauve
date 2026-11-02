from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from guimauve.enums import OcrFidelity
from guimauve.gui.common.widgets.combo_box import NoScrollComboBox, YesNoComboBox
from guimauve.gui.common.widgets.line_edit import FloatLineEdit, IntLineEdit


class TestDialog(QDialog):
    test_requested = Signal(str, dict)

    def __init__(self, default, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Test Parameters")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setFixedSize(280, 450)

        self.default = default

        self._init_ui()
        self._init_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- MODE SELECTION ---
        grp_mode = QGroupBox("Detection")
        mode_layout = QVBoxLayout(grp_mode)
        self.rad_template = QRadioButton("Template matching")
        self.rad_feature = QRadioButton("Feature matching")
        self.rad_ocr = QRadioButton("OCR")
        self.rad_template.setChecked(True)
        mode_layout.addWidget(self.rad_template)
        mode_layout.addWidget(self.rad_feature)
        mode_layout.addWidget(self.rad_ocr)
        layout.addWidget(grp_mode)

        # --- STACKED PARAMS ---
        self.param_stack = QStackedWidget()

        # TEMPLATE
        self.page_template = QWidget()
        tpl_layout = QFormLayout(self.page_template)

        self.cmb_template_grayscale = YesNoComboBox(undefined_item=False)
        self.edt_template_confidence_threshold = FloatLineEdit(min_val=0.0, max_val=1.0)

        self.cmb_template_grayscale.value = self.default.template_grayscale
        self.edt_template_confidence_threshold.value = self.default.template_confidence_threshold

        tpl_layout.addRow("Grayscale", self.cmb_template_grayscale)
        tpl_layout.addRow("Confidence Thr.", self.edt_template_confidence_threshold)

        self.param_stack.addWidget(self.page_template)

        # FEATURE
        self.page_feature = QWidget()
        feature_main_layout = QVBoxLayout(self.page_feature)
        feature_main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_content = QWidget()
        f_layout = QFormLayout(scroll_content)
        f_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.edt_feature_n_features = IntLineEdit(min_val=10, max_val=5000)
        self.edt_feature_contrast_threshold = FloatLineEdit(min_val=0.01, max_val=0.2)
        self.edt_feature_edge_threshold = IntLineEdit(min_val=1, max_val=50)
        self.edt_feature_sigma = FloatLineEdit(min_val=0.5, max_val=3.0)
        self.edt_feature_lowe_ratio = FloatLineEdit(min_val=0.4, max_val=0.95)
        self.edt_feature_min_points = IntLineEdit(min_val=4, max_val=50)
        self.edt_feature_ransac_threshold = FloatLineEdit(min_val=1.0, max_val=20.0)
        self.edt_feature_ratio_tolerance = FloatLineEdit(min_val=0.01, max_val=2.0)
        self.edt_feature_size_tolerance = FloatLineEdit(min_val=0.05, max_val=8.0)

        self.edt_feature_n_features.value = self.default.feature_n_features
        self.edt_feature_contrast_threshold.value = self.default.feature_contrast_threshold
        self.edt_feature_edge_threshold.value = self.default.feature_edge_threshold
        self.edt_feature_sigma.value = self.default.feature_sigma
        self.edt_feature_lowe_ratio.value = self.default.feature_lowe_ratio
        self.edt_feature_min_points.value = self.default.feature_min_points
        self.edt_feature_ransac_threshold.value = self.default.feature_ransac_threshold
        self.edt_feature_ratio_tolerance.value = self.default.feature_ratio_tolerance
        self.edt_feature_size_tolerance.value = self.default.feature_size_tolerance

        f_layout.addRow("N Features", self.edt_feature_n_features)
        f_layout.addRow("Contrast Thr.", self.edt_feature_contrast_threshold)
        f_layout.addRow("Edge Thr.", self.edt_feature_edge_threshold)
        f_layout.addRow("Sigma", self.edt_feature_sigma)
        f_layout.addRow("Lowe Ratio", self.edt_feature_lowe_ratio)
        f_layout.addRow("Min Points", self.edt_feature_min_points)
        f_layout.addRow("RANSAC Thr.", self.edt_feature_ransac_threshold)
        f_layout.addRow("Ratio Tol.", self.edt_feature_ratio_tolerance)
        f_layout.addRow("Size Tol.", self.edt_feature_size_tolerance)

        scroll.setWidget(scroll_content)
        feature_main_layout.addWidget(scroll)
        self.param_stack.addWidget(self.page_feature)

        layout.addWidget(self.param_stack)

        # OCR
        self.page_ocr = QWidget()
        ocr_layout = QFormLayout(self.page_ocr)

        self.edt_ocr_confidence_threshold = FloatLineEdit(min_val=0.0, max_val=1.0)
        self.cmb_ocr_fidelity = NoScrollComboBox()
        for fidelity in OcrFidelity:
            self.cmb_ocr_fidelity.addItem(fidelity.name, fidelity)

        self.edt_ocr_confidence_threshold.value = self.default.ocr_confidence_threshold
        self.cmb_ocr_fidelity.setCurrentIndex(self.cmb_ocr_fidelity.findData(self.default.ocr_fidelity))

        ocr_layout.addRow("Confidence Thr.", self.edt_ocr_confidence_threshold)
        ocr_layout.addRow("Fidelity.", self.cmb_ocr_fidelity)

        self.param_stack.addWidget(self.page_ocr)

        # --- ACTIONS / RESULTS ---
        self.btn_test = QPushButton("Run Test")
        self.btn_test.setMinimumHeight(35)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)

        self.lbl_result = QLabel("")
        self.lbl_result.setAlignment(Qt.AlignCenter)
        self.lbl_result.setStyleSheet("font-weight: bold;")

        layout.addWidget(self.btn_test)
        layout.addWidget(self.progress)
        layout.addWidget(self.lbl_result)

    def _init_signals(self):
        self.btn_test.clicked.connect(self._on_test)
        self.rad_template.toggled.connect(lambda t: self.param_stack.setCurrentIndex(0))
        self.rad_feature.toggled.connect(lambda t: self.param_stack.setCurrentIndex(1))
        self.rad_ocr.toggled.connect(lambda t: self.param_stack.setCurrentIndex(2))

    def _on_test(self):
        is_template = self.rad_template.isChecked()
        is_feature = self.rad_feature.isChecked()
        is_ocr = self.rad_ocr.isChecked()

        mode = None
        params = None

        if is_template:
            mode = "template"
            params = {
                "grayscale": self.cmb_template_grayscale.value,
                "confidence_threshold": self.edt_template_confidence_threshold.value,
            }
        elif is_feature:
            mode = "feature"
            params = {
                "n_features": self.edt_feature_n_features.value,
                "contrast_threshold": self.edt_feature_contrast_threshold.value,
                "edge_threshold": self.edt_feature_edge_threshold.value,
                "sigma": self.edt_feature_sigma.value,
                "lowe_ratio": self.edt_feature_lowe_ratio.value,
                "min_points": self.edt_feature_min_points.value,
                "ransac_threshold": self.edt_feature_ransac_threshold.value,
                "ratio_tolerance": self.edt_feature_ratio_tolerance.value,
                "size_tolerance": self.edt_feature_size_tolerance.value,
            }
        elif is_ocr:
            mode = "ocr"
            params = {
                "confidence_threshold": self.edt_ocr_confidence_threshold.value,
                "fidelity": self.cmb_ocr_fidelity.currentData(),
            }

        self.set_running(True)
        self.test_requested.emit(mode, params)

    def set_running(self, running: bool):
        self.btn_test.setEnabled(not running)
        self.progress.setVisible(running)
        if running:
            self.lbl_result.setText("Processing...")
            self.lbl_result.setStyleSheet("color: gray;")

    def set_result(self, count: int):
        self.set_running(False)
        if count == 0:
            self.lbl_result.setText("No match")
            self.lbl_result.setStyleSheet("color: #e05252;")
        else:
            self.lbl_result.setText(f"{count} match{'es' if count > 1 else ''}")
            self.lbl_result.setStyleSheet("color: #52b052;")
