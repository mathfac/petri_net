#!/usr/bin/python
# -*- coding: utf-8 -*-

import wx
import traceback
import time
import petri
import vector_2d as vec2d
import itertools
import json
import collections
import wx.lib.buttons as buttons
from petrigui.dialog_fields import DialogFields, place_ranged 
import serializable
from collections import OrderedDict




if __name__ == '__main__':
    app = wx.App(False)

BLUE_PEN = wx.Pen('BLUE', 1)

def draw_text(dc, text, center_x, center_y):
    """ Draws text, given text center """
    tw, th = dc.GetTextExtent(text)
    dc.DrawText(text, (center_x-tw/2),  (center_y-th/2))
    
def draw_unique_id(dc, unique_id, left_x, top_y):
    """ Draws element label, given topleft coordinates. """
    tw, th = dc.GetTextExtent(unique_id)
    dc.DrawText(unique_id, left_x-tw, top_y-th)
    
def rectangles_intersect(rect1, rect2):
    """ Detects, whtether one rectangles intersects with another (including their square) """
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    #print rect1,rect2
    separate = r1 < l2 or l1 > r2 or t1>b2 or b1<t2
    #print separate
    return not separate 



class ElementPropertiesDialog(wx.Dialog):
    def __init__(self, parent, window_id, title, obj, fields):
        self.fields = collections.OrderedDict()
        for field, value in fields:
            self.fields[field] = value
        self.obj = obj
        super(ElementPropertiesDialog, self).__init__(parent, window_id, title)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.result = {} #
        
        sb = wx.StaticBox(self, label=title)
        sbs = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)
        self.InitUI(sbs)

        sizer.Add(sbs, border=5, proportion=1, flag=wx.ALL|wx.EXPAND)
        
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, wx.ID_OK, label='Ok')
        closeButton = wx.Button(self, wx.ID_CANCEL, label='Cancel')
        hbox2.Add(okButton)
        hbox2.Add(closeButton, flag=wx.LEFT, border=5)
        sizer.Add(hbox2, 
            flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        closeButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        
        
        self.SetSizer(sizer)
        self.Fit()
        
    def OnOk(self, event):
        for field_name, (label, getter, setter) in self.fields.iteritems():
            control = self.field_controls[field_name]
            value = setter(control)
            self.result[field_name] = value
            if getattr(self.obj, field_name, None) == value:
                continue
            checker = getattr(self.obj, 'check_update_'+field_name, None)
            if checker:
                try:
                    checker(value)
                except Exception, e:
                    error = getattr(e,'message','')
                    error = '\n'+error if error else error
                    wx.MessageBox("Incorrect value for field %s.%s"%(field_name, error))
                    return
        self.UpdateObjectValues()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
        
    def UpdateObjectValues(self):
        for field, value in self.result.iteritems():
            if getattr(self.obj, field, None) != value:
                updater = getattr(self.obj, 'update_'+field, None)
                if updater is not None:
                    updater(value)
                else:
                    setattr(self.obj, field, value)
        
    def OnCancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)
        
    def InitUI(self, sizer):
        self.field_controls = {}
        for field_name, (label, getter, setter) in self.fields.iteritems():
            value = getattr(self.obj, field_name, '')
            self.result[field_name] = value
            hbox1 = wx.BoxSizer(wx.HORIZONTAL)
            hbox1.Add(wx.StaticText(self, label=label))
            control = getter(self, value)
            hbox1.Add(control, flag=wx.LEFT, border=5, )
            self.field_controls[field_name] = control
            sizer.Add(hbox1)
            

    
class PositionMixin(object):
    def __init__(self, *args, **kwargs):
        self.pos_x, self.pos_y = kwargs.get('pos_x', 0), kwargs.get('pos_y', 0)
        super(PositionMixin, self).__init__(*args, **kwargs)
        
    def set_position(self, x, y):
        self.pos_x = x # - (x%7)
        self.pos_y = y # - (y%7) # lol grid
        
    def get_position(self):
        return self.pos_x, self.pos_y
    
    def prepare_to_move(self):
        self.memo_x, self.memo_y = self.pos_x, self.pos_y
        
    def move_diff(self, diff_x, diff_y):
        new_x = self.memo_x + diff_x
        new_y = self.memo_y + diff_y
        self.set_position(new_x, new_y)
        
class SelectionMixin(object):
    def __init__(self, *args, **kwargs):
        self.selected = False
        self.temporary_selected = False
        self.temporary_discarded = False
        super(SelectionMixin, self).__init__(*args, **kwargs)
        
    @property
    def is_selected(self):
        return False if self.temporary_discarded else self.selected or self.temporary_selected
        
    def unselect_temporary(self):
        self.temporary_discarded = self.temporary_selected = False
        
    def set_selected(self, selected):
        if not selected:
            self.unselect_temporary()
        self.selected = selected
        

class ObjectLabel(SelectionMixin, serializable.Serializable):
    diff_x_to_serialize = True
    diff_y_to_serialize = True
    
    def __init__(self, obj, x=0, y=0):
        self.obj = obj
        self.diff_x = x
        self.diff_y = y
        self.rectangle = None
        
    def draw(self, dc):
        text = str(self.obj.unique_id)
        obj_x, obj_y = self.obj.get_position()
        self.draw_text(dc, text, obj_x + self.diff_x, obj_y + self.diff_y)
        
    def draw_text(self, dc, text, left_x, top_y):
        tw, th = dc.GetTextExtent(text)
        x1, y1 = left_x-tw, top_y-th
        x2, y2 = x1 + tw, y1 + th
        self.rectangle = (x1, y1, x2, y2)
        dc.DrawText(text,  x1, y1)
        
    def contains_point(self, x, y):
        x1, y1, x2, y2 = self.rectangle
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def prepare_to_move(self):
        self.memo_diff_x = self.diff_x
        self.memo_diff_y = self.diff_y
    
    def in_rect(self, lx, ly, tx, ty):
        pass
    
    def move_diff(self, diff_x, diff_y):
        self.diff_x = self.memo_diff_x + diff_x
        self.diff_y = self.memo_diff_y + diff_y

class GUIPlace(PositionMixin, SelectionMixin, petri.Place):
    pos_x_to_serialize = True
    pos_y_to_serialize = True
    radius_to_serialize = True
    
    def __init__(self, net, unique_id=None, tokens=0, position=None):
        """
        unique_id - unique identifier (hash if None)
        tokens - number of tokens in initial marking
        """
        super(GUIPlace, self).__init__(net=net, unique_id=unique_id, tokens=tokens)
        self.radius = 14
        self.label = ObjectLabel(self, -self.radius, -self.radius)
           
    def label_to_json_struct(self):
        return self.label.to_json_struct()
    
    def label_from_json_struct(self, label_obj, **kwargs):
        return ObjectLabel.from_json_struct(label_obj, constructor_args=dict(obj=self), **kwargs)
           
    def draw(self, dc):
        if self.is_selected:
            dc.SetPen(BLUE_PEN)
        else:
            dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawCircle(self.pos_x, self.pos_y, self.radius)
        if self.tokens>4:
            draw_text(dc, str(self.tokens), self.pos_x, self.pos_y)
        elif self.tokens>0:
            self.draw_tokens(dc)        
    def draw_tokens(self, dc):
        #This sucks, but who cares
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        tokens_r = self.radius/3
        tokens_offset = self.radius/2.8
        if self.tokens==1:
            dc.DrawCircle(self.pos_x, self.pos_y, tokens_r)
        elif self.tokens==2:
            dc.DrawCircle(self.pos_x-tokens_offset, self.pos_y, tokens_r)
            dc.DrawCircle(self.pos_x + tokens_offset, self.pos_y, tokens_r)
        elif self.tokens==3:
            dc.DrawCircle(self.pos_x-tokens_offset, self.pos_y+tokens_r, tokens_r)
            dc.DrawCircle(self.pos_x + tokens_offset, self.pos_y+tokens_r, tokens_r)
            dc.DrawCircle(self.pos_x, self.pos_y-tokens_r, tokens_r)
        elif self.tokens==4:
            for x_diff in xrange(0,2):
                x_diff = (x_diff*2-1)*tokens_offset
                for y_diff in xrange(0,2):
                    y_diff = (y_diff*2-1)*tokens_offset
                    dc.DrawCircle(self.pos_x+x_diff, self.pos_y+y_diff, tokens_r)

        
    def contains_point(self, x, y):
        x_diff = self.pos_x - x
        y_diff = self.pos_y - y
        return x_diff**2 + y_diff**2 <= self.radius**2
    
    def in_rect(self, lx, ly, tx, ty):
        r = self.radius
        bounding_rect = (self.pos_x-r, self.pos_y-r, self.pos_x+r, self.pos_y+r)
        return rectangles_intersect(bounding_rect, (lx, ly, tx, ty))
    
    def get_begin(self, arc):
        pos = vec2d.Vec2d(self.get_position())
        vec = vec2d.Vec2d(arc.get_point_next_to(self)) - pos
        pos += vec.normalized()*self.radius
        return pos
    
    def get_end(self, arc):
        pos = vec2d.Vec2d(self.get_position())
        vec = vec2d.Vec2d(arc.get_point_next_to(self)) - pos
        pos += vec.normalized()*self.radius
        return pos
    
    
    
    def open_properties_dialog(self, parent):
        fields = [ ('unique_id', DialogFields.unique_id),
                   ('tokens', place_ranged('Tokens', minimum=0)),
                   ('radius', place_ranged('Radius', minimum=5))
                   ]
        dia = ElementPropertiesDialog(parent, -1, 'Place properties', obj=self, fields=fields)
        dia.ShowModal()
        dia.Destroy()      
        
    def check_update_unique_id(self, value):
        if value in self.net.places:
            raise ValueError, "A place with such name already exists"
        
    def update_unique_id(self, value):
        self.net.rename_place(from_name=self.unique_id, to_name=value)
        
class GUIArc(SelectionMixin, PositionMixin, petri.Arc): #PositionMixin is just a stub
    
    INSERT_POINT = wx.NewId()
    REMOVE_POINT = wx.NewId()
    
    def __init__(self, net, place=None, transition=None, weight=1):
        super(GUIArc, self).__init__(net=net, place=place, transition=transition, weight=weight)
        self.tail_length = 10
        self.tail_angle = 15
        line_width = 2
        self.line_pen = wx.Pen(wx.BLACK, line_width)
        self.line_selected_pen = wx.Pen("Blue", line_width)
        self.begin = self.end = None
        self.points = []
        self.points_selected = 0
        #
        self.menu_fields = OrderedDict()
        self.menu_fields[GUIArc.INSERT_POINT] = ('Insert point', self.menu_insert_point)
        self.menu_fields[GUIArc.REMOVE_POINT] = ('Remove point', self.menu_remove_point)
        
    def points_to_json_struct(self):
        return [point.get_position() for point in self.points]
    
    def points_from_json_struct(self, points_obj, **kwargs):
        points = []
        for point in points_obj:
            arc_point = ArcPoint(self)
            arc_point.set_position(*point)
            points.append(arc_point)
        return points
        
    def select_line_pen(self, dc):
        if self.is_selected:
            dc.SetPen(self.line_selected_pen)
        else:
            dc.SetPen(self.line_pen)
            
    def draw(self, dc):
        self.select_line_pen(dc)
        fr = self.place
        to = self.transition
        if self.weight<0:
            fr, to = to, fr
        fr_begin = fr.get_begin(self)
        to_end = to.get_end(self)
        self.begin = fr_begin
        self.end = to_end
        for fr, to in self._iter_segments():
            self.draw_segment(dc, fr, to)
            fr_begin = fr
        fr_begin = vec2d.Vec2d(fr_begin)
        self.draw_arrow(dc, fr_begin, to_end)
        if abs(self.weight)>1:
            self.draw_label(dc)
            
    def draw_label(self, dc):
        point, direction = self.get_center()
        label = str(abs(self.weight))
        label_x = point[0]
        label_y = point[1]
        tw,th = dc.GetTextExtent(label)
        label_vec_perp = direction.perpendicular_normal()*max(th,tw)*0.8
        draw_text(dc, label, label_x+label_vec_perp[0], label_y+label_vec_perp[1])
        
    def get_center(self):
        length = 0.
        for a,b in self._iter_segments():
            a, b = vec2d.Vec2d(a), vec2d.Vec2d(b)
            length += a.get_distance(b)
        new_length = 0
        half_length = length / 2.
        for a,b in self._iter_segments():
            a, b = vec2d.Vec2d(a), vec2d.Vec2d(b)
            dist = a.get_distance(b)
            new_length += dist
            if new_length > half_length:
                redundancy = new_length - half_length
                dist_proportion = (dist - redundancy) / dist
                resulting_vec = b - a
                return a + resulting_vec*dist_proportion, resulting_vec
                
    def draw_segment(self, dc, fr, to):
        x1, y1 = fr[0], fr[1]
        x2, y2 = to[0], to[1]
        self.select_line_pen(dc)
        dc.DrawLine(x1, y1, x2, y2)
        
    def draw_arrow(self, dc, fr, to):
        end_x, end_y = to[0], to[1]
        vec = -(to - fr)
        vec = vec.normalized()
        tail_1 = vec.rotated(self.tail_angle) * self.tail_length
        tail_2 = vec.rotated(-self.tail_angle) * self.tail_length
        dc.DrawLine(end_x, end_y, end_x+tail_1[0], end_y+tail_1[1])
        dc.DrawLine(end_x, end_y, end_x+tail_2[0], end_y+tail_2[1])
        
    def get_point_next_to(self, obj):
        index = 0 if self.weight>0 else -1
        if obj==self.place:
            next_obj = self.points[index] if self.points else self.transition
        elif obj==self.transition:
            next_obj = self.points[-1-index] if self.points else self.place
        return next_obj.get_position()
        
    def contains_point(self, x, y):
        segment = self.get_segment_nearest_to_point(x, y, self.line_pen.GetWidth())
        return segment is not None
    
    def get_segment_nearest_to_point(self, x, y, maximum_distnace):
        """ Returns  (a,b) tuple, where a and b are points """
        if self.begin is None or self.end is None:
            return None
        for fr, to in self._iter_segments():
            x1, y1 = fr[0], fr[1]
            x2, y2 = to[0], to[1]
            distance = vec2d.dist(x1, y1, x2, y2, x, y)
            if distance <= maximum_distnace:
                return (fr, to)
        return None
    
    
    def _iter_points(self, include_first=True):
        """ Returns object that provide a[0] a[1], this generator returns vectors and tuples."""
        if include_first:
            yield self.begin
        for point in self.points:
            yield point.get_position()
        yield self.end
         
    def _iter_segments(self):
        for a,b in itertools.izip(self._iter_points(), self._iter_points(include_first=False)):
            yield a,b   
    
    def in_rect(self, lx, ly, tx, ty):
        for a,b in self._iter_segments():

            x1,y1 = a[0],a[1]
            x2,y2 = b[0],b[1]
            if vec2d.rectangle_intersects_line((x1,y1), (x2, y2), (lx, ly, tx, ty)):
                return True
        return False
    
    def open_properties_dialog(self, parent):
        fields = [ 
                   ('weight', place_ranged('Weight', minimum=1))
                   ]
        dia = ElementPropertiesDialog(parent, -1, 'Arc properties', obj=self, fields=fields)
        dia.ShowModal()
        dia.Destroy()      

    def update_weight(self, value):
        if self.weight < 0:
            value = -value
        self.weight = value
        
    def spawn_context_menu(self, parent, event):
        self.menu_event = event
        menu = wx.Menu()
        for event_id, (name, handler) in self.menu_fields.iteritems():
            menu.Append(event_id, name)
            parent.Bind(wx.EVT_MENU, handler, id=event_id)
        parent.PopupMenu(menu, event.GetPositionTuple())
        menu.Destroy()
        for event_id, (name, handler) in self.menu_fields.iteritems():
            parent.Unbind(wx.EVT_MENU, id=event_id)
        parent.Refresh()
        
    def menu_insert_point(self, event):
        x,y = self.menu_event.GetPositionTuple()
        a,b = self.get_segment_nearest_to_point(x, y, self.line_pen.GetWidth())
        arc_point = ArcPoint(self)
        arc_point.set_position(x, y)
        try:
            ind = self.points.index(a)
        except:
            ind = 0
        self.points.insert(ind, arc_point)
        
        
        
    def menu_remove_point(self, event):
        #remove me later, just for test
        print "HI", self

            
        
class ArcPoint(SelectionMixin, PositionMixin):
    def __init__(self, arc):
        super(ArcPoint, self).__init__()
        self.arc = arc
        self.width = 7
        self.height = 7
        
    def get_rectangle(self):
        x,y = self.pos_x, self.pos_y
        w,h = self.width,self.height
        return x-w/2,y-h/2,w,h
    
    def set_selected(self, selected):
        previous = self.is_selected
        super(ArcPoint, self).set_selected(selected)
        new = self.is_selected
        if new and not previous:
            self.arc.points_selected+=1
        elif previous and not new:
            self.arc.points_selected -=1
        
        
    
    def contains_point(self, x, y):
        r_x,r_y,r_w,r_h = self.get_rectangle()
        return (r_x <= x <= r_x+r_w) and (r_y <= y <= r_y+r_h)
    
    def in_rect(self, lx, ly, tx, ty):
        x, y, w, h = self.get_rectangle()
        return rectangles_intersect((x, y, x+w, y+h), (lx, ly, tx, ty))
    
    def draw(self, dc):
        if not self.arc.points_selected and not self.arc.is_selected:
            return 
        x, y, w, h = self.get_rectangle()
        if self.selected:
            dc.SetPen(BLUE_PEN)
        else:
            dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(x, y, w, h)
        
        
class GUITransition(PositionMixin, SelectionMixin, petri.Transition):
    ARC_CLS = GUIArc
    
    pos_x_to_serialize = True
    pos_y_to_serialize = True
    width_to_serialize = True
    height_to_serialize = True
    
    def __init__(self, unique_id=None, position=None, input_arcs=None, output_arcs=None, net=None):
        super(GUITransition,self).__init__(unique_id=unique_id, input_arcs=input_arcs, output_arcs=output_arcs, net=net)
        self.pos_x, self.pos_y = position or (0,0)
        self.width_coef = 0.9
        self.height_coef = 0.5
        self._width = self._height = 0
        self.width = 50
        self.height = 20
        
        self.side_slots = []
        self.main_angle = 90
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1), ]
        self.label = ObjectLabel(self, 0, -10)
        
    def label_to_json_struct(self):
        return self.label.to_json_struct()
    
    def label_from_json_struct(self, label_obj, **kwargs):
        return ObjectLabel.from_json_struct(label_obj, constructor_args=dict(obj=self), **kwargs)

        
    def __set_width(self, width):
        self._width = width
        self.width_start = self._width * (1-self.width_coef) / 2.
        self.width_range = self._width * self.width_coef
        self.update_main_angle()
        
    def update_main_angle(self):
        self.main_angle = 180*self._height/(self._width + self._height)
        
    def __set_height(self, height):
        self._height = height
        self.height_start = self._height * (1-self.height_coef) /2.
        self.height_range = self._height * self.height_coef
        self.update_main_angle()
        
    def __get_width(self):
        return self._width
    
    def __get_height(self):
        return self._height
    
    width = property(__get_width, __set_width)
    height = property(__get_height, __set_height)
        
    def rotate(self):
        self.width, self.height = self.height, self.width
        
    def draw(self, dc):
        self.precalculate_arcs()
        rect = self.get_rectangle()
        x,y,w,h = rect
        if self.is_enabled:
            dc.SetBrush(wx.RED_BRUSH)
            dc.SetPen(wx.RED_PEN)
        else:
            dc.SetBrush(wx.BLACK_BRUSH)
            dc.SetPen(wx.BLACK_PEN)
        if self.is_selected:
            dc.SetPen(BLUE_PEN)
        #dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(x,y,w,h)
        
    def get_rectangle(self):
        x,y = self.pos_x, self.pos_y
        w,h = self.width,self.height
        return x-w/2,y-h/2,w,h
    
    def contains_point(self, x, y):
        r_x,r_y,r_w,r_h = self.get_rectangle()
        return (r_x <= x <= r_x+r_w) and (r_y <= y <= r_y+r_h)
    
    def in_rect(self, lx, ly, tx, ty):
        x, y, w, h = self.get_rectangle()
        return rectangles_intersect((x, y, x+w, y+h), (lx, ly, tx, ty))
    
    def get_begin(self, arc):
        return self.get_touch_point(arc)
    
    def get_end(self, arc):
        return self.get_touch_point(arc)
    
    def get_touch_point(self, arc):
        result = vec2d.Vec2d(self.get_position())
        order, total_order, direction = self.side_slots[arc]
        order = (order + 1) / float(total_order+1)
        mx, my = self.directions[direction]
        if my == 0:
            my = self.height_start + order*self.height_range - self.height/2
            mx *= self.width/2.
        else:
            mx = self.width_start + order*self.width_range - self.width/2
            my *= self.height/2.
        result += vec2d.Vec2d(mx, my)
        return result
    
    def get_side(self, angle):
        if angle>180:
            a = 1
            angle-=180
        else:
            a = 0
        b = angle > self.main_angle
        return a*2+b
        
    
    def precalculate_arcs(self):
        """Precalculates the position of arcs' ends so that they are places as free as possible"""
        side_slots = [[] for i in xrange(4)]
        for arc in itertools.chain(self.input_arcs, self.output_arcs):
            point = arc.get_point_next_to(self)
            p_trans = vec2d.Vec2d(self.get_position())
            p_place = vec2d.Vec2d(point) - p_trans
            angle = p_place.angle
            angle += self.main_angle/2
            if angle<0:
                angle+=360
            elif angle>360:
                angle-=360
            direction = self.get_side(angle)
            side_slots[direction].append((arc, angle))
        self.side_slots = {}
        for n, slot in enumerate(side_slots):
            signum = 1 if (n==0 or n==3) else -1
            self.side_slots.update(dict((elem[0], (i, len(slot), n)) for i, elem in enumerate(sorted(slot, key=lambda x:x[1])[::signum])))
        
    def open_properties_dialog(self, parent):
        fields = [ ('unique_id', DialogFields.unique_id),
                   ('width', place_ranged('Width', minimum=5)),
                   ('height', place_ranged('Height', minimum=5)),
                   ] 
        dia = ElementPropertiesDialog(parent, -1, 'Transition properties', obj=self, fields=fields)
        dia.ShowModal()
        dia.Destroy()      
        
    def check_update_unique_id(self, value):
        if value in self.net.transitions:
            raise ValueError, "A transition with such name already exists"
        
    def update_unique_id(self, value):
        self.net.rename_transition(from_name=self.unique_id, to_name=value)
        
        
        

class GUIPetriNet(petri.PetriNet):
    PLACE_CLS = GUIPlace
    TRANSITION_CLS = GUITransition
    
    def rename_place(self, from_name, to_name):
        place = self.remove_place(from_name)
        place.unique_id = to_name
        self.add_place(place)
        
    def rename_transition(self, from_name, to_name):
        transition = self.remove_transition(from_name)
        transition.unique_id = to_name
        self.add_transition(transition)

    

class Strategy(object):
    def __init__(self, panel):
        self._panel = panel
        self.left_down = False
        self.right_down = False
        self.mouse_x, self.mouse_y = 0, 0
        
        
    @property
    def panel(self):
        return self._panel()
        
    def set_mouse_coords(self, event):
        self.mouse_x, self.mouse_y = event.m_x, event.m_y
        
    def on_left_down(self, event):
        self.left_down = True
        self.set_mouse_coords(event)
        
    def on_left_dclick(self, event):
        self.set_mouse_coords(event)
    
    def on_left_up(self, event):
        self.left_down = False
        self.set_mouse_coords(event)
    
    def on_right_down(self, event):
        self.right_down = True
        self.set_mouse_coords(event)
    
    def on_right_up(self, event):
        self.right_down = False
        self.set_mouse_coords(event)
    
    def on_motion(self, event):
        self.set_mouse_coords(event)
        
    def draw(self, dc):
        pass
    
    def on_switched(self):
        pass
        
class PropertiesMixin(object):
    def on_left_dclick(self, event):
        super(PropertiesMixin, self).on_left_dclick(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if not obj:
            return
        obj.open_properties_dialog(self.panel)
        self.panel.Refresh()
        
    
class MoveAndSelectStrategy(PropertiesMixin, Strategy):
    def __init__(self, panel):
        super(MoveAndSelectStrategy, self).__init__(panel=panel)
        self.selection = set()
        self.choosing_rect_left = None
        self.choosing_rect_right = None
        self.to_select = None
        self.object_moved = False
        self.dragging = False
        self.obj_under_mouse = None
        self.label_moved = None
        
    def on_left_down(self, event):
        super(MoveAndSelectStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if isinstance(obj, ObjectLabel):
            self.label_moved = obj
            self.start_dragging()
            self.panel.Refresh()
            return
        if not (event.ControlDown() or event.AltDown()):
            if obj not in self.selection:
                self.discard_selection()
        self.obj_under_mouse = obj
        if obj is None:
            self.choosing_rect_left = self.mouse_x, self.mouse_y
            self.choosing_rect_right = None
            #self.update_selected(event.AltDown())
            self.panel.Refresh()
            return
        if event.AltDown():
            self.remove_from_selection(obj)
        else:
            self.add_to_selection(obj)  
            self.start_dragging()
        self.panel.Refresh()
        
    def on_right_down(self, event):
        super(MoveAndSelectStrategy, self).on_right_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if obj is None:
            return
        self.add_to_selection(obj)
        obj.spawn_context_menu(self.panel, event)

    def discard_selection(self):
        if not self.selection:
            return
        for obj in self.selection:
            obj.set_selected(False)
        self.selection.clear()
        
    def add_to_selection(self, *objects):
        for obj in objects:
            obj.set_selected(True)
        self.selection.update(objects)
        
    def remove_from_selection(self, *objects):
        for obj in objects:
            obj.set_selected(False)
        self.selection.difference_update(objects)
        
    def move_selection(self, object_to_move=None):
        diff_x, diff_y = self.mouse_x - self.drag_mouse_x, self.mouse_y - self.drag_mouse_y
        if object_to_move is None:
            for obj in self.selection:
                obj.move_diff(diff_x, diff_y)
        else:
            object_to_move.move_diff(diff_x, diff_y)
            
    def on_switched(self):
        self.discard_selection()
        self.panel.Refresh()
        
    def on_motion(self, event):
        if not event.LeftIsDown():
            return
        super(MoveAndSelectStrategy, self).on_motion(event)
        self.object_moved = True
        if self.choosing_rect_left is not None:
            self.update_selected(event.AltDown())
            self.panel.Refresh()
        elif self.left_down:
            if self.label_moved is not None:
                self.move_selection(object_to_move=self.label_moved)
            elif self.selection is not None:
                self.move_selection()
            self.panel.Refresh()

            
    def update_selected(self, alt_down, return_selection=False):
        self.choosing_rect_right = self.mouse_x, self.mouse_y
        gen = self.panel.GetObjectsInRect(*self.points_to_rect(self.choosing_rect_left, self.choosing_rect_right))
        if return_selection:
            result = list(gen)
        else:
            result = gen
        for obj in result:
            if return_selection:
                obj.unselect_temporary()
                continue
                # This is left button up event, no need to calculate temporary values
            obj.temporary_selected = not alt_down
            if alt_down:
                obj.temporary_discarded = True
        return result if return_selection else None
        
    def points_to_rect(self, left, right):
            lx,ly = left
            tx,ty = right
            if lx>tx:
                tx, lx = lx, tx
            if ly>ty:
                ty, ly = ly, ty
            return lx, ly, tx, ty
        
    def draw(self, dc):
        if self.choosing_rect_left and self.choosing_rect_right:
            lx, ly, tx, ty = self.points_to_rect(self.choosing_rect_left, self.choosing_rect_right)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(wx.BLACK_PEN)
            dc.DrawRectangle(lx,ly, tx-lx, ty-ly)
        
            
    def on_left_up(self, event):
        super(MoveAndSelectStrategy, self).on_left_up(event)
        if self.label_moved is not None:
            self.label_moved = None
        elif self.choosing_rect_left is not None and self.choosing_rect_right:
            selected = self.update_selected(event.AltDown(), return_selection=True)
            if event.AltDown():
                self.remove_from_selection(*selected)
            else:
                self.add_to_selection(*selected)
            self.choosing_rect_left = None
            self.panel.Refresh()
        elif not self.object_moved and self.obj_under_mouse in self.selection:
            if not event.ControlDown():
                self.discard_selection()
            self.add_to_selection(self.obj_under_mouse)
            self.panel.Refresh()
        if self.dragging:
            self.stop_dragging()
        self.panel.save_to_file('net.json', self.panel.petri)
              
    def start_dragging(self):
        self.drag_mouse_x, self.drag_mouse_y = self.mouse_x, self.mouse_y
        if self.label_moved is not None:
            self.label_moved.prepare_to_move()
        else:
            for obj in self.selection:
                obj.prepare_to_move()
        self.dragging = True
        self.object_moved = False
        
    def stop_dragging(self):
        self.dragging = False

class SimulateStrategy(Strategy):
    def __init__(self, panel):
        super(SimulateStrategy, self).__init__(panel=panel)
        
    def on_left_down(self, event):
        super(SimulateStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if isinstance(obj, petri.Transition):
            if obj.is_enabled:
                obj.fire()
                self.panel.Refresh()
                print self.panel.petri.get_state()
    
    

class PetriPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PetriPanel, self).__init__(*args, **kwargs)
        self.SetDoubleBuffered(True)
        self.Bind(wx.EVT_PAINT, self.on_paint_event)
        self.Bind(wx.EVT_SIZE,  self.on_size_event)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_button_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_button_up)
        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_button_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_button_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_button_up)
        self.size = 0, 0
        self.mouse_x = self.mouse_y = 0
        
        try:
            self.petri = self.load_from_file('net.json')
        except:
            self.petri = GUIPetriNet.from_string("""
                # p1::1 p2::2 p3::3 p4::4 p5::5
                p2 -> t1 -> p1 p3
                p1 -> t2 -> p3
                p1 -> t3 -> p4
                p3 p4 -> t4 -> p2
            """)
            self.petri = GUIPetriNet.from_string("""
                # p1::1
                p1 -> t2 ->
                p2 -> t3 ->
            """)
            
            
        #self.strategy = MoveAndSelectStrategy(self)
        #self.strategy = SimulateStrategy(self)
        #self.petri.transitions['t1'].set_horizontal(True)
        
    @property
    def strategy(self):
        return self.GetParent().strategy
        
    def GetObjectsInRect(self, lx, ly, tx, ty): #ignore labels
        if not self.petri:
            return
        for obj in self.get_objects_iter():
            if isinstance(obj, ObjectLabel):
                continue
            obj.unselect_temporary()
            if obj.in_rect(lx, ly, tx, ty):
                yield obj
        
            
        
    def load_from_file(self, filepath):
        net = None
        with open(filepath, 'rb') as f:
            json_struct = json.load(f)
        net = GUIPetriNet.from_json_struct(json_struct)
        return net
        
    def save_to_file(self, filepath, net):
        json_struct = net.to_json_struct()
        with open(filepath, 'wb') as f:
            json.dump(json_struct, f)
        
        
    def on_size_event(self, event):
        self.size = event.GetSize()
        self.Refresh()
        
    def on_paint_event(self, event):
        dc = wx.BufferedPaintDC(self)
        w, h = self.size
        dc.SetPen(wx.WHITE_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(0,0,w,h)
        self.draw(dc, w, h)
        
    def on_left_button_down(self, event):
        self.mouse_in = True
        self.on_lbutton_timer()
        self.strategy.on_left_down(event)
        
    def on_right_button_down(self, event):
        self.strategy.on_right_down(event)
        
    def on_right_button_up(self, event):
        self.strategy.on_right_up(event)
        
    def on_left_button_dclick(self, event):
        self.strategy.on_left_dclick(event)
        
    def on_lbutton_timer(self, *args, **kwargs):
        x, y, w, h = self.GetScreenRect()
        mx, my = wx.GetMousePosition()
        state = wx.GetMouseState()
        if not state.LeftDown():
            if self.HasCapture():
                self.ReleaseMouse()
            return
        mouse_in = x <= mx <= x+w and y <= my <= y+h
        if mouse_in and not self.mouse_in:
            if self.HasCapture():
                self.ReleaseMouse()
        elif not mouse_in and self.mouse_in:
            self.CaptureMouse()
        self.mouse_in = mouse_in
        wx.CallLater(20, self.on_lbutton_timer)
        
    def get_object_at(self, x, y):
        # Check in reverse order so the topmost object will be selected
        for obj in self.get_objects_reversed_iter():
            if obj.contains_point(x, y):
                return obj

        
    def on_mouse_motion(self, event):
        self.strategy.on_motion(event)
        
    def on_left_button_up(self, event):
        self.strategy.on_left_up(event)
        
    def get_objects_iter(self):
        for place in self.petri.get_places_iter():
            yield place
            yield place.label
        for transition in self.petri.get_transitions_iter():
            yield transition
            yield transition.label
        for transition in self.petri.get_transitions_iter():   
            for arc in transition.get_arcs():
                yield arc
                for point in arc.points:
                    yield point
        
    def get_objects_reversed_iter(self):
        for transition in reversed(self.petri.get_transitions()):
            for arc in reversed(transition.get_arcs()):
                for point in reversed(arc.points):
                    yield point
                yield arc
        for transition in reversed(self.petri.get_transitions()):
            yield transition.label
            yield transition
        for place in reversed(self.petri.get_places()):
            yield place.label
            yield place
        
    def draw(self, dc, w, h):
        if not self.petri:
            return
        for obj in self.get_objects_iter():
            obj.draw(dc)
        self.strategy.draw(dc)
        
        """
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawLine(0,0,w,h)
        if self.mouse_pos:
            dc.DrawLine(0, 0, self.mouse_pos[0], self.mouse_pos[1])"""
        
       

class Example(wx.Frame):
    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(500, 500))
        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        
        bmp_mouse = wx.Bitmap("icons/arrow.png", wx.BITMAP_TYPE_ANY)
        bmp_animate = wx.Bitmap("icons/animate.png", wx.BITMAP_TYPE_ANY)
        
        mouse_button = buttons.GenBitmapToggleButton(self, bitmap=bmp_mouse)
        
        self.buttons = [(mouse_button, MoveAndSelectStrategy(self.panel_getter)),
                         (buttons.GenBitmapToggleButton(self, bitmap=bmp_animate), SimulateStrategy(self.panel_getter)),
                         ]
        
        for button,_ in self.buttons:
            buttons_sizer.Add(button)
            self.Bind(wx.EVT_BUTTON, self.on_toggle_button)
            
        self.buttons = dict(self.buttons)
        
        self.strategy = self.buttons[mouse_button]
            
        self.toggle_button(mouse_button)
            
        vert_sizer.Add(buttons_sizer)
        self._petri_panel = PetriPanel(self)
        self.petri_panel.SetFocus()
        vert_sizer.Add(self.petri_panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(vert_sizer)
        self.Centre() 
        self.Show()
        
    def panel_getter(self):
        return self._petri_panel
    
    petri_panel = property(panel_getter)
        
    def toggle_button(self, button_on):
        button_on.SetValue(True)
        for button in self.buttons:
            if button!=button_on:
                button.SetValue(False)
                
    def on_toggle_button(self, event):
        button_on = event.GetEventObject()
        if not button_on.GetValue(): #can't untoggle 
            button_on.SetValue(True)
            return
        for button in self.buttons:
            if button != button_on:
                button.SetValue(False)
        self.strategy.on_switched()
        self.strategy = self.buttons[button_on]
        


if __name__ == '__main__':
    Example(None, 'Line')
    app.MainLoop()
    '''
    p  = GUIPlace('p1', 1, (100,100))
    x = p.to_json_struct()
    p2 = GUIPlace.from_json_struct(x, unique_id='p1')
    
    net1 = GUIPetriNet.from_string("""
    # 
    p2 -> t1 -> p1 p3
    p1 -> t2 -> p3
    p1 -> t3 -> p4
    p3 p4 -> t4 -> p2
    """,)
    
    print net1.to_json_struct()
    '''
    