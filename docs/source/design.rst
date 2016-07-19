Design
######

The base idea is to mimic QgsMapCanvas and to use the already avaiable rendering to render in the (s, z) plane instead of the (x, y) plane.

Definitions:

S 
    the LINESTRING definig the section

s
    curvilinear coordinate of a point on S (in length units if not lat/lon, in deg if lat/lon)

(s, z) 
    the section plane

(x, y) 
    the usual canvas plane

width
    the with of the section "plane" in wich data are projected

*Note* it could be wize to always store s in relative, such that OTF reprojection change can be taken into account without recomputing, but legth or surface computation become invalid in this case, same for marker sizes etc.

Section definition
==================

The section is defined by a LINESTRING (S) in the (x, y) plane.

Within a parametrable width around this LINESTRING, layer data are projected on the section "plane".

Projected data
==============

The geometry of projected data is expressed in 2D (r, z) coordinates.

The curvilinear coordinate can be obtained with geos LineString.project function (not available with QgsGeometry, but something like QgsGeometry.asGeos().project(Point(x,y)) should do the trick).

To avoid looping in python and handling all geometry cases, we could use QgsGeometry.transform(QgsCoordinateTransform) and give a custom instance of QgsCoordinateTransform with overloaded `transform` function to do the projection. The class is fairly complex, better look at the implementation to know wich functions should be overloaded.

The projected data are stored as memory layers in the section canvas (they are not visible in the layer tree and not stored in QgsMapLayerRegistry).

**Note**: make sure that all data specific to a given section are groupped together in the Canvas class, such that on section change, they can all be delete and rebuild from scratch.



