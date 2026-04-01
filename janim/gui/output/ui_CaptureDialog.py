# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'CaptureDialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
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
    QDialog, QDialogButtonBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_CaptureDialog(object):
    def setupUi(self, CaptureDialog):
        if not CaptureDialog.objectName():
            CaptureDialog.setObjectName(u"CaptureDialog")
        CaptureDialog.resize(418, 301)
        self.verticalLayout = QVBoxLayout(CaptureDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.option_groups = QGroupBox(CaptureDialog)
        self.option_groups.setObjectName(u"option_groups")
        self.horizontalLayout = QHBoxLayout(self.option_groups)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(6, 6, 6, 6)
        self.src_option = QWidget(self.option_groups)
        self.src_option.setObjectName(u"src_option")
        self.verticalLayout_2 = QVBoxLayout(self.src_option)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.rb_raw = QRadioButton(self.src_option)
        self.rb_raw.setObjectName(u"rb_raw")
        self.rb_raw.setChecked(True)

        self.verticalLayout_2.addWidget(self.rb_raw)

        self.rb_screen = QRadioButton(self.src_option)
        self.rb_screen.setObjectName(u"rb_screen")

        self.verticalLayout_2.addWidget(self.rb_screen)


        self.horizontalLayout.addWidget(self.src_option)

        self.target_option = QWidget(self.option_groups)
        self.target_option.setObjectName(u"target_option")
        self.verticalLayout_3 = QVBoxLayout(self.target_option)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.rb_file = QRadioButton(self.target_option)
        self.rb_file.setObjectName(u"rb_file")
        self.rb_file.setChecked(True)

        self.verticalLayout_3.addWidget(self.rb_file)

        self.rb_clipboard = QRadioButton(self.target_option)
        self.rb_clipboard.setObjectName(u"rb_clipboard")

        self.verticalLayout_3.addWidget(self.rb_clipboard)


        self.horizontalLayout.addWidget(self.target_option)


        self.verticalLayout.addWidget(self.option_groups)

        self.vspacer_options = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.vspacer_options)

        self.gridlayout = QGridLayout()
        self.gridlayout.setObjectName(u"gridlayout")
        self.hlayout_path = QHBoxLayout()
        self.hlayout_path.setObjectName(u"hlayout_path")
        self.edit_path = QLineEdit(CaptureDialog)
        self.edit_path.setObjectName(u"edit_path")
        self.edit_path.setReadOnly(True)

        self.hlayout_path.addWidget(self.edit_path)

        self.btn_browse = QPushButton(CaptureDialog)
        self.btn_browse.setObjectName(u"btn_browse")
        self.btn_browse.setMinimumSize(QSize(30, 0))
        self.btn_browse.setMaximumSize(QSize(30, 16777215))

        self.hlayout_path.addWidget(self.btn_browse)

        self.hlayout_path.setStretch(0, 1)

        self.gridlayout.addLayout(self.hlayout_path, 1, 1, 1, 1)

        self.label_path = QLabel(CaptureDialog)
        self.label_path.setObjectName(u"label_path")

        self.gridlayout.addWidget(self.label_path, 1, 0, 1, 1)

        self.label_size = QLabel(CaptureDialog)
        self.label_size.setObjectName(u"label_size")

        self.gridlayout.addWidget(self.label_size, 2, 0, 1, 1)

        self.hlayout_size = QHBoxLayout()
        self.hlayout_size.setObjectName(u"hlayout_size")
        self.cbb_size = QComboBox(CaptureDialog)
        self.cbb_size.setObjectName(u"cbb_size")
        self.cbb_size.setMinimumSize(QSize(160, 0))

        self.hlayout_size.addWidget(self.cbb_size)

        self.spacer_size = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.hlayout_size.addItem(self.spacer_size)


        self.gridlayout.addLayout(self.hlayout_size, 2, 1, 1, 1)


        self.verticalLayout.addLayout(self.gridlayout)

        self.hlayout_transparent = QHBoxLayout()
        self.hlayout_transparent.setObjectName(u"hlayout_transparent")
        self.spacer_transparent = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.hlayout_transparent.addItem(self.spacer_transparent)

        self.ckb_transparent = QCheckBox(CaptureDialog)
        self.ckb_transparent.setObjectName(u"ckb_transparent")
        self.ckb_transparent.setChecked(True)

        self.hlayout_transparent.addWidget(self.ckb_transparent)


        self.verticalLayout.addLayout(self.hlayout_transparent)

        self.hlayout_open = QHBoxLayout()
        self.hlayout_open.setObjectName(u"hlayout_open")
        self.spacer_open = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.hlayout_open.addItem(self.spacer_open)

        self.ckb_open = QCheckBox(CaptureDialog)
        self.ckb_open.setObjectName(u"ckb_open")

        self.hlayout_open.addWidget(self.ckb_open)


        self.verticalLayout.addLayout(self.hlayout_open)

        self.vspacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.vspacer)

        self.btn_box = QDialogButtonBox(CaptureDialog)
        self.btn_box.setObjectName(u"btn_box")
        self.btn_box.setOrientation(Qt.Orientation.Horizontal)
        self.btn_box.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout.addWidget(self.btn_box)

        self.vspacer2 = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.vspacer2)


        self.retranslateUi(CaptureDialog)
        self.btn_box.rejected.connect(CaptureDialog.reject)

        QMetaObject.connectSlotsByName(CaptureDialog)
    # setupUi

    def retranslateUi(self, CaptureDialog):
        CaptureDialog.setWindowTitle(QCoreApplication.translate("CaptureDialog", u"Export", None))
        self.option_groups.setTitle(QCoreApplication.translate("CaptureDialog", u"_", None))
        self.rb_raw.setText(QCoreApplication.translate("CaptureDialog", u"_", None))
        self.rb_screen.setText(QCoreApplication.translate("CaptureDialog", u"_", None))
        self.rb_file.setText(QCoreApplication.translate("CaptureDialog", u"_", None))
        self.rb_clipboard.setText(QCoreApplication.translate("CaptureDialog", u"_", None))
        self.btn_browse.setText(QCoreApplication.translate("CaptureDialog", u"...", None))
        self.label_path.setText(QCoreApplication.translate("CaptureDialog", u"_", None))
        self.label_size.setText(QCoreApplication.translate("CaptureDialog", u"_", None))
        self.ckb_transparent.setText(QCoreApplication.translate("CaptureDialog", u"_", None))
        self.ckb_open.setText(QCoreApplication.translate("CaptureDialog", u"_", None))
    # retranslateUi

