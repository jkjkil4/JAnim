# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AnimViewer.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
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
from PySide6.QtWidgets import (QApplication, QSizePolicy, QSlider, QVBoxLayout,
    QWidget)

from janim.gui.glwidget import GLWidget

class Ui_AnimViewer(object):
    def setupUi(self, AnimViewer):
        if not AnimViewer.objectName():
            AnimViewer.setObjectName(u"AnimViewer")
        AnimViewer.resize(400, 300)
        self.verticalLayout = QVBoxLayout(AnimViewer)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.glw = GLWidget(AnimViewer)
        self.glw.setObjectName(u"glw")

        self.verticalLayout.addWidget(self.glw)

        self.progressSilder = QSlider(AnimViewer)
        self.progressSilder.setObjectName(u"progressSilder")
        self.progressSilder.setOrientation(Qt.Horizontal)

        self.verticalLayout.addWidget(self.progressSilder)


        self.retranslateUi(AnimViewer)

        QMetaObject.connectSlotsByName(AnimViewer)
    # setupUi

    def retranslateUi(self, AnimViewer):
        AnimViewer.setWindowTitle(QCoreApplication.translate("AnimViewer", u"AnimViewer", None))
    # retranslateUi

