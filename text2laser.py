#!/usr/bin/python

"""
    text2laser.py
    adapted from engrave-11.py

    engrave-lines.py G-Code Engraving Generator for command-line usage
    (C) ArcEye <2012>  <arceye at mgware dot co dot uk>
    syntax  ---   see helpfile below
    
    Allows the generation of multiple lines of engraved text in one go
    Will take each string arguement, apply X and Y offset generating code until last line done
    
  
    based upon code from engrave-11.py
    Copyright (C) <2008>  <Lawrence Glaister> <ve7it at shaw dot ca>
                     based on work by John Thornton  -- GUI framwork from arcbuddy.py
                     Ben Lipkowitz  (fenn)-- cxf2cnc.py v0.5 font parsing code

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    Rev v2 21.06.2012 ArcEye
"""

import getopt
import re
import sys
from math import *

# change this if you want to use another font
fontfile = "normal.cxf"
laser_range = 1000.
laser_operative_pwr = 0.2
Feed = 1000


Deg2Rad = 2.0 * pi / 360.0
String = ""
SafeZ = 2
XStart = 0
XLineOffset = 0
XIndentList = ""
YStart = 0
YLineOffset = 0
Depth = 0.1
XScale = 1
YScale = 1
CSpaceP = 25
WSpaceP = 100
Angle = 0
Mirror = 0
Flip = 0
Spindle = 0.
font = None

Preamble = """
G21         ; Set units to mm
M4 S0       ; Enable Laser/Spindle (0 power)
"""

Postamble = """
M5          ; Disable Laser/Spindle
"""

stringlist = []
p = {}


# =======================================================================
class Character:
    def __init__(self, key):
        self.key = key
        self.stroke_list = []
        self.stroke_list_groups = []

    def __repr__(self):
        return "%s" % (self.stroke_list)

    def get_xmax(self):
        try:
            return max([s.xmax for s in self.stroke_list[:]])
        except ValueError:
            return 0

    def get_ymax(self):
        try:
            return max([s.ymax for s in self.stroke_list[:]])
        except ValueError:
            return 0

# =======================================================================
class Line:

    def __init__(self, coords):
        self.xstart, self.ystart, self.xend, self.yend = coords
        self.xmax = max(self.xstart, self.xend)
        self.ymax = max(self.ystart, self.yend)
        self.xmin = min(self.xstart, self.xend)
        self.ymin = min(self.ystart, self.yend)

    def __repr__(self):
        return "Line([%s, %s, %s, %s])" % (self.xstart, self.ystart, self.xend, self.yend)


class StrokeGroup:
    def __init__(self):
        self.lines = []
        self.xmax = -sys.maxint-1
        self.ymax = -sys.maxint-1
        self.xmin = sys.maxint
        self.ymin = sys.maxint

    def addLine(self, line):
        self.lines.append(line)
        self.xmax = max(self.xmax, line.xmax)
        self.xmin = min(self.xmin, line.xmin)
        self.ymax = max(self.ymax, line.ymax)
        self.ymin = min(self.ymin, line.ymin)


def inside_cmp(g1, g2):
    if g1.xmin < g2.xmin and g1.xmax > g2.xmax and g1.ymin < g2.ymin and g1.ymax > g2.xmax:
        return 1
    return -1

def inside_first(strokes):
    # pass1 : divide strokes
    o_stroke = None
    stroke_groups = []
    distance = 1
    for stroke in strokes:
        if o_stroke is not None:
            dx = stroke.xstart-o_stroke.xend
            dy = stroke.ystart-o_stroke.yend
            distance = sqrt(dx * dx + dy * dy)
        if distance > 0.001:
            stroke_group = StrokeGroup()
            stroke_groups.append(stroke_group)
        stroke_group.addLine(stroke)
        o_stroke = stroke

    # pass2: order stroke, first inside one
    stroke_groups.sort(inside_cmp)

    # pass3: return order strokes
    order_strokes = []
    for sg in stroke_groups:
        for line in sg.lines:
            order_strokes.append(line)

    return stroke_groups, order_strokes


# =======================================================================
# This routine parses the .cxf font file and builds a font dictionary of
# line segment strokes required to cut each character.
# Arcs (only used in some fonts) are converted to a number of line
# segemnts based on the angular length of the arc. Since the idea of
# this font description is to make it support independant x and y scaling,
# we can not use native arcs in the gcode.
# =======================================================================
def parse(filein):
    font = {}
    key = None
    num_cmds = 0
    line_num = 0
    xmax, ymax = 0, 0
    for text in filein:
        # format for a typical letter (lowercase r):
        ##comment, with a blank line after it
        #
        # [r] 3
        # L 0,0,0,6
        # L 0,6,2,6
        # A 2,5,1,0,90
        #
        line_num += 1
        end_char = re.match('^$', text)  # blank line
        if end_char and key:  # save the character to our dictionary
            font[key] = Character(key)

            font[key].stroke_list_groups, font[key].stroke_list = inside_first(stroke_list)

            font[key].xmax = xmax
            if num_cmds != cmds_read:
                print "; warning: discrepancy in number of commands %s, line %s, %s != %s " % (
                fontfile, line_num, num_cmds, cmds_read)

        new_cmd = re.match('^\[(.*)\]\s(\d+)', text)
        if new_cmd:  # new character
            key = new_cmd.group(1)
            num_cmds = int(new_cmd.group(2))  # for debug
            cmds_read = 0
            stroke_list = []
            xmax, ymax = 0, 0

        line_cmd = re.match('^L (.*)', text)
        if line_cmd:
            cmds_read += 1
            coords = line_cmd.group(1)
            coords = [float(n) for n in coords.split(',')]
            stroke_list += [Line(coords)]
            xmax = max(xmax, coords[0], coords[2])
            ymax = max(ymax, coords[1], coords[3])

        arc_cmd = re.match('^A (.*)', text)
        if arc_cmd:
            cmds_read += 1
            coords = arc_cmd.group(1)
            coords = [float(n) for n in coords.split(',')]
            xcenter, ycenter, radius, start_angle, end_angle = coords
            # since font defn has arcs as ccw, we need some font foo
            if (end_angle < start_angle):
                start_angle -= 360.0
            # approximate arc with line seg every 20 degrees
            segs = int((end_angle - start_angle) / 20) + 1
            angleincr = (end_angle - start_angle) / segs
            xstart = cos(start_angle * pi / 180) * radius + xcenter
            ystart = sin(start_angle * pi / 180) * radius + ycenter
            angle = start_angle
            for i in range(segs):
                angle += angleincr
                xend = cos(angle * pi / 180) * radius + xcenter
                yend = sin(angle * pi / 180) * radius + ycenter
                coords = [xstart, ystart, xend, yend]
                stroke_list += [Line(coords)]
                xmax = max(xmax, coords[0], coords[2])
                ymax = max(ymax, coords[1], coords[3])
                xstart = xend
                ystart = yend

        arc_cmd = re.match('^AR (.*)', text)
        if arc_cmd:
            cmds_read += 1
            coords = arc_cmd.group(1)
            coords = [float(n) for n in coords.split(',')]
            xcenter, ycenter, radius, end_angle, start_angle = coords
            # since font defn has arcs as ccw, we need some font foo
            if (end_angle < start_angle):
                start_angle -= 360.0
            # approximate arc with line seg every 20 degrees
            segs = int((end_angle - start_angle) / 20) + 1
            angleincr = (end_angle - start_angle) / segs
            xstart = cos(end_angle * pi / 180) * radius + xcenter
            ystart = sin(end_angle * pi / 180) * radius + ycenter
            angle = end_angle
            for i in range(segs):
                angle -= angleincr
                xend = cos(angle * pi / 180) * radius + xcenter
                yend = sin(angle * pi / 180) * radius + ycenter
                coords = [xstart, ystart, xend, yend]
                stroke_list += [Line(coords)]
                xmax = max(xmax, coords[0], coords[2])
                ymax = max(ymax, coords[1], coords[3])
                xstart = xend
                ystart = yend

    return font

# =======================================================================


def get_xmax():
    try:
        return max([s.xmax for s in stroke_list[:]])
    except ValueError:
        return 0


def get_ymax():
    try:
        return max([s.ymax for s in stroke_list[:]])
    except ValueError:
        return 0


# =======================================================================


# =======================================================================
def sanitize(string):
    retval = ''
    good = ' ~!@#$%^&*_+=-{}[]|\:;"<>,./?'
    for char in string:
        if char.isalnum() or good.find(char) != -1:
            retval += char
        else:
            retval += (' 0x%02X ' % ord(char))
    return retval


# =======================================================================
# routine takes an x and a y in raw internal format
# x and y scales are applied and then x,y pt is rotated by angle
# Returns new x,y tuple
def Rotn(x, y, xscale, yscale, angle):
    xx = x * xscale
    yy = y * yscale
    rad = sqrt(xx * xx + yy * yy)
    theta = atan2(yy, xx)
    newx = rad * cos(theta + angle * Deg2Rad)
    newy = rad * sin(theta + angle * Deg2Rad)
    return newx, newy


def laser_power(pwr):
    global Spindle
    Spindle = pwr*laser_range
#  return "S%.0f" % (pwr*laser_range)
# =======================================================================


def o9000(p1, p2, p3):
    p28 = p2*p[1004]
    p29 = p3*p[1005]
    p30 = sqrt(p28*p28 + p29*p29)
    p31 = atan2(p29, p28)
    p32 = p30*cos(p31+p[1006]*Deg2Rad)
    p33 = p30*sin(p31+p[1006]*Deg2Rad)
    if p1 < 0.5:
        out = "G00 X%f Y%f" % (p32+p[1002], p33+p[1003])
    else:
        out = "G01 X%f Y%f S%.0f F%.0f" % (p32 + p[1002], p33 + p[1003], Spindle, Feed)

    return out

def code(arg, visit, last):

    global p
    global String

    String = arg

    str1 = ""
    # erase old gcode as needed
    gcode = []

    oldx = oldy = -99990.0

    if visit != 0:
        # all we need is new X and Y for subsequent lines
        gcode.append("; ===================================================================")
        gcode.append('; Engraving: "%s" ' % (String))
        gcode.append('; Line %d ' % visit)

        p[1002] = XStart
        if XLineOffset:
            if XIndentList.find(str(visit)) != -1:
                p[1002] = XStart + XLineOffset

        p[1003] = YStart - (YLineOffset * visit)

    else:
        gcode.append('; Code generated by text2laser.py ')
        gcode.append('; Engraving: "%s"' % (String))
        gcode.append('; Fontfile: %s ' % (fontfile))

        p[1000] = SafeZ
        p[1001] = Depth

        p[1002] = XStart
        if XLineOffset:
            if XIndentList.find(str(visit)) != -1:
                p1002 = XStart+XLineOffset

        p[1003] = YStart
        p[1004] = XScale
        p[1005] = YScale
        p[1006] = Angle
        gcode.append(Preamble)

    laser_power(0)

    font_word_space = max(font[key].get_xmax() for key in font) * (WSpaceP / 100.0)
    font_char_space = font_word_space * (CSpaceP / 100.0)

    xoffset = 0  # distance along raw string in font units

    # calc a plot scale so we can show about first 15 chars of string
    # in the preview window
    PlotScale = 15 * font['A'].get_xmax() * XScale / 150

    for char in String:
        if char == ' ':
            xoffset += font_word_space
            continue
        try:
            gcode.append(";character '%s'" % sanitize(char))
            first_stroke = True
            for stroke_group in font[char].stroke_list_groups:
                first_stroke = True
                for stroke in stroke_group.lines:
                    x1 = stroke.xstart + xoffset
                    y1 = stroke.ystart
                    if Mirror == 1:
                        x1 = -x1
                    if Flip == 1:
                        y1 = -y1
                    # check and see if we need to move to a new discontinuous start point
                    if first_stroke:
                        first_stroke = False
                        # lift engraver, rapid to start of stroke, drop tool
                        laser_power(0)
                        gcode.append(o9000(0., x1, y1))
                        laser_power(laser_operative_pwr)
                    x2 = stroke.xend + xoffset
                    y2 = stroke.yend
                    if Mirror == 1:
                        x2 = -x2
                    if Flip == 1:
                        y2 = -y2
                    gcode.append(o9000(1., x2, y2))

            # move over for next character
            char_width = font[char].get_xmax()
            xoffset += font_char_space + char_width

        except KeyError:
            gcode.append("; warning: character '0x%02X' not found in font defn" % ord(char))

        gcode.append("")  # blank line after every char block

    laser_power(0)

    # finish up with icing
    if last:
        gcode.append(Postamble)

    for line in gcode:
        sys.stdout.write(line + '\n')


################################################################################################################

def help_message():
    print '''text2laser.py G-Code laser Engraving Generator for command-line usage
            bugfix and adapted to laser machines by Fabrizio Zellini on 2020
            (C) ArcEye <2012> 
            based upon code from engrave-11.py
            Copyright (C) <2008>  <Lawrence Glaister> <ve7it at shaw dot ca>'''

    print '''text2laser.py -X -x -i -Y -y -S -s -Z -D -C -W -M -F -P -p -a ..............
       Options: 
       -h   Display this help message
       -X   Start X value                       Defaults to 0
       -x   X offset between lines              Defaults to 0
       -i   X indent line list                  String of lines to indent in single quotes
       -Y   Start Y value                       Defaults to 0
       -y   Y offset between lines, in % respect to font height
       -A   Angle                               Defaults to 0 
       -S   X Scale                             Defaults to 1
       -s   Y Scale                             Defaults to 1       
       -C   Charactor Space %                   Defaults to 25%
       -W   Word Space %                        Defaults to 100%
       -M   Mirror                              Defaults to 0 (No)
       -f   Flip                                Defaults to 0 (No)
       -F   Feed Rate                           Defaults to 1000
       -L   Laser max power                     Defaults to 1000
       -l   laser engrave power in %            defaults to 20%
       -P   Preamble g code                     
       -p   Postamble g code                    
       -a   append line to engrave
       --font font                              defaults "normal.cxf"

      Example
      text2laser.py -S0.4 -s0.5 -a'Line0' -a'Line1' -a'Line2' -a'Line3' -F4000 -L1000 -l20> test.ngc
      
      fonts are searched on paths ./cxf_fonts, env "CXF_FONTS", ".cxf_fonts" of user HOME directory
    '''
    sys.exit(0)


# ===============================================================================================================

def main():
    debug = 0
    # need to declare the globals because we want to write to them
    # otherwise python will create a local of the same name and
    # not change the global
    global SafeZ
    global XStart
    global XLineOffset
    global XIndentList
    global YStart
    global YLineOffset
    global Depth
    global XScale
    global YScale
    global CSpaceP
    global WSpaceP
    global Angle
    global Mirror
    global Flip
    global Preamble
    global Postamble
    global stringlist
    global Feed
    global font
    global laser_range
    global laser_operative_pwr
    global fontfile


    try:
        options, xarguments = getopt.getopt(sys.argv[1:], 'hd:X:x:i:Y:y:S:s:Z:D:C:W:M:F:f:P:p:L:l:a:A:',["font="])
    except getopt.error:
        print 'Error: You tried to use an unknown option. Try `text2laser.py -h\' for more information.'
        sys.exit(0)

    if len(sys.argv[1:]) == 0:
        help_message()
        sys.exit(0)

    for o, a in options:
        if o == '-h':
            help_message()
            sys.exit(0)

        if o == '-d' and a != '':
            debug = int(a)
            print'debug set to %d' % (debug)

        if o == "--font":
            fontfile = a
            if debug:
                print'font = %s' % (fontfile)

        if o == '-L' and a != '':
            laser_range = float(a)
            if debug:
                print'L = %.4f' % (laser_range)
        if o == '-l' and a != '':
            laser_operative_pwr = float(a)/100.
            if debug:
                print'L = %.4f' % (laser_operative_pwr)

        if o == '-X' and a != '':
            XStart = float(a)
            if debug:
                print'X = %.4f' % (XStart)
        if o == '-x' and a != '':
            XLineOffset = float(a)
            if debug:
                print'x = %.4f' % (XLineOffset)
        if o == '-i' and a != '':
            XIndentList = a
            if debug:
                print'i = %s' % (a)
        if o == '-Y' and a != '':
            YStart = float(a)
            if debug:
                print'Y = %.4f' % (YStart)
        if o == '-y' and a != '':
            YLineOffset = float(a)
            if debug:
                print'y = %.4f' % (YLineOffset)
        if o == '-S' and a != '':
            XScale = float(a)
            if debug:
                print'S = %.4f' % (XScale)
        if o == '-s' and a != '':
            YScale = float(a)
            if debug:
                print's = %.4f' % (YScale)
        if o == '-Z' and a != '':
            SafeZ = float(a)
            if debug:
                print'Z = %.4f' % (SafeZ)
        if o == '-D' and a != '':
            Depth = float(a)
            if debug:
                print'D = %.4f' % (Depth)
        if o == '-C' and a != '':
            CSpaceP = float(a)
            if debug:
                print'C = %.4f' % (CSpaceP)
        if o == '-W' and a != '':
            WSpaceP = float(a)
            if debug:
                print'W = %.4f' % (WSpaceP)
        if o == '-A' and a != '':
            Angle = float(a)
            if debug:
                print'A = %.4f' % (Angle)
        if o == '-M' and a != '':
            Mirror = float(a)
            if debug:
                print'M = %.4f' % (Mirror)
        if o == '-f' and a != '':
            Flip = float(a)
            if debug:
                print'f = %.4f' % (Flip)
        if o == '-F' and a != '':
            Feed = float(a)
            if debug:
                print'F = %.4f' % (Feed)
        if o == '-P' and a != '':
            Preamble = a
            if debug:
                print'P = %s' % (a)
        if o == '-p' and a != '':
            Postamble = a
            if debug:
                print'p = %s' % (a)
        if o == '-a' and a != '':
            stringlist.append(a)
            if debug:
                print'0 = %s' % (a)

    import os

    thefont = None
    fontpathlist = ["./cxf_fonts"]
    if os.getenv("cxf_fonts"):
        fontpathlist.append(os.getenv("cxf_fonts"))
    if os.getenv("HOME"):
        fontpathlist.append(os.path.join(os.getenv("HOME"), ".cxf_fonts"))

    font_exists = False
    for fontpath in fontpathlist:
        thefont = os.path.join(fontpath, fontfile)
        if os.path.exists(thefont):
            fontfile = thefont
            font_exists=True
            break

    if not font_exists:
        print "; font not found"
        sys.exit(1)

    file = open(fontfile)
    font = parse(file)  # build stroke lists from font file
    file.close()
    font_line_height = max(font[key].get_ymax() for key in font)

    if YLineOffset == 0:
        YLineOffset = YScale*font_line_height
    else:
        YLineOffset = YScale * font_line_height * YLineOffset/100.


    for index, item in enumerate(stringlist):
        code(item, index, index == (len(stringlist) - 1))


# ===============================================================================================

if __name__ == "__main__":
    main()

# ===============================================================================================END
