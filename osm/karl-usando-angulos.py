#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Script that helps to map using the Karlsruhe Schema
#
# Diego Woitasen - <diego@woitasen.com.ar>
#
 
import sys
import math
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QPointF, QLineF

class Highway(QLineF):
    def __init__(self, *args):
        super(Highway, self).__init__(*args)

    def setPoints(self, p1, p2):
        super(Highway, self).__init__(*args)

    def start_end(self):
        line_start = QLineF(self)
        line_end = QLineF(self.p2(), self.p1())
        line_start.setLength(30)
        line_end.setLength(30)

        return line_start, line_end
 
    def addr_line1(self):
        line_start, line_end = self.start_end()
        line_start.setAngle(line_start.angle() - 45)
        line_end.setAngle(line_end.angle() + 45)

        return QLineF(line_start.x2(), line_start.y2(), 
                        line_end.x2(), line_end.y2())

    def addr_line2(self):
        line_start, line_end = self.start_end()
        line_start.setAngle(line_start.angle() + 45)
        line_end.setAngle(line_end.angle() - 45)

        return QLineF(line_start.x2(), line_start.y2(), 
                        line_end.x2(), line_end.y2())

 
class Karl(QtGui.QWidget):
  
    def __init__(self):
        super(Karl, self).__init__()
 
        self.setGeometry(200, 200, 400, 500)
        self.setWindowTitle('penstyles')
 
    def paintEvent(self, e):
      
        qp = QtGui.QPainter()
 
        qp.begin(self)        
        self.doDrawing(qp)        
        qp.end()
        
    def doDrawing(self, qp):
        highway = Highway(QPointF(300, 300), QPointF(10, 100))        
        highway1 = Highway(QPointF(10, 100), QPointF(10, 300))        

        pen = QtGui.QPen(QtCore.Qt.black, 2, QtCore.Qt.SolidLine)
        qp.setPen(pen)

        qp.drawLine(highway)
        qp.drawLine(highway1)

        pen.setColor(QtCore.Qt.blue)
        qp.setPen(pen)
        qp.drawLine(highway.addr_line1())

        pen.setColor(QtCore.Qt.green)
        qp.setPen(pen)
        qp.drawLine(highway.addr_line2())

 
app = QtGui.QApplication(sys.argv)
k = Karl()
k.show()
app.exec_()

