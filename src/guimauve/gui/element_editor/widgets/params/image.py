from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QVBoxLayout

from guimauve.gui.common.widgets.combo_box import YesNoComboBox
from guimauve.gui.common.widgets.line_edit import FloatLineEdit, IntLineEdit


class ImageParamsGroup(QGroupBox):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("IMAGE", parent)
        self._init_ui()
        self._init_signals()

    def load(self, element, default):
        self.blockSignals(True)

        # DEFAULT
        self.cmb_use_template.default = default.use_template
        self.cmb_template_grayscale.default = default.template_grayscale
        self.edt_template_confidence_threshold.default = default.template_confidence_threshold

        self.cmb_use_feature.default = default.use_feature
        self.edt_feature_n_features.default = default.feature_n_features
        self.edt_feature_contrast_threshold.default = default.feature_contrast_threshold
        self.edt_feature_edge_threshold.default = default.feature_edge_threshold
        self.edt_feature_sigma.default = default.feature_sigma
        self.edt_feature_lowe_ratio.default = default.feature_lowe_ratio
        self.edt_feature_min_points.default = default.feature_min_points
        self.edt_feature_ransac_threshold.default = default.feature_ransac_threshold
        self.edt_feature_ratio_tolerance.default = default.feature_ratio_tolerance
        self.edt_feature_size_tolerance.default = default.feature_size_tolerance

        self.cmb_use_ocr.default = default.use_ocr
        self.edt_ocr_confidence_threshold.default = default.ocr_confidence_threshold

        # VALUES
        self.cmb_use_template.value = element.use_template
        self.cmb_template_grayscale.value = element.template_grayscale
        self.edt_template_confidence_threshold.value = element.template_confidence_threshold

        self.cmb_use_feature.value = element.use_feature
        self.edt_feature_n_features.value = element.feature_n_features
        self.edt_feature_contrast_threshold.value = element.feature_contrast_threshold
        self.edt_feature_edge_threshold.value = element.feature_edge_threshold
        self.edt_feature_sigma.value = element.feature_sigma
        self.edt_feature_lowe_ratio.value = element.feature_lowe_ratio
        self.edt_feature_min_points.value = element.feature_min_points
        self.edt_feature_ransac_threshold.value = element.feature_ransac_threshold
        self.edt_feature_ratio_tolerance.value = element.feature_ratio_tolerance
        self.edt_feature_size_tolerance.value = element.feature_size_tolerance

        self.cmb_use_ocr.value = element.use_ocr
        self.edt_ocr_confidence_threshold.value = element.ocr_confidence_threshold

        self.blockSignals(False)

    def _on_changed(self):
        to_update = {
            "use_template": self.cmb_use_template.value,
            "template_grayscale": self.cmb_template_grayscale.value,
            "template_confidence_threshold": self.edt_template_confidence_threshold.value,
            "use_feature": self.cmb_use_feature.value,
            "feature_n_features": self.edt_feature_n_features.value,
            "feature_contrast_threshold": self.edt_feature_contrast_threshold.value,
            "feature_edge_threshold": self.edt_feature_edge_threshold.value,
            "feature_sigma": self.edt_feature_sigma.value,
            "feature_lowe_ratio": self.edt_feature_lowe_ratio.value,
            "feature_min_points": self.edt_feature_min_points.value,
            "feature_ransac_threshold": self.edt_feature_ransac_threshold.value,
            "feature_ratio_tolerance": self.edt_feature_ratio_tolerance.value,
            "feature_size_tolerance": self.edt_feature_size_tolerance.value,
            "use_ocr": self.cmb_use_ocr.value,
            "ocr_confidence_threshold": self.edt_ocr_confidence_threshold.value,
        }

        self.changed.emit(to_update)

    def _init_ui(self):
        # TEMPLATE
        self.cmb_use_template = YesNoComboBox()
        self.cmb_template_grayscale = YesNoComboBox()
        self.edt_template_confidence_threshold = FloatLineEdit(min_val=0.0, max_val=1.0, decimals=2)

        # FEATURE
        self.cmb_use_feature = YesNoComboBox()
        self.edt_feature_n_features = IntLineEdit(min_val=10, max_val=5000)
        self.edt_feature_contrast_threshold = FloatLineEdit(min_val=0.01, max_val=0.2)
        self.edt_feature_edge_threshold = IntLineEdit(min_val=1, max_val=50)
        self.edt_feature_sigma = FloatLineEdit(min_val=0.5, max_val=3.0)
        self.edt_feature_lowe_ratio = FloatLineEdit(min_val=0.4, max_val=0.95)
        self.edt_feature_min_points = IntLineEdit(min_val=4, max_val=50)
        self.edt_feature_ransac_threshold = FloatLineEdit(min_val=1.0, max_val=5.0)
        self.edt_feature_ratio_tolerance = FloatLineEdit(min_val=0.01, max_val=2.0)
        self.edt_feature_size_tolerance = FloatLineEdit(min_val=0.1, max_val=8.0)

        # OCR
        self.cmb_use_ocr = YesNoComboBox(self)
        self.edt_ocr_confidence_threshold = FloatLineEdit(min_val=0.0, max_val=1.0, decimals=2)

        # ASSEMBLY
        layout = QVBoxLayout(self)

        grp_template = QGroupBox("TEMPLATE MATCHING")
        template_layout = QFormLayout(grp_template)
        template_layout.addRow("Use", self.cmb_use_template)
        template_layout.addRow("Grayscale", self.cmb_template_grayscale)
        template_layout.addRow("Confidence Thr.", self.edt_template_confidence_threshold)

        grp_feature = QGroupBox("FEATURE MATCHING")
        feature_layout = QFormLayout(grp_feature)
        feature_layout.addRow("Use", self.cmb_use_feature)
        feature_layout.addRow("N Features", self.edt_feature_n_features)
        feature_layout.addRow("Contrast Thr.", self.edt_feature_contrast_threshold)
        feature_layout.addRow("Edge Thr.", self.edt_feature_edge_threshold)
        feature_layout.addRow("Sigma", self.edt_feature_sigma)
        feature_layout.addRow("Lowe ratio", self.edt_feature_lowe_ratio)
        feature_layout.addRow("Min points", self.edt_feature_min_points)
        feature_layout.addRow("Ransac Thr.", self.edt_feature_ransac_threshold)
        feature_layout.addRow("Ratio Tol.", self.edt_feature_ratio_tolerance)
        feature_layout.addRow("Size Tol.", self.edt_feature_size_tolerance)

        grp_ocr = QGroupBox("OCR")
        ocr_layout = QFormLayout(grp_ocr)
        ocr_layout.addRow("Use", self.cmb_use_ocr)
        ocr_layout.addRow("Confidence Thr.", self.edt_ocr_confidence_threshold)

        layout.addWidget(grp_template)
        layout.addWidget(grp_feature)
        layout.addWidget(grp_ocr)

    def _init_signals(self):
        # TEMPLATE
        self.cmb_use_template.currentIndexChanged.connect(self._on_changed)
        self.cmb_template_grayscale.currentIndexChanged.connect(self._on_changed)
        self.edt_template_confidence_threshold.textChanged.connect(self._on_changed)

        # FEATURE
        self.cmb_use_feature.currentIndexChanged.connect(self._on_changed)
        self.edt_feature_n_features.textChanged.connect(self._on_changed)
        self.edt_feature_contrast_threshold.textChanged.connect(self._on_changed)
        self.edt_feature_edge_threshold.textChanged.connect(self._on_changed)
        self.edt_feature_sigma.textChanged.connect(self._on_changed)
        self.edt_feature_lowe_ratio.textChanged.connect(self._on_changed)
        self.edt_feature_min_points.textChanged.connect(self._on_changed)
        self.edt_feature_ransac_threshold.textChanged.connect(self._on_changed)
        self.edt_feature_ratio_tolerance.textChanged.connect(self._on_changed)
        self.edt_feature_size_tolerance.textChanged.connect(self._on_changed)

        # OCR
        self.cmb_use_ocr.currentIndexChanged.connect(self._on_changed)
        self.edt_ocr_confidence_threshold.textChanged.connect(self._on_changed)
