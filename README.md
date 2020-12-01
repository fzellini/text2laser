# text2laser
text to gcode for laser cut machines

`
text2laser.py G-Code laser Engraving Generator for command-line usage
            bugfix and adapted to laser machines by Fabrizio Zellini on 2020
            (C) ArcEye <2012> 
            based upon code from engrave-11.py
            Copyright (C) <2008>  <Lawrence Glaister> <ve7it at shaw dot ca>
text2laser.py -X -x -i -Y -y -S -s -Z -D -C -W -M -F -P -p -a ..............
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
`
