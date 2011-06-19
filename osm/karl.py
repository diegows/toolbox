#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Script that helps to map using the Karlsruhe Schema
#
# Diego Woitasen - <diego@woitasen.com.ar>
#
 
import sys
import math
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import OsmApi

class MiniWay(QLineF):
    DEST = 30
    LEFT = 0
    RIGHT = 1
    def __init__(self, lat1, long1, lat2, long2):
        super(MiniWay, self).__init__(QPointF(lat1, long1),
                                        QPointF(lat2, long2))

    def start_end(self):
        line_start = QLineF(self)
        line_end = QLineF(self.p2(), self.p1())

        return line_start, line_end
 
    def line(self, angle1 = 45, angle2 = 10, side = 0):
#Seguir probando esto, la idea es usar los angulos y la tangente
#para calcular la longitud del cateto que coincide con el highway
        line_start, line_end = self.start_end()
        hypotenuse = self.DEST / math.sin(math.radians(angle1))
        line_start.setLength(hypotenuse)
        hypotenuse = self.DEST / math.sin(math.radians(angle2))
        line_end.setLength(hypotenuse)
        if side == 0:
            line_start.setAngle(line_start.angle() + angle1)
            line_end.setAngle(line_end.angle() - angle2)
        else:
            line_start.setAngle(line_start.angle() - angle1)
            line_end.setAngle(line_end.angle() + angle2)

        return QLineF(line_start.x2(), line_start.y2(), 
                        line_end.x2(), line_end.y2())

    def right(self, angle1, angle2):
        return self.line(45, 45, self.LEFT)

    def left(self, angle1, angle2):
        return self.line(45, 45, self.RIGHT)


class Ways:
    #Simple (name, id) way list
    ways = False

    #Ways indexed by id
    ways_d = {}

    #Ways id indexed by node.
    node_ways = {}

    #Nodes
    nodes = {}

    @classmethod
    def get(cls, lat = False, long = False):
        if not Ways.ways:
            cls._get(lat, long)

        return cls.ways

    @classmethod
    def _get(cls, lat, long):
        #Get the highways 500 meters around of the given point.
        #100 meters is about 0.0009 degrees on latitude
        lat_shifted = lat + .0009 * 1
        line = QLineF(QPointF(lat, long), QPointF(lat_shifted, long))
        line.setAngle(135)
        lat1 = line.y2()
        long1 = line.x2()
        line.setAngle(315)
        lat2 = line.y2()
        long2 = line.x2()

        MyApi = OsmApi.OsmApi()
        data = MyApi.Map(lat1, long1, lat2, long2)
        ways = []
        for obj in data:
            if obj['type'] == 'way' and obj['data']['tag'].has_key('name'):
                try:
                    way_id = obj['data']['id']
                    way_info = '%s (%s)' % (obj['data']['tag']['name'],
                                    way_id)
                    ways.append((way_info, way_id))
                except:
                      print 'XXX', obj
                      
        cls.ways = ways

    @classmethod
    def _getAll(cls, wayIds):
        print wayIds
        for way_id in wayIds:
            if way_id in cls.ways_d.keys():
                wayIds.remove(way_id)

        MyApi = OsmApi.OsmApi()
        ways = MyApi.WaysGet(wayIds)
        cls.ways_d.update(ways)
        for id, data in ways.iteritems():
            for node in data['nd']:
                ways = MyApi.NodeWays(node)
                wayIds = []
                for way in ways:
                    try:
                        wayIds.append(way['id'])
                    except KeyError:
                        print 'XXX', way
                ways = MyApi.WaysGet(wayIds)
                cls.ways_d.update(ways)
                cls.node_ways[node] = ways.keys()

        #Get all current ways nodes
        nodes = []
        for id, data in cls.ways_d.iteritems():
            for node in data['nd']:
                nodes.append(node)

        cls.nodes = MyApi.NodesGet(nodes)

    @classmethod
    def getAll(cls, wayIds):
        #If wy try to get a lot of ways, the operation fails.
        #Get up to limit ways per call.
        limit = 3
        while len(wayIds) > 0:
            print wayIds
            cls._getAll(wayIds[:limit])
            del wayIds[:limit]


class WayItem(QStandardItem):
    def setId(self, id):
        self.way_id = id

    def getId(self):
        return self.way_id
 
class Karl(QDialog):
    def __init__(self, args):
        super(Karl, self).__init__()
 
        lat = float(args[1])
        long = float(args[2])
  
        self.setGeometry(200, 200, 800, 500)
        self.setWindowTitle('Address numbers helper')

        ways = Ways.get(lat, long)
        model = QStandardItemModel() 
        self.ways = []
        ways_id = []
        for way in ways:
            item = WayItem(way[0])
            item.setId(way[1])
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled) 
            item.setData(QVariant(Qt.Unchecked), Qt.CheckStateRole) 
            self.ways.append(item)
            model.appendRow(item) 
            ways_id.append(way[1])

        Ways.getAll(ways_id)
            
        way_list = QListView(self)
        way_list.setGeometry(QRect(0,0,200,500))
        way_list.setModel(model)

        way_layout = QBoxLayout(QBoxLayout.TopToBottom)
        way_layout.addWidget(QLabel('Select the ways to add addressing:'))
        way_layout.addWidget(way_list)

        addr_layout = QGridLayout()
        addr_layout.addWidget(QLabel('Addressing parameters:'), 0, 0)

        addr_layout.addWidget(QLabel('First number:'), 1, 0)
        self.start = QLineEdit()
        addr_layout.addWidget(self.start, 1, 1)

        addr_layout.addWidget(QLabel('Interval number:'), 3, 0)
        self.interval = QLineEdit()
        addr_layout.addWidget(self.interval, 3, 1)

        self.start_junction = QComboBox()
        for way in ways:
            self.start_junction.addItem(way[0], way[1])

        addr_layout.addWidget(QLabel('Start junction:'), 4, 0)
        addr_layout.addWidget(self.start_junction, 4, 1)

        self.end_junction = QComboBox()
        for way_id, way_data in Ways.ways_d.iteritems():
            self.end_junction.addItem(way_data['tag']['name'])

        addr_layout.addWidget(QLabel('# of blocks:'), 5, 0)
        self.blocks = QLineEdit()
        addr_layout.addWidget(self.blocks, 5, 1)

        button_ok = QPushButton('OK')
        button_cancel = QPushButton('Cancel')
        addr_layout.addWidget(button_ok, 6, 0)
        addr_layout.addWidget(button_cancel, 6, 1)

        self.connect(button_ok, SIGNAL("clicked()"),
                        self, SLOT('accept()'))
        self.connect(button_cancel, SIGNAL("clicked()"),
                        self, SLOT('reject()'))

        main_layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        main_layout.addLayout(way_layout)
        main_layout.addLayout(addr_layout)

    def accept(self):
        print 'ACCEPTED'

        index = self.start_junction.currentIndex()
        self.start_name = self.start_junction.itemData(index).toString()
        self.n_blocks = self.start.text()
        self.start_number = self.start.text()
        self.interval_number =  self.interval.text()
        print self.start_name, self.n_blocks, self.start_number, \
                self.interval_number

        wayIds = []
        for way in self.ways:
            if way.checkState() == Qt.Checked:
                wayIds.append(way.getId())
        Ways.getAll(wayIds)
        for way_id in wayIds:
            self.interpolate(way_id)

        #QDialog.accept(self)

    def in_range(self, node):
        for way in Ways.node_ways[node]:
            try:
                way_name = Ways.ways_d[way]['tag']['name']
            except KeyError:
                print 'ERROR: name tag missing'
                return False

            if self.in_range_f < 0 and way_name == self.start_name:
                self.in_range_f = 0
            elif self.in_range_f <= int(self.n_blocks):
                self.in_range_f = -1
            elif self.in_range_f >= 0:
                self.in_range_f += 1 

        return self.in_range_f

    def interpolate(self, way_id):
        way = Ways.ways_d[way_id]
        nodes = way['nd']
        self.in_range_f = -1
        for i in range(0, len(nodes) - 1):
            if not self.in_range(nodes[i]):
                continue

            print 'UUU'


    def reject(self):
        print 'REJECTED', self.interval.text()
        sys.exit(0)
 
    def paintEvent(self, e):
        qp = QPainter()
 
        qp.begin(self)        
        self.doDrawing(qp)        
        qp.end()
        
    def doDrawing(self, qp):
        miniway1 = MiniWay(600, 100, 400, 100)        

        pen = QPen(Qt.black, 2, Qt.SolidLine)
        qp.setPen(pen)

        qp.drawLine(miniway1)

        pen.setColor(Qt.blue)
        qp.setPen(pen)
        qp.drawLine(miniway1.right(45, 45))
        pen.setColor(Qt.yellow)
        qp.setPen(pen)
        qp.drawLine(miniway1.left(45, 45))

 
app = QApplication(sys.argv)
k = Karl(sys.argv)
k.show()
app.exec_()

