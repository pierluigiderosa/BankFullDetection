# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_bankfulldetection.ui'
#
# Created: Tue Jan 28 13:22:53 2014
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_BankFullDetection(object):
    def setupUi(self, BankFullDetection):
        BankFullDetection.setObjectName(_fromUtf8("BankFullDetection"))
        BankFullDetection.resize(423, 214)
        self.verticalLayout = QtGui.QVBoxLayout(BankFullDetection)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(BankFullDetection)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.comboVector = QtGui.QComboBox(BankFullDetection)
        self.comboVector.setObjectName(_fromUtf8("comboVector"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.comboVector)
        self.label_2 = QtGui.QLabel(BankFullDetection)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.comboDEM = QtGui.QComboBox(BankFullDetection)
        self.comboDEM.setObjectName(_fromUtf8("comboDEM"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.comboDEM)
        self.verticalLayout.addLayout(self.formLayout)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.formLayout_2 = QtGui.QFormLayout()
        self.formLayout_2.setObjectName(_fromUtf8("formLayout_2"))
        self.label_3 = QtGui.QLabel(BankFullDetection)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_3)
        self.stepXSspin = QtGui.QSpinBox(BankFullDetection)
        self.stepXSspin.setMaximum(10000)
        self.stepXSspin.setSingleStep(10)
        self.stepXSspin.setProperty("value", 50)
        self.stepXSspin.setObjectName(_fromUtf8("stepXSspin"))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.FieldRole, self.stepXSspin)
        self.label_4 = QtGui.QLabel(BankFullDetection)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_4)
        self.widthXSspin = QtGui.QSpinBox(BankFullDetection)
        self.widthXSspin.setMaximum(1000)
        self.widthXSspin.setProperty("value", 500)
        self.widthXSspin.setObjectName(_fromUtf8("widthXSspin"))
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.FieldRole, self.widthXSspin)
        self.horizontalLayout.addLayout(self.formLayout_2)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.genXSbtn = QtGui.QPushButton(BankFullDetection)
        self.genXSbtn.setObjectName(_fromUtf8("genXSbtn"))
        self.horizontalLayout.addWidget(self.genXSbtn)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.progressBar = QtGui.QProgressBar(BankFullDetection)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.verticalLayout.addWidget(self.progressBar)
        self.buttonBox = QtGui.QDialogButtonBox(BankFullDetection)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(BankFullDetection)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), BankFullDetection.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), BankFullDetection.reject)
        QtCore.QMetaObject.connectSlotsByName(BankFullDetection)

    def retranslateUi(self, BankFullDetection):
        BankFullDetection.setWindowTitle(QtGui.QApplication.translate("BankFullDetection", "Automatic Bankfull detection", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("BankFullDetection", "Vector layer", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("BankFullDetection", "DEM", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("BankFullDetection", "step of XS", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("BankFullDetection", "Width of XS", None, QtGui.QApplication.UnicodeUTF8))
        self.genXSbtn.setText(QtGui.QApplication.translate("BankFullDetection", "Generate XS", None, QtGui.QApplication.UnicodeUTF8))

