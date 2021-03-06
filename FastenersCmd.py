﻿# -*- coding: utf-8 -*-
###################################################################################
#
#  FastenersCmd.py
#  
#  Copyright 2015 Shai Seger <shaise at gmail dot com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  
###################################################################################

from FreeCAD import Gui
import FreeCAD, FreeCADGui, Part, os
__dir__ = os.path.dirname(__file__)
iconPath = os.path.join( __dir__, 'Icons' )

import FastenerBase
from FastenerBase import FSBaseObject
import ScrewMaker  
screwMaker = ScrewMaker.Instance()

class FSScrewObject(FSBaseObject):
  def __init__(self, obj, type, attachTo):
    '''"Add screw type fastener" '''
    FSBaseObject.__init__(self, obj, attachTo)
    self.itemText = screwMaker.GetTypeName(type)
    diameters = screwMaker.GetAllDiams(type)
    diameters.insert(0, 'Auto')
    #self.Proxy = obj.Name
    
    obj.addProperty("App::PropertyEnumeration","type","Parameters","Screw type").type = screwMaker.GetAllTypes(self.itemText)
    obj.addProperty("App::PropertyEnumeration","diameter","Parameters","Screw diameter standard").diameter = diameters
    self.VerifyCreateMatchOuter(obj)
    if (self.itemText == "Screw"):
      obj.addProperty("App::PropertyEnumeration","length","Parameters","Screw length").length = screwMaker.GetAllLengths(type, diameters[1])
    if (self.itemText != "Washer"):
      obj.addProperty("App::PropertyBool", "thread", "Parameters", "Generate real thread").thread = False
    obj.type = type
    obj.Proxy = self
    
  def VerifyCreateMatchOuter(self, obj):
    if not (hasattr(obj,'matchOuter')):
      obj.addProperty("App::PropertyBool", "matchOuter", "Parameters", "Match outer thread diameter").matchOuter = FastenerBase.FSMatchOuter
 
  def execute(self, fp):
    '''"Print a short message when doing a recomputation, this method is mandatory" '''
    
    try:
      baseobj = fp.baseObject[0]
      shape = baseobj.Shape.getElement(fp.baseObject[1][0])
    except:
      baseobj = None
      shape = None
    
    # for backward compatibility: add missing attribute if needed
    self.VerifyCreateMatchOuter(fp)
    
    FreeCAD.Console.PrintLog("MatchOuter:" + str(fp.matchOuter) + "\n")
    
    typechange = False
    if fp.type == "ISO7380":
      fp.type = "ISO7380-1"   # backward compatibility
    if not (hasattr(self,'type')) or fp.type != self.type:
      typechange = True
      curdiam = fp.diameter
      diameters = screwMaker.GetAllDiams(fp.type)
      diameters.insert(0, 'Auto')
      if not(curdiam in diameters):
        curdiam='Auto'
      fp.diameter = diameters
      fp.diameter = curdiam
      
    diameterchange = False      
    if not (hasattr(self,'diameter')) or self.diameter != fp.diameter:
      diameterchange = True      

    matchouterchange = not (hasattr(self,'matchOuter')) or self.matchOuter != fp.matchOuter

    if fp.diameter == 'Auto' or matchouterchange:
      d = screwMaker.AutoDiameter(fp.type, shape, baseobj, fp.matchOuter)
      fp.diameter = d
      diameterchange = True      
    else:
      d = fp.diameter
    
    if hasattr(fp,'length'):
      d , l = screwMaker.FindClosest(fp.type, d, fp.length)
      if d != fp.diameter:
        diameterchange = True      
        fp.diameter = d
        
      if l != fp.length or diameterchange or typechange:
        if diameterchange or typechange:
          fp.length = screwMaker.GetAllLengths(fp.type, fp.diameter)
        fp.length = l
    else:
      l = 1
      
    threadType = 'simple'
    if hasattr(fp,'thread') and fp.thread:
      threadType = 'real'
      
    (key, s) = FastenerBase.FSGetKey(self.itemText, fp.type, d, l, threadType)
    if s == None:
      s = screwMaker.createFastener(fp.type, d, l, threadType, True)
      FastenerBase.FSCache[key] = s
    else:
      FreeCAD.Console.PrintLog("Using cached object\n")

    self.type = fp.type
    self.diameter = fp.diameter
    self.matchOuter = fp.matchOuter
    if hasattr(fp,'length'):
      self.length = fp.length
      fp.Label = fp.diameter + 'x' + fp.length + '-' + self.itemText
    else:
      fp.Label = fp.diameter + '-' + self.itemText
    
    if hasattr(fp,'thread'):
      self.realThread = fp.thread
    #self.itemText = s[1]
    fp.Shape = s

    if shape != None:
      #feature = FreeCAD.ActiveDocument.getObject(self.Proxy)
      #fp.Placement = FreeCAD.Placement() # reset placement
      FastenerBase.FSMoveToObject(fp, shape, fp.invert, fp.offset.Value)
    
  #def getItemText():
  #  return self.itemText
    


class FSViewProviderTree:
  "A View provider for custom icon"
      
  def __init__(self, obj):
    obj.Proxy = self
    self.Object = obj.Object
      
  def attach(self, obj):
    self.Object = obj.Object
    return

  def updateData(self, fp, prop):
    return

  def getDisplayModes(self,obj):
    modes=[]
    return modes

  def setDisplayMode(self,mode):
    return mode

  def onChanged(self, vp, prop):
    return

  def __getstate__(self):
    #        return {'ObjectName' : self.Object.Name}
    return None

  def __setstate__(self,state):
    if state is not None:
      import FreeCAD
      doc = FreeCAD.ActiveDocument #crap
      self.Object = doc.getObject(state['ObjectName'])
 
  def getIcon(self):
    if hasattr(self.Object, "type"):
      return os.path.join( iconPath , self.Object.type + '.svg')
    elif isinstance(self.Object.Proxy, FSScrewRodObject):
      return os.path.join( iconPath , 'ScrewTap.svg')
    return os.path.join( iconPath , 'ISO4017.svg')



class FSScrewCommand:
  """Add Screw command"""

  def __init__(self, type, help):
    self.Type = type
    self.Help = help
    self.TypeName = screwMaker.GetTypeName(type)

  def GetResources(self):
    icon = os.path.join( iconPath , self.Type + '.svg')
    return {'Pixmap'  : icon , # the name of a svg file available in the resources
            'MenuText': "Add " + self.Help ,
            'ToolTip' : self.Help}
 
  def Activated(self):
    for selObj in FastenerBase.FSGetAttachableSelections():
      a=FreeCAD.ActiveDocument.addObject("Part::FeaturePython",self.TypeName)
      FSScrewObject(a, self.Type, selObj)
      a.Label = a.Proxy.itemText
      FSViewProviderTree(a.ViewObject)
    FreeCAD.ActiveDocument.recompute()
    return
   
  def IsActive(self):
    return Gui.ActiveDocument != None

def FSAddScrewCommand(type, help, dropGroup = None):
  cmd = 'FS' + type
  Gui.addCommand(cmd,FSScrewCommand(type, help))
  FastenerBase.FSCommands.append(cmd, "screws", dropGroup)
  
FSAddScrewCommand("ISO4017", "ISO 4017 Hex head screw", "Hex head")
FSAddScrewCommand("ISO4014", "ISO 4014 Hex head bolt", "Hex head")
FSAddScrewCommand("EN1662", "EN 1662 Hexagon bolt with flange, small series", "Hex head")
FSAddScrewCommand("EN1665", "EN 1665 Hexagon bolt with flange, heavy series", "Hex head")
FSAddScrewCommand("ISO4762", "ISO4762 Hexagon socket head cap screw", "Hexagon socket")
FSAddScrewCommand("ISO7380-1", "ISO 7380 Hexagon socket button head screw", "Hexagon socket")
FSAddScrewCommand("ISO7380-2", "ISO 7380 Hexagon socket button head screws with collar", "Hexagon socket")
FSAddScrewCommand("ISO10642", "ISO 10642 Hexagon socket countersunk head screw", "Hexagon socket")
FSAddScrewCommand("ISO2009", "ISO 2009 Slotted countersunk flat head screw", "Slotted")
FSAddScrewCommand("ISO2010", "ISO 2010 Slotted raised countersunk head screw", "Slotted")
FSAddScrewCommand("ISO1580", "ISO 1580 Slotted pan head screw", "Slotted")
FSAddScrewCommand("ISO1207", "ISO 1207 Slotted cheese head screw", "Slotted")
FSAddScrewCommand("DIN967", "DIN 967 Cross recessed pan head screws with collar", "H cross")
FSAddScrewCommand("ISO7045", "ISO 7045 Pan head screws type H cross recess", "H cross")
FSAddScrewCommand("ISO7046", "ISO 7046 Countersunk flat head screws H cross r.", "H cross")
FSAddScrewCommand("ISO7047", "ISO 7047 Raised countersunk head screws H cross r.", "H cross")
FSAddScrewCommand("ISO7048", "ISO 7048 Cheese head screws with type H cross r.", "H cross")
FSAddScrewCommand("ISO14579", "ISO 14579 Hexalobular socket head cap screws", "Hexalobular socket")
FSAddScrewCommand("ISO14580", "ISO 14580 Hexalobular socket cheese head screws", "Hexalobular socket")
#FSAddScrewCommand("ISO14581", "ISO 14581 Hexalobular socket countersunk flat head screws", "Hexalobular socket")
FSAddScrewCommand("ISO14582", "ISO 14582 Hexalobular socket countersunk head screws, high head", "Hexalobular socket")
FSAddScrewCommand("ISO14583", "ISO 14583 Hexalobular socket pan head screws", "Hexalobular socket")
FSAddScrewCommand("ISO14584", "ISO 14584 Hexalobular socket raised countersunk head screws", "Hexalobular socket")
FSAddScrewCommand("ISO7089", "ISO 7089 Washer", "Washer")
FSAddScrewCommand("ISO7090", "ISO 7090 Plain Washers, chamfered - Normal series", "Washer")
#FSAddScrewCommand("ISO7091", "ISO 7091 Plain washer - Normal series Product Grade C", "Washer")  # same as 7089??
FSAddScrewCommand("ISO7092", "ISO 7092 Plain washers - Small series", "Washer")
FSAddScrewCommand("ISO7093-1", "ISO 7093-1 Plain washers - Large series", "Washer")
FSAddScrewCommand("ISO7094", "ISO 7094 Plain washers - Extra large series", "Washer")
FSAddScrewCommand("ISO4032", "ISO 4032 Hexagon nuts, Style 1", "Nut")
FSAddScrewCommand("ISO4033", "ISO 4033 Hexagon nuts, Style 2", "Nut")
FSAddScrewCommand("ISO4035", "ISO 4035 Hexagon thin nuts, chamfered", "Nut")
#FSAddScrewCommand("ISO4036", "ISO 4035 Hexagon thin nuts, unchamfered", "Nut")
FSAddScrewCommand("EN1661", "EN 1661 Hexagon nuts with flange", "Nut")
FSAddScrewCommand("DIN557", "DIN 557 Square nuts", "Nut")
FSAddScrewCommand("DIN562", "DIN 562 Square nuts", "Nut")
FSAddScrewCommand("DIN985", "DIN 985 Nyloc nuts", "Nut")



#deprecated    
class FSWasherObject(FSBaseObject):
  def __init__(self, obj, type, attachTo):
    '''"Add washer / nut type fastener" '''
    FSBaseObject.__init__(self, obj, attachTo)
    self.itemText = screwMaker.GetTypeName(type)
    diameters = screwMaker.GetAllDiams(type)
    diameters.insert(0, 'Auto')
    #self.Proxy = obj.Name
    
    obj.addProperty("App::PropertyEnumeration","type","Parameters","Screw type").type = screwMaker.GetAllTypes(self.itemText)
    obj.addProperty("App::PropertyEnumeration","diameter","Parameters","Screw diameter standard").diameter = diameters
    obj.type = type
    obj.Proxy = self
 
  def execute(self, fp):
    '''"Print a short message when doing a recomputation, this method is mandatory" '''
    
    try:
      baseobj = fp.baseObject[0]
      shape = baseobj.Shape.getElement(fp.baseObject[1][0])
    except:
      baseobj = None
      shape = None
   
    if (not (hasattr(self,'diameter')) or self.diameter != fp.diameter):
      if fp.diameter == 'Auto':
        d = screwMaker.AutoDiameter(fp.type, shape)
        diameterchange = True      
      else:
        d = fp.diameter
        
      d , l = screwMaker.FindClosest(fp.type, d, '0')
      if d != fp.diameter: 
        fp.diameter = d
      s = screwMaker.createScrew(fp.type, d, l, 'simple', True)
      self.diameter = fp.diameter
      fp.Label = fp.diameter + '-' + self.itemText
      #self.itemText = s[1]
      fp.Shape = s
    else:
      FreeCAD.Console.PrintLog("Using cached object\n")
    if shape != None:
      #feature = FreeCAD.ActiveDocument.getObject(self.Proxy)
      #fp.Placement = FreeCAD.Placement() # reset placement
      FastenerBase.FSMoveToObject(fp, shape, fp.invert, fp.offset.Value)
    
  def getItemText():
    return self.itemText

#deprecated    
class FSWasherCommand:
  """Add Screw command"""

  def __init__(self, type, help):
    self.Type = type
    self.Help = help

  def GetResources(self):
    icon = os.path.join( iconPath , self.Type + '.svg')
    return {'Pixmap'  : icon , # the name of a svg file available in the resources
            'MenuText': "Add " + self.Help ,
            'ToolTip' : self.Help}
 
  def Activated(self):
    for selObj in FastenerBase.FSGetAttachableSelections():
      a=FreeCAD.ActiveDocument.addObject("Part::FeaturePython","Washer")
      FSWasherObject(a, self.Type, selObj)
      a.Label = a.Proxy.itemText
      FSViewProviderTree(a.ViewObject)
    FreeCAD.ActiveDocument.recompute()
    return
   
  def IsActive(self):
    return Gui.ActiveDocument != None

#Gui.addCommand("FSISO7089",FSWasherCommand("ISO7089", "Washer"))
#FastenerBase.FSCommands.append("FSISO7089")

class FSScrewRodObject(FSBaseObject):
  def __init__(self, obj, attachTo):
    '''"Add screw rod" '''
    FSBaseObject.__init__(self, obj, attachTo)
    self.itemText = "ScrewTap"
    self.type = 'ScrewTap'
    diameters = screwMaker.GetAllDiams(self.type)
    diameters.insert(0, 'Auto')
    #self.Proxy = obj.Name
    
    obj.addProperty("App::PropertyEnumeration","diameter","Parameters","Screw diameter standard").diameter = diameters
    obj.addProperty("App::PropertyLength","length","Parameters","Screw length").length = 20.0
    self.VerifyCreateMatchOuter(obj)
    obj.addProperty("App::PropertyBool", "thread", "Parameters", "Generate real thread").thread = False
    obj.Proxy = self
 
  def VerifyCreateMatchOuter(self, obj):
    if not (hasattr(obj,'matchOuter')):
      obj.addProperty("App::PropertyBool", "matchOuter", "Parameters", "Match outer thread diameter").matchOuter = FastenerBase.FSMatchOuter
 
  def execute(self, fp):
    '''"Print a short message when doing a recomputation, this method is mandatory" '''
    
    try:
      baseobj = fp.baseObject[0]
      shape = baseobj.Shape.getElement(fp.baseObject[1][0])
    except:
      baseobj = None
      shape = None
          
    self.VerifyCreateMatchOuter(fp)
    diameterchange = False      
    if not (hasattr(self,'diameter')) or self.diameter != fp.diameter:
      diameterchange = True    
      
    matchouterchange = not (hasattr(self,'matchOuter')) or self.matchOuter != fp.matchOuter

    if fp.diameter == 'Auto' or matchouterchange:
      d = screwMaker.AutoDiameter(self.type, shape, baseobj, fp.matchOuter)
      fp.diameter = d
      diameterchange = True      
    else:
      d = fp.diameter
    
    l = fp.length.Value
    if l < 2.0:
      l = 2.0
      fp.length = 2.0
      
    threadType = 'simple'
    if hasattr(fp,'thread') and fp.thread:
      threadType = 'real'
      
    (key, s) = FastenerBase.FSGetKey(self.itemText, d, str(l), threadType)
    if s == None:
      s = screwMaker.createScrew(self.type, d, str(l), threadType, True)
      FastenerBase.FSCache[key] = s
    else:
      FreeCAD.Console.PrintLog("Using cached object\n")

    self.diameter = fp.diameter
    self.length = l
    self.matchOuter = fp.matchOuter
    fp.Label = fp.diameter + 'x' + str(l) + '-' + self.itemText
    self.realThread = fp.thread
    fp.Shape = s

    if shape != None:
      FastenerBase.FSMoveToObject(fp, shape, fp.invert, fp.offset.Value)

class FSScrewRodCommand:
  """Add Screw Rod command"""

  def GetResources(self):
    icon = os.path.join( iconPath , 'ScrewTap.svg')
    return {'Pixmap'  : icon , # the name of a svg file available in the resources
            'MenuText': "Add Threaded Rod" ,
            'ToolTip' : "Add arbitrary length threaded rod"}
 
  def Activated(self):
    for selObj in FastenerBase.FSGetAttachableSelections():
      a=FreeCAD.ActiveDocument.addObject("Part::FeaturePython","ScrewTap")
      FSScrewRodObject(a, selObj)
      a.Label = a.Proxy.itemText
      FSViewProviderTree(a.ViewObject)
    FreeCAD.ActiveDocument.recompute()
    return
   
  def IsActive(self):
    return Gui.ActiveDocument != None

Gui.addCommand("FSScrewTap",FSScrewRodCommand())
FastenerBase.FSCommands.append("FSScrewTap", "screws", "misc")

## add fastener types
FastenerBase.FSAddFastenerType("Screw")
FastenerBase.FSAddFastenerType("Washer", False)
FastenerBase.FSAddFastenerType("Nut", False)
FastenerBase.FSAddFastenerType("ScrewTap", True, False)
for item in ScrewMaker.screwTables:
  FastenerBase.FSAddItemsToType(ScrewMaker.screwTables[item][0], item)
