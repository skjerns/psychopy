# -*- coding: utf-8 -*-
"""Classes for the color picker."""

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

import wx
import wx.lib.agw.cubecolourdialog as ccd
from wx.adv import PseudoDC
from wx.lib.embeddedimage import PyEmbeddedImage
from wx.lib.buttons import GenButton
from wx.lib.scrolledpanel import ScrolledPanel

from psychopy.app.colorpicker.hsv import HSVColorPicker
from psychopy.app.colorpicker.chip import ColorChip
from psychopy.app.themes import ThemeMixin
from psychopy.colors import Color, AdvancedColor, colorNames
import wx.lib.agw.aui as aui


class PsychoColorPicker(wx.Dialog, ThemeMixin):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=u"Color Picker", pos=wx.DefaultPosition,
                           style=wx.DEFAULT_DIALOG_STYLE)
        # Set main params
        self.color = Color((0,0,0,1), 'rgba')
        self.sizer = wx.GridBagSizer()
        # Add colourful top bar
        self.preview = ColorPreview(color=self.color, parent=self)
        self.sizer.Add(self.preview, pos=(0,0), span=wx.GBSpan(2,1), border=5, flag=wx.RIGHT | wx.EXPAND)
        # Add notebook of controls
        self.ctrls = aui.AuiNotebook(self, wx.ID_ANY, size=wx.Size(400, 400))
        self.sizer.Add(self.ctrls, pos=(0,1), border=5, flag=wx.ALL)
        self.ctrls.AddPage(ColorPage(self.ctrls, self, 'rgba'), 'RGB (-1 to 1)')
        self.ctrls.AddPage(ColorPage(self.ctrls, self, 'rgba1'), 'RGB (0 to 1)')
        self.ctrls.AddPage(ColorPage(self.ctrls, self, 'rgba255'), 'RGB (0 to 255)')
        self.ctrls.AddPage(ColorPage(self.ctrls, self, 'hsva'), 'HSV')
        self.ctrls.AddPage(ColorPage(self.ctrls, self, 'hexa'), 'Hex')
        self.ctrls.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.onPageChanged)
        # Add array of named colours
        self.presets = ColorPresets(parent=self)
        self.sizer.Add(self.presets, pos=(0,2), border=5, flag=wx.ALL)
        # Add buttons
        self.buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.closeButton = wx.Button(self, label="Cancel")
        self.closeButton.Bind(wx.EVT_BUTTON, self.Close)
        self.buttons.Add(self.closeButton, border=5, flag=wx.ALL)
        # Add insert buttons
        # self.insertValueButton = wx.Button(self, label="Insert As Value")
        # self.insertValueButton.Bind(wx.EVT_BUTTON, self.insertValue)
        # self.buttons.Add(self.insertValueButton, border=5, flag=wx.ALL)
        # self.insertObjectButton = wx.Button(self, label="Insert As Object")
        # self.insertObjectButton.Bind(wx.EVT_BUTTON, self.insertObject)
        # self.buttons.Add(self.insertObjectButton, border=5, flag=wx.ALL)
        # Add copy buttons
        self.copyValueButton = wx.Button(self, label="Copy As Value")
        self.copyValueButton.Bind(wx.EVT_BUTTON, self.copyValue)
        self.buttons.Add(self.copyValueButton, border=5, flag=wx.ALL)
        self.copyObjectButton = wx.Button(self, label="Copy As Object")
        self.copyObjectButton.Bind(wx.EVT_BUTTON, self.copyObject)
        self.buttons.Add(self.copyObjectButton, border=5, flag=wx.ALL)

        self.sizer.Add(self.buttons, pos=(1,1), span=wx.GBSpan(1,2), border=5, flag=wx.ALL | wx.ALIGN_RIGHT)

        # Configure sizer
        self.sizer.AddGrowableRow(0)
        self.sizer.AddGrowableCol(1)
        self.SetSizerAndFit(self.sizer)
        self._applyAppTheme()
        self._applyAppTheme(self.ctrls)

        self.Layout()
        self.Centre(wx.BOTH)
        self.Show(True)

    def setColor(self, color, space):
        self.color.set(color, space)
        self.preview.color = self.color

    def insertValue(self, event):
        print(self.color)

    def insertObject(self, event):
        print(self.color)

    def copyValue(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(
                str(getattr(self.color, self.ctrls.GetCurrentPage().space))
            ))
            wx.TheClipboard.Close()

    def copyObject(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(
                "Color("+str(getattr(self.color, self.ctrls.GetCurrentPage().space))+", "+self.ctrls.GetCurrentPage().space+")"
            ))
            wx.TheClipboard.Close()

    def onPageChanged(self, event):
        event.EventObject.GetPage(event.Selection).onOpen()


class ColorPreview(wx.Window):
    def __init__(self, color, parent):
        wx.Window.__init__(self, parent, size=(100,-1))
        self.SetBackgroundColour(ThemeMixin.appColors['frame_bg'])
        self.parent = parent
        self.color = color
        self.Bind(wx.EVT_PAINT, self.onPaint)

    @property
    def color(self):
        return self._color
    @color.setter
    def color(self, value):
        self._color = value
        self.Refresh()

    def onPaint(self, event):
        self.pdc = wx.PaintDC(self)
        self.dc = wx.GCDC(self.pdc)
        self.pdc.SetBrush(wx.Brush(ThemeMixin.appColors['panel_bg']))
        self.pdc.SetPen(wx.Pen(ThemeMixin.appColors['panel_bg']))
        w = 10
        h = 10
        for x in range(0, self.GetSize()[0], w*2):
            for y in range(0+(x%2)*h, self.GetSize()[1], h*2):
                self.pdc.DrawRectangle(x, y, w, h)
                self.pdc.DrawRectangle(x+w, y+h, w, h)
        self.dc.SetBrush(wx.Brush(self.color.rgba255, wx.BRUSHSTYLE_TRANSPARENT))
        self.dc.SetPen(wx.Pen(self.color.rgba255, wx.PENSTYLE_TRANSPARENT))
        self.dc.DrawRectangle(0, 0, self.GetSize()[0], self.GetSize()[1])

class ColorPresets(ScrolledPanel):
    def __init__(self, parent):
        ScrolledPanel.__init__(self, parent, size=(120,400), style=wx.VSCROLL | wx.BORDER_NONE)
        self.sizer = wx.GridBagSizer()
        self.parent = parent
        for i in range(len(colorNames)):
            color = list(colorNames)[i]
            btn = GenButton(self, size=(100, 30),
                               label=color, name=color)
            btn.SetOwnBackgroundColour(Color(color, 'named').rgba255)
            btn.SetBezelWidth(0)
            btn.SetUseFocusIndicator(False)
            btn.colorData = color
            #btn.SetBackgroundColour(wx.Colour(Color(color, 'named').rgba1))
            btn.Bind(wx.EVT_BUTTON, self.onClick)
            self.sizer.Add(btn, pos=(i,0))
        self.SetSizer(self.sizer)
        self.SetupScrolling()

    def onClick(self, event):
        self.parent.setColor(event.GetEventObject().colorData, 'named')
        self.parent.ctrls.GetCurrentPage().onOpen()


class ColorPage(wx.Window, ThemeMixin):
    def __init__(self, parent, dlg, space):
        wx.Window.__init__(self, parent)
        self.dlg = dlg
        self.space = space
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.AddSpacer(15)
        rowh = 30
        self.ctrls = []
        if space in ['rgb', 'rgba']:
            self.ctrls = [
                ColorControl(parent=self, id=wx.ID_ANY, name="Red", value=0, min=-1, max=1, interval=0.01),
                ColorControl(parent=self, id=wx.ID_ANY, name="Green", value=0, min=-1, max=1, interval=0.01),
                ColorControl(parent=self, id=wx.ID_ANY, name="Blue", value=0, min=-1, max=1, interval=0.01)]
            if space == 'rgba':
                self.ctrls.append(
                    ColorControl(parent=self, id=wx.ID_ANY, name="Alpha", value=1, min=-1, max=1, interval=0.01))
        elif space in ['rgb1', 'rgba1']:
            self.ctrls = [
                ColorControl(parent=self, id=wx.ID_ANY, name="Red", value=0.5, min=0, max=1, interval=0.01),
                ColorControl(parent=self, id=wx.ID_ANY, name="Green", value=0.5, min=0, max=1, interval=0.01),
                ColorControl(parent=self, id=wx.ID_ANY, name="Blue", value=0.5, min=0, max=1, interval=0.01)]
            if space == 'rgba1':
                self.ctrls.append(
                    ColorControl(parent=self, id=wx.ID_ANY, name="Alpha", value=1, min=0, max=1, interval=0.01))
        elif space in ['rgb255', 'rgba255']:
            self.ctrls = [
                ColorControl(parent=self, id=wx.ID_ANY, name="Red", value=127, min=0, max=255, interval=1),
                ColorControl(parent=self, id=wx.ID_ANY, name="Green", value=127, min=0, max=255, interval=1),
                ColorControl(parent=self, id=wx.ID_ANY, name="Blue", value=127, min=0, max=255, interval=1)]
            if space == 'rgba255':
                self.ctrls.append(
                    ColorControl(parent=self, id=wx.ID_ANY, name="Alpha", value=255, min=0, max=255, interval=1))
        elif space in ['hsv', 'hsva']:
            self.ctrls = [
                ColorControl(parent=self, id=wx.ID_ANY, name="Hue", value=180, min=0, max=360, interval=0.01),
                ColorControl(parent=self, id=wx.ID_ANY, name="Saturation", value=0.5, min=0, max=1, interval=0.01),
                ColorControl(parent=self, id=wx.ID_ANY, name="Vividness", value=0.5, min=0, max=1, interval=0.01)]
            if space == 'hsva':
                self.ctrls.append(
                    ColorControl(parent=self, id=wx.ID_ANY, name="Alpha", value=1, min=0, max=1, interval=0.01))
        elif space in ['hex', 'hexa']:
            self.ctrls = [
                ColorControl(parent=self, id=wx.ID_ANY, name="Red", value=127, min=0, max=255, interval=1),
                ColorControl(parent=self, id=wx.ID_ANY, name="Green", value=127, min=0, max=255, interval=1),
                ColorControl(parent=self, id=wx.ID_ANY, name="Blue", value=127, min=0, max=255, interval=1)]
            if space == 'hexa':
                self.ctrls.append(
                    ColorControl(parent=self, id=wx.ID_ANY, name="Alpha", value=255, min=0, max=255, interval=1))
            for ctrl in self.ctrls:
                ctrl.spinner.SetBase(16)
        self.valCtrl = ColorValue(self)
        self.sizer.Add(self.valCtrl, border=15, flag=wx.ALL | wx.ALIGN_CENTER)
        self.sizer.AddMany(self.ctrls)
        self.SetSizer(self.sizer)
        #self.onOpen()

    def _applyAppTheme(self, target=None):
        self.SetBackgroundColour(ThemeMixin.appColors['tab_bg'])

    def onOpen(self):
        if self.space =='hex':
            col = self.dlg.color.rgb255
        elif self.space == 'hexa':
            col = self.dlg.color.rgba255
        else:
            col = getattr(self.dlg.color, self.space)
        for i in range(len(col)):
            self.ctrls[i].value = col[i]

    def onChange(self):
        if self.space in ['hex', 'hexa']:
            col = tuple(ctrl.value for ctrl in self.ctrls)
            self.dlg.setColor(col, 'rgba255')
            return

        col = tuple(ctrl.value for ctrl in self.ctrls)
        self.dlg.setColor(col, self.space)


class ColorValue(wx.TextCtrl):
    def __init__(self, parent=None):
        self.parent = parent
        self.space = parent.space
        self.color = parent.dlg.color
        wx.TextCtrl.__init__(self, parent=self.parent, value=str(getattr(self.color, self.space)), style=wx.TE_RICH, size=(250, -1))
        self.Bind(wx.EVT_TEXT, self.onChange)

    def onChange(self, event):
        obj = event.EventObject
        if self.space in Color.getSpace(event.String, True):
            self.SetStyle(0, len(event.String), wx.TextAttr(wx.Colour((0, 0, 0))))
            self.parent.dlg.setColor(event.String, self.space)
            self.parent.onChange()
        else:
            self.SetStyle(0, len(event.String), wx.TextAttr(wx.Colour((255,0,0))))


class ColorControl(wx.Panel):
    def __init__(self, parent=None, row=0, id=None, name="", value=0, min=-1, max=1, interval=0.01):
        rowh = 30
        wx.Panel.__init__(self, parent, id=id, style=wx.BORDER_NONE, name=name)
        # Store attributes
        self.color = parent.dlg.color
        self.parent = parent
        self.min = min
        self.max = max
        self.interval=interval
        # Make sizer
        self.sizer = wx.GridBagSizer()
        self.SetSizer(self.sizer)
        # Make label
        self.label = wx.StaticText(parent=self, label=name, size=(75,rowh), style=wx.ALIGN_RIGHT)
        self.sizer.Add(self.label, pos=(0, 0))
        self.sizer.AddGrowableCol(0, 0.25)
        # Make slider
        self.slider = wx.Slider(self, name=name, minValue=0, maxValue=255, size=(200, rowh))
        self.slider.Bind(wx.EVT_COMMAND_SCROLL_CHANGED, self.onChange)
        self.sizer.Add(self.slider, pos=(0, 1))
        self.sizer.AddGrowableCol(1, 0.5)
        # Make spinner
        self.spinner = wx.SpinCtrl(self, name=name, min=min, max=max, size=(75,rowh-5))
        self.spinner.Bind(wx.EVT_SPIN_UP, self.spinUp)
        self.spinner.Bind(wx.EVT_SPIN_UP, self.spinDown)
        self.spinner.Bind(wx.EVT_SPINCTRL, self.onChange)
        self.sizer.Add(self.spinner, pos=(0, 2))
        self.sizer.AddGrowableCol(2, 0.25)
        # Set value
        self.value = value

    def spinUp(self, event):
        self.value += self.interval
    def spinDown(self, event):
        self.value -= self.interval

    @property
    def value(self):
        if self.max - self.min > 2:
            return round(self._value)
        else:
            return self._value
    @value.setter
    def value(self, val):
        if val > self.max:
            val = self.max
        if val < self.min:
            val = self.min
        self._value = val
        self.spinner.SetValue(val)
        propVal = (val-self.min) / (self.max-self.min)
        self.slider.SetValue(propVal*255)
        self.parent.onChange()

    def onChange(self, event):
        obj = event.GetEventObject()
        if obj == self.slider:
            propVal = obj.GetValue()/255
            self.value = self.min + (self.max-self.min)*propVal
        if obj == self.spinner:
            self.value = obj.GetValue()

class HexControl(ColorControl):
    def __init__(self, parent=None, row=0, id=None, name="", value=0):
        ColorControl.__init__(self, parent=parent, row=row, id=id, name=name, value=value, min=0, max=255, interval=1)
        self.spinner.SetBase(16)