# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ColorWidget.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_ColorWidget(object):
    def setupUi(self, ColorWidget):
        if not ColorWidget.objectName():
            ColorWidget.setObjectName(u"ColorWidget")
        ColorWidget.resize(597, 379)
        ColorWidget.setStyleSheet(u"QLabel {\n"
"	background: none;\n"
"}\n"
"QCheckBox {\n"
"	background: none;\n"
"}")
        self.verticalLayout_2 = QVBoxLayout(ColorWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.widget_top = QWidget(ColorWidget)
        self.widget_top.setObjectName(u"widget_top")
        self.horizontalLayout = QHBoxLayout(self.widget_top)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.layout_RGB_2 = QVBoxLayout()
        self.layout_RGB_2.setObjectName(u"layout_RGB_2")
        self.label_RGB = QLabel(self.widget_top)
        self.label_RGB.setObjectName(u"label_RGB")
        self.label_RGB.setIndent(12)

        self.layout_RGB_2.addWidget(self.label_RGB)

        self.widget_RGB = QWidget(self.widget_top)
        self.widget_RGB.setObjectName(u"widget_RGB")
        self.widget_RGB.setStyleSheet(u"#widget_RGB {\n"
"	background: #3e5b7a;\n"
"	border-radius: 12px;\n"
"}")
        self.verticalLayout = QVBoxLayout(self.widget_RGB)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.layout_RGB = QHBoxLayout()
        self.layout_RGB.setObjectName(u"layout_RGB")
        self.label_R = QLabel(self.widget_RGB)
        self.label_R.setObjectName(u"label_R")
        self.label_R.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.layout_RGB.addWidget(self.label_R)

        self.edit_R = QLineEdit(self.widget_RGB)
        self.edit_R.setObjectName(u"edit_R")
        self.edit_R.setMinimumSize(QSize(60, 0))
        self.edit_R.setMaximumSize(QSize(120, 16777215))

        self.layout_RGB.addWidget(self.edit_R)

        self.spacer_RGB_1 = QSpacerItem(13, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.layout_RGB.addItem(self.spacer_RGB_1)

        self.label_G = QLabel(self.widget_RGB)
        self.label_G.setObjectName(u"label_G")
        self.label_G.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.layout_RGB.addWidget(self.label_G)

        self.edit_G = QLineEdit(self.widget_RGB)
        self.edit_G.setObjectName(u"edit_G")
        self.edit_G.setMinimumSize(QSize(60, 0))
        self.edit_G.setMaximumSize(QSize(120, 16777215))

        self.layout_RGB.addWidget(self.edit_G)

        self.spacer_RGB_2 = QSpacerItem(13, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.layout_RGB.addItem(self.spacer_RGB_2)

        self.label_B = QLabel(self.widget_RGB)
        self.label_B.setObjectName(u"label_B")
        self.label_B.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.layout_RGB.addWidget(self.label_B)

        self.edit_B = QLineEdit(self.widget_RGB)
        self.edit_B.setObjectName(u"edit_B")
        self.edit_B.setMinimumSize(QSize(60, 0))
        self.edit_B.setMaximumSize(QSize(120, 16777215))

        self.layout_RGB.addWidget(self.edit_B)


        self.verticalLayout.addLayout(self.layout_RGB)

        self.layout_norm = QHBoxLayout()
        self.layout_norm.setObjectName(u"layout_norm")
        self.display_label = QLineEdit(self.widget_RGB)
        self.display_label.setObjectName(u"display_label")
        self.display_label.setReadOnly(True)

        self.layout_norm.addWidget(self.display_label)

        self.spacer_norm = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.layout_norm.addItem(self.spacer_norm)

        self.cbb_norm = QCheckBox(self.widget_RGB)
        self.cbb_norm.setObjectName(u"cbb_norm")

        self.layout_norm.addWidget(self.cbb_norm)


        self.verticalLayout.addLayout(self.layout_norm)


        self.layout_RGB_2.addWidget(self.widget_RGB)


        self.horizontalLayout.addLayout(self.layout_RGB_2)

        self.spacer1 = QSpacerItem(12, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.spacer1)

        self.widget = QWidget(self.widget_top)
        self.widget.setObjectName(u"widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QSize(100, 0))

        self.horizontalLayout.addWidget(self.widget)


        self.verticalLayout_2.addWidget(self.widget_top)

        self.spacer2 = QSpacerItem(0, 12, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_2.addItem(self.spacer2)

        self.layout_bottom = QHBoxLayout()
        self.layout_bottom.setObjectName(u"layout_bottom")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.layout_hex = QVBoxLayout()
        self.layout_hex.setObjectName(u"layout_hex")
        self.label = QLabel(ColorWidget)
        self.label.setObjectName(u"label")
        self.label.setIndent(12)

        self.layout_hex.addWidget(self.label)

        self.widget_hex = QWidget(ColorWidget)
        self.widget_hex.setObjectName(u"widget_hex")
        self.widget_hex.setStyleSheet(u"#widget_hex {\n"
"	background: #3e5b7a;\n"
"	border-radius: 12px;\n"
"}")
        self.horizontalLayout_2 = QHBoxLayout(self.widget_hex)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.edit_hex = QLineEdit(self.widget_hex)
        self.edit_hex.setObjectName(u"edit_hex")
        self.edit_hex.setMaximumSize(QSize(200, 16777215))

        self.horizontalLayout_2.addWidget(self.edit_hex)


        self.layout_hex.addWidget(self.widget_hex)


        self.verticalLayout_3.addLayout(self.layout_hex)

        self.spacer3 = QSpacerItem(20, 12, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_3.addItem(self.spacer3)

        self.layout_picker = QVBoxLayout()
        self.layout_picker.setObjectName(u"layout_picker")
        self.label_picker = QLabel(ColorWidget)
        self.label_picker.setObjectName(u"label_picker")
        self.label_picker.setIndent(12)

        self.layout_picker.addWidget(self.label_picker)

        self.btn_picker = QPushButton(ColorWidget)
        self.btn_picker.setObjectName(u"btn_picker")

        self.layout_picker.addWidget(self.btn_picker)

        self.spacer_bottom = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.layout_picker.addItem(self.spacer_bottom)


        self.verticalLayout_3.addLayout(self.layout_picker)


        self.layout_bottom.addLayout(self.verticalLayout_3)

        self.spacer4 = QSpacerItem(12, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.layout_bottom.addItem(self.spacer4)

        self.layout_builtins = QVBoxLayout()
        self.layout_builtins.setObjectName(u"layout_builtins")
        self.label_builtins = QLabel(ColorWidget)
        self.label_builtins.setObjectName(u"label_builtins")
        self.label_builtins.setIndent(12)

        self.layout_builtins.addWidget(self.label_builtins)

        self.scroll_area = QScrollArea(ColorWidget)
        self.scroll_area.setObjectName(u"scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area_widget = QWidget()
        self.scroll_area_widget.setObjectName(u"scroll_area_widget")
        self.scroll_area_widget.setGeometry(QRect(0, 0, 395, 217))
        self.scroll_area.setWidget(self.scroll_area_widget)

        self.layout_builtins.addWidget(self.scroll_area)


        self.layout_bottom.addLayout(self.layout_builtins)

        self.layout_bottom.setStretch(2, 1)

        self.verticalLayout_2.addLayout(self.layout_bottom)


        self.retranslateUi(ColorWidget)

        QMetaObject.connectSlotsByName(ColorWidget)
    # setupUi

    def retranslateUi(self, ColorWidget):
        ColorWidget.setWindowTitle(QCoreApplication.translate("ColorWidget", u"Color", None))
        self.label_RGB.setText(QCoreApplication.translate("ColorWidget", u"RGB", None))
        self.label_R.setText(QCoreApplication.translate("ColorWidget", u"R", None))
        self.edit_R.setText("")
        self.label_G.setText(QCoreApplication.translate("ColorWidget", u"G", None))
        self.edit_G.setText("")
        self.label_B.setText(QCoreApplication.translate("ColorWidget", u"B", None))
        self.edit_B.setText("")
        self.cbb_norm.setText(QCoreApplication.translate("ColorWidget", u"normalized form", None))
        self.label.setText(QCoreApplication.translate("ColorWidget", u"HEX", None))
        self.edit_hex.setText("")
        self.label_picker.setText(QCoreApplication.translate("ColorWidget", u"Color picker", None))
        self.btn_picker.setText(QCoreApplication.translate("ColorWidget", u"Open", None))
        self.label_builtins.setText(QCoreApplication.translate("ColorWidget", u"Builtins", None))
    # retranslateUi

