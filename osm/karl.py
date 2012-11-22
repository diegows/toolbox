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
from OsmApi import OsmApi
import bsddb
from copy import copy

class OsmObject(object):
    def __init__(self, osm_data = None):
        """osm_data is the osm dictionary returned by OsmApi functions."""
        if not hasattr(self, 'osm_attrs'):
            self.osm_attrs = []
        self.osm_attrs += [ 'id', 'user', 'uid', 'timestamp', 'visible',
                            'version', 'changeset' ]

        if osm_data:
            self.load_osm_data(osm_data)

    def load_osm_data(self, osm_data):
        self.osm_data = osm_data
        for attr in self.osm_attrs:
            setattr(self, attr, osm_data[attr])

        self.tags = osm_data.setdefault('tag', {})

    def get_tag(self, name):
        if name in self.tags:
            return self.tags[name]
        else:
            return False


class OsmNode(OsmObject):
    def __init__(self, osm_data = None):
        self.osm_attrs = [ 'lat', 'lon' ]
        super(OsmNode, self).__init__(osm_data)

    def load_osm_data(self, osm_data):
        super(OsmNode, self).load_osm_data(osm_data)

    def get_adjacent_nodes(self):
        ways = osm_api.NodeWays(self.id)
        self.adjacent_nodes = []
        ways = osm_api.WaysGet(ways)
        for way in ways:
            for node in enumerate(way.nodes):
                if node[1] == self.id:
                    if node[0] > 0:
                        self.adjacent_nodes.append(way.nodes[node[0]-1])
                    if node[0] < len(way.nodes)-1:
                        self.adjacent_nodes.append(way.nodes[node[0]+1])

    def q_point(self):
        return QPointF(self.lon, self.lat)

class OsmWay(OsmObject):
    def __init__(self, osm_data = None):
        super(OsmWay, self).__init__(osm_data)

    def load_osm_data(self, osm_data):
        super(OsmWay, self).load_osm_data(osm_data)

        if osm_data.has_key('nd'):
            self.nodes = osm_data['nd']


class MyOsmApi(OsmApi):
    def __init__(self, *args, **kwargs):
        super(MyOsmApi, self).__init__(*args, **kwargs)
        self.ways_cache = {}
        self.nodes_cache = {}
        self.nodes_ways_cache = {}

    def NodeWays(self, node_id):
        if self.nodes_ways_cache.has_key(node_id):
            return self.nodes_ways_cache[node_id]

        ways = super(MyOsmApi, self).NodeWays(node_id)
        way_ids = []
        for way in ways:
            way_ids.append(way['id'])
        #cache ways here. I don't remember why I did this, review! :P
        self.WaysGet(way_ids)
        self.nodes_ways_cache[node_id] = way_ids

        return way_ids

    def WayGet(self, way_id):
        if self.ways_cache.has_key(way_id):
            return self.ways_cache[way_id]

        way = super(MyOsmApi, self).WayGet(way_id)
        way = OsmWay(way)
        self.ways_cache[way_id] = way
        return way

    def NodeGet(self, node_id):
        if self.nodes_cache.has_key(node_id):
            return self.nodes_cache[node_id]

        node = super(MyOsmApi, self).NodeGet(node_id)
        node = OsmNode(node)
        self.nodes_cache[node_id] = node
        return node

    def NodesGet(self, node_ids):
        node_ids = copy(node_ids)
        nodes = []
        for node_id in node_ids:
            if self.nodes_cache.has_key(node_id):
                nodes.append(self.nodes_cache[node_id])
                node_ids.remove(node_id)

        if len(node_ids) > 0:
            osm_nodes = super(MyOsmApi, self).NodesGet(node_ids)
            for node_id, node_data in osm_nodes.iteritems():
                node = OsmNode(node_data)
                self.nodes_cache[node_id] = node
                nodes.append(node)

        return nodes

    def WaysGet(self, way_ids):
        way_ids = copy(way_ids)
        ways = []
        for way_id in way_ids:
            if self.ways_cache.has_key(way_id):
                ways.append(self.ways_cache[way_id])
                way_ids.remove(way_id)

        if len(way_ids) > 0:
            osm_ways = super(MyOsmApi, self).WaysGet(way_ids)
            for way_id, way_data in osm_ways.iteritems():
                way = OsmWay(way_data)
                self.ways_cache[way_id] = way
                ways.append(way)

        return ways



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


osm_api = MyOsmApi()
DEST = 30

def get_nodes(node1, node2, line):
    max_angle = 0
    min_angle = 360
    left1 = None
    right1 = None
    for adj_node in node1.adjacent_nodes:
        if node2.id == adj_node:
            continue
        adj_node_obj = osm_api.NodeGet(adj_node)
        line_node = QLineF(node1.q_point(), adj_node_obj.q_point())
        angle = line.angleTo(line_node)
        if angle < min_angle:
            min_angle = angle
            right1 = adj_node
        if angle > max_angle:
            max_angle = angle
            left1 = adj_node

    print node1.id, left1, right1

    angle_left = (max_angle / 2) - 10
    angle_right = (min_angle / 2) + 10

    hypo_len_left = DEST / math.sin(math.radians(angle_left))
    hypo_len_right = DEST / math.sin(math.radians(angle_right))

    line_left = QLineF(line)
    line_left.setLength(hypo_len_left)
    line_right = QLineF(line)
    line_right.setLength(hypo_len_right)

    line_left.setAngle(line_left.angle() + angle_left)
    line_right.setAngle(line_right.angle() + angle_right)
    
    return (line_left.x2, line_left.y2), (line_right.x2, line_right.y2)


def draw_lines(node1, node2):
    node1 = osm_api.NodeGet(node1)
    node2 = osm_api.NodeGet(node2)
    print 'NODES:', node1.id, node2.id

    line1 = QLineF(node1.q_point(), node2.q_point())
    line2 = QLineF(node2.q_point(), node1.q_point())

    node1_nodes = get_nodes(node1, node2, line1)
    node2_nodes = get_nodes(node2, node1, line2)
    print 'NODE1 - nodes:', node1_nodes
    print 'NODE2 - nodes:', node2_nodes
    #raise NameError("Continuar aca")
#XXX: ya tengo los nodos para dibujar las rectas, auqnue hay que probarlo.
#los nodos del karl. Tomar en cuenta como las intersecciones en T o
#los nodos que solo son para hacer una curva en el camino

def do_karl(first_node, last_node):
    first_node = int(first_node)
    last_node = int(last_node)
    ways_first = osm_api.NodeWays(first_node)
    ways_last = osm_api.NodeWays(last_node)

    print ways_first
    print ways_last

    way = False
    for way_i in ways_first:
        if way_i in ways_last:
            way = osm_api.WayGet(way_i)
            break

    if not way:
        raise NameError("Nodes don't belong to the same way")
    
    #Build the sequence of nodes in the order specified by the user
    #This order could be different in the OSM DB, we could reverse it
    node_ids = way.nodes
    first_index = node_ids.index(first_node)
    last_index = node_ids.index(last_node)
    if last_index < first_index:
        node_ids = node_ids[last_index:first_index + 1]
        node_ids.reverse()
    else:
        node_ids = node_ids[first_index:last_index + 1]

    #We need all the adjacents node to calculate the nodes of the ways
    #of the KarlShrue schema
    nodes = osm_api.NodesGet(node_ids)
    for node in nodes:
        node.get_adjacent_nodes()

    print node_ids
    for index in range(len(node_ids)-1):
        draw_lines(node_ids[index], node_ids[index+1])

    return True

class Karl(QDialog):
    def __init__(self, args):
        super(Karl, self).__init__()
 
        self.setGeometry(200, 200, 400, 200)
        self.setWindowTitle('Address numbers helper')

        main_layout = QGridLayout(self)

        main_layout.addWidget(QLabel('First node: '), 0, 0)
        self.first = QLineEdit()
        main_layout.addWidget(self.first, 0, 1)
        if len(args) >= 2:
            self.first.setText(args[1])

        main_layout.addWidget(QLabel('Last node: '), 1, 0)
        self.last = QLineEdit()
        main_layout.addWidget(self.last, 1, 1)
        if len(args) >= 3:
            self.last.setText(args[2])

        button_ok = QPushButton('OK')
        button_cancel = QPushButton('Cancel')
        main_layout.addWidget(button_ok, 2, 0)
        main_layout.addWidget(button_cancel, 2, 1)

        self.connect(button_ok, SIGNAL("clicked()"),
                        self, SLOT('accept()'))
        self.connect(button_cancel, SIGNAL("clicked()"),
                        self, SLOT('reject()'))

    def accept(self):
        print 'ACCEPTED', self.first.text(), self.last.text()
        do_karl(self.first.text(), self.last.text())

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
        print 'REJECTED'
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

