# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ExportDialog.ui'
##
## Created by: Qt User Interface Compiler version 6.8.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QSpinBox,
    QVBoxLayout, QWidget)

class Ui_ExportDialog(object):
    def setupUi(self, ExportDialog):
        if not ExportDialog.objectName():
            ExportDialog.setObjectName(u"ExportDialog")
        ExportDialog.resize(409, 221)
        self.verticalLayout = QVBoxLayout(ExportDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.vspacer1 = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.vspacer1)

        self.gridlayout = QGridLayout()
        self.gridlayout.setObjectName(u"gridlayout")
        self.hlayout_fps = QHBoxLayout()
        self.hlayout_fps.setObjectName(u"hlayout_fps")
        self.spb_fps = QSpinBox(ExportDialog)
        self.spb_fps.setObjectName(u"spb_fps")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.spb_fps.sizePolicy().hasHeightForWidth())
        self.spb_fps.setSizePolicy(sizePolicy)
        self.spb_fps.setMinimumSize(QSize(80, 0))
        self.spb_fps.setMinimum(1)
        self.spb_fps.setMaximum(999)
        self.spb_fps.setValue(60)

        self.hlayout_fps.addWidget(self.spb_fps)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.hlayout_fps.addItem(self.horizontalSpacer)


        self.gridlayout.addLayout(self.hlayout_fps, 2, 1, 1, 1)

        self.label_path = QLabel(ExportDialog)
        self.label_path.setObjectName(u"label_path")

        self.gridlayout.addWidget(self.label_path, 1, 0, 1, 1)

        self.hlayout_path = QHBoxLayout()
        self.hlayout_path.setObjectName(u"hlayout_path")
        self.edit_path = QLineEdit(ExportDialog)
        self.edit_path.setObjectName(u"edit_path")
        self.edit_path.setReadOnly(True)

        self.hlayout_path.addWidget(self.edit_path)

        self.btn_browse = QPushButton(ExportDialog)
        self.btn_browse.setObjectName(u"btn_browse")
        self.btn_browse.setMinimumSize(QSize(30, 0))
        self.btn_browse.setMaximumSize(QSize(30, 16777215))

        self.hlayout_path.addWidget(self.btn_browse)

        self.hlayout_path.setStretch(0, 1)

        self.gridlayout.addLayout(self.hlayout_path, 1, 1, 1, 1)

        self.label_fps = QLabel(ExportDialog)
        self.label_fps.setObjectName(u"label_fps")

        self.gridlayout.addWidget(self.label_fps, 2, 0, 1, 1)

        self.label_size = QLabel(ExportDialog)
        self.label_size.setObjectName(u"label_size")

        self.gridlayout.addWidget(self.label_size, 3, 0, 1, 1)

        self.hlayou_size = QHBoxLayout()
        self.hlayou_size.setObjectName(u"hlayou_size")
        self.cbb_size = QComboBox(ExportDialog)
        self.cbb_size.setObjectName(u"cbb_size")
        self.cbb_size.setMinimumSize(QSize(160, 0))

        self.hlayou_size.addWidget(self.cbb_size)

        self.spacer_size = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.hlayou_size.addItem(self.spacer_size)


        self.gridlayout.addLayout(self.hlayou_size, 3, 1, 1, 1)


        self.verticalLayout.addLayout(self.gridlayout)

        self.hlayout_d = QHBoxLayout()
        self.hlayout_d.setObjectName(u"hlayout_d")
        self.frame = QFrame(ExportDialog)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Plain)
        self.gridLayout = QGridLayout(self.frame)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(8)
        self.gridLayout.setVerticalSpacing(2)
        self.gridLayout.setContentsMargins(4, 4, 20, 4)
        self.label_range = QLabel(self.frame)
        self.label_range.setObjectName(u"label_range")
        self.label_range.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.gridLayout.addWidget(self.label_range, 0, 0, 1, 1)

        self.rbtn_full = QRadioButton(self.frame)
        self.rbtn_full.setObjectName(u"rbtn_full")
        self.rbtn_full.setChecked(True)

        self.gridLayout.addWidget(self.rbtn_full, 0, 1, 1, 1)

        self.rbtn_inout = QRadioButton(self.frame)
        self.rbtn_inout.setObjectName(u"rbtn_inout")

        self.gridLayout.addWidget(self.rbtn_inout, 1, 1, 1, 1)


        self.hlayout_d.addWidget(self.frame)

        self.spacer_d = QSpacerItem(20, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.hlayout_d.addItem(self.spacer_d)

        self.vlayout_dr = QVBoxLayout()
        self.vlayout_dr.setObjectName(u"vlayout_dr")
        self.hlayout_hwaccel = QHBoxLayout()
        self.hlayout_hwaccel.setObjectName(u"hlayout_hwaccel")
        self.spacer_hwaccel = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.hlayout_hwaccel.addItem(self.spacer_hwaccel)

        self.ckb_hwaccel = QCheckBox(ExportDialog)
        self.ckb_hwaccel.setObjectName(u"ckb_hwaccel")

        self.hlayout_hwaccel.addWidget(self.ckb_hwaccel)


        self.vlayout_dr.addLayout(self.hlayout_hwaccel)

        self.hlayout_open = QHBoxLayout()
        self.hlayout_open.setObjectName(u"hlayout_open")
        self.spacer_open = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.hlayout_open.addItem(self.spacer_open)

        self.ckb_open = QCheckBox(ExportDialog)
        self.ckb_open.setObjectName(u"ckb_open")

        self.hlayout_open.addWidget(self.ckb_open)


        self.vlayout_dr.addLayout(self.hlayout_open)


        self.hlayout_d.addLayout(self.vlayout_dr)


        self.verticalLayout.addLayout(self.hlayout_d)

        self.verticalSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.btn_box = QDialogButtonBox(ExportDialog)
        self.btn_box.setObjectName(u"btn_box")
        self.btn_box.setOrientation(Qt.Orientation.Horizontal)
        self.btn_box.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.btn_box)

        self.vspacer2 = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.vspacer2)


        self.retranslateUi(ExportDialog)
        self.btn_box.rejected.connect(ExportDialog.reject)

        QMetaObject.connectSlotsByName(ExportDialog)
    # setupUi

    def retranslateUi(self, ExportDialog):
        ExportDialog.setWindowTitle(QCoreApplication.translate("ExportDialog", u"Export", None))
        self.label_path.setText(QCoreApplication.translate("ExportDialog", u"_", None))
        self.btn_browse.setText(QCoreApplication.translate("ExportDialog", u"...", None))
        self.label_fps.setText(QCoreApplication.translate("ExportDialog", u"_", None))
        self.label_size.setText(QCoreApplication.translate("ExportDialog", u"_", None))
        self.label_range.setText(QCoreApplication.translate("ExportDialog", u"_", None))
        self.rbtn_full.setText(QCoreApplication.translate("ExportDialog", u"_", None))
        self.rbtn_inout.setText(QCoreApplication.translate("ExportDialog", u"_", None))
        self.ckb_hwaccel.setText(QCoreApplication.translate("ExportDialog", u"_", None))
        self.ckb_open.setText(QCoreApplication.translate("ExportDialog", u"_", None))
    # retranslateUi

