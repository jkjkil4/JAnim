# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ToolkitWidget.ui'
##
## Created by: Qt User Interface Compiler version 6.5.2
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QLayout, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QStackedWidget, QVBoxLayout,
    QWidget)

class Ui_ToolkitWidget(object):
    def setupUi(self, ToolkitWidget):
        if not ToolkitWidget.objectName():
            ToolkitWidget.setObjectName(u"ToolkitWidget")
        ToolkitWidget.resize(373, 123)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ToolkitWidget.sizePolicy().hasHeightForWidth())
        ToolkitWidget.setSizePolicy(sizePolicy)
        ToolkitWidget.setMinimumSize(QSize(300, 0))
        self.verticalLayout = QVBoxLayout(ToolkitWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetMinimumSize)
        self.horLayoutSelect = QHBoxLayout()
        self.horLayoutSelect.setObjectName(u"horLayoutSelect")
        self.labelSelect = QLabel(ToolkitWidget)
        self.labelSelect.setObjectName(u"labelSelect")

        self.horLayoutSelect.addWidget(self.labelSelect)

        self.cbbSelect = QComboBox(ToolkitWidget)
        self.cbbSelect.addItem("")
        self.cbbSelect.setObjectName(u"cbbSelect")
        sizePolicy1 = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.cbbSelect.sizePolicy().hasHeightForWidth())
        self.cbbSelect.setSizePolicy(sizePolicy1)

        self.horLayoutSelect.addWidget(self.cbbSelect)

        self.horSpacerSelect = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horLayoutSelect.addItem(self.horSpacerSelect)


        self.verticalLayout.addLayout(self.horLayoutSelect)

        self.line = QFrame(ToolkitWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.stkWidget = QStackedWidget(ToolkitWidget)
        self.stkWidget.setObjectName(u"stkWidget")
        self.pageChildrenIndexViewer = QWidget()
        self.pageChildrenIndexViewer.setObjectName(u"pageChildrenIndexViewer")
        self.verticalLayout_2 = QVBoxLayout(self.pageChildrenIndexViewer)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setSizeConstraint(QLayout.SetMinimumSize)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.editCIV = QLineEdit(self.pageChildrenIndexViewer)
        self.editCIV.setObjectName(u"editCIV")

        self.verticalLayout_2.addWidget(self.editCIV)

        self.horLayoutCIV = QHBoxLayout()
        self.horLayoutCIV.setObjectName(u"horLayoutCIV")
        self.btnCIVClear = QPushButton(self.pageChildrenIndexViewer)
        self.btnCIVClear.setObjectName(u"btnCIVClear")

        self.horLayoutCIV.addWidget(self.btnCIVClear)

        self.horSpacerCIV = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horLayoutCIV.addItem(self.horSpacerCIV)


        self.verticalLayout_2.addLayout(self.horLayoutCIV)

        self.stkWidget.addWidget(self.pageChildrenIndexViewer)
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.stkWidget.addWidget(self.page_2)

        self.verticalLayout.addWidget(self.stkWidget)


        self.retranslateUi(ToolkitWidget)

        QMetaObject.connectSlotsByName(ToolkitWidget)
    # setupUi

    def retranslateUi(self, ToolkitWidget):
        ToolkitWidget.setWindowTitle(QCoreApplication.translate("ToolkitWidget", u"ToolkitWidget", None))
        self.labelSelect.setText(QCoreApplication.translate("ToolkitWidget", u"\u9009\u62e9\u529f\u80fd", None))
        self.cbbSelect.setItemText(0, QCoreApplication.translate("ToolkitWidget", u"\u67e5\u770b\u5b50\u7269\u4ef6\u5e8f\u53f7", None))

        self.btnCIVClear.setText(QCoreApplication.translate("ToolkitWidget", u"\u6e05\u7a7a", None))
    # retranslateUi

