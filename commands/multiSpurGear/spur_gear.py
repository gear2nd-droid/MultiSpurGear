import adsk.core, adsk.fusion, adsk.cam, traceback
import math

_app = adsk.core.Application.get()
_ui  = _app.userInterface
_units = ''

# Calculate points along an involute curve.
def involutePoint(baseCircleRadius, distFromCenterToInvolutePoint):
    try:
        # Calculate the other side of the right-angle triangle defined by the base circle and the current distance radius.
        # This is also the length of the involute chord as it comes off of the base circle.
        triangleSide = math.sqrt(math.pow(distFromCenterToInvolutePoint,2) - math.pow(baseCircleRadius,2)) 
        
        # Calculate the angle of the involute.
        alpha = triangleSide / baseCircleRadius

        # Calculate the angle where the current involute point is.
        theta = alpha - math.acos(baseCircleRadius / distFromCenterToInvolutePoint)

        # Calculate the coordinates of the involute point.    
        x = distFromCenterToInvolutePoint * math.cos(theta)
        y = distFromCenterToInvolutePoint * math.sin(theta)

        # Create a point to return.        
        return adsk.core.Point3D.create(x, y, 0)
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Builds a spur gear.
#def drawGear(design, diametralPitch, numTeeth, thickness, rootFilletRad, pressureAngle, backlash, holeDiam, x, y, angle):
def drawGear(design, diametralPitch, numTeeth, thickness, rootFilletRad, pressureAngle, backlash, holeDiam):
    try:
        # The diametral pitch is specified in inches but everthing
        # here expects all distances to be in centimeters, so convert
        # for the gear creation.
        diametralPitch = diametralPitch / 2.54
    
        # Compute the various values for a gear.
        pitchDia = numTeeth / diametralPitch
        
        #addendum = 1.0 / diametralPitch
        if (diametralPitch < (20 *(math.pi/180))-0.000001):
            dedendum = 1.157 / diametralPitch
        else:
            circularPitch = math.pi / diametralPitch
            if circularPitch >= 20:
                dedendum = 1.25 / diametralPitch
            else:
                dedendum = (1.2 / diametralPitch) + (.002 * 2.54)                

        rootDia = pitchDia - (2 * dedendum)
        
        baseCircleDia = pitchDia * math.cos(pressureAngle)
        outsideDia = (numTeeth + 2) / diametralPitch
        
        # Create a new component by creating an occurrence.
        occs = design.rootComponent.occurrences
        mat = adsk.core.Matrix3D.create()
        newOcc = occs.addNewComponent(mat)        
        newComp = adsk.fusion.Component.cast(newOcc.component)
        
        # Create a new sketch.
        sketches = newComp.sketches
        xyPlane = newComp.xYConstructionPlane
        baseSketch = sketches.add(xyPlane)

        # Draw a circle for the base.
        baseSketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), rootDia/2.0)
        
        # Draw a circle for the center hole, if the value is greater than 0.
        prof = adsk.fusion.Profile.cast(None)
        if holeDiam - (_app.pointTolerance * 2) > 0:
            baseSketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), holeDiam/2.0)
            
            # Find the profile that uses both circles.
            for prof in baseSketch.profiles:
                if prof.profileLoops.count == 2:
                    break
        else:
            # Use the single profile.
            prof = baseSketch.profiles.item(0)
        
        #### Extrude the circle to create the base of the gear.

        # Create an extrusion input to be able to define the input needed for an extrusion
        # while specifying the profile and that a new component is to be created
        extrudes = newComp.features.extrudeFeatures
        extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

        # Define that the extent is a distance extent of 5 cm.
        distance = adsk.core.ValueInput.createByReal(thickness)
        extInput.setDistanceExtent(False, distance)

        # Create the extrusion.
        baseExtrude = extrudes.add(extInput)
        
        # Create a second sketch for the tooth.
        toothSketch = sketches.add(xyPlane)

        # Calculate points along the involute curve.
        involutePointCount = 15 
        involuteIntersectionRadius = baseCircleDia / 2.0
        involutePoints = []
        involuteSize = (outsideDia - baseCircleDia) / 2.0
        for i in range(0, involutePointCount):
            involuteIntersectionRadius = (baseCircleDia / 2.0) + ((involuteSize / (involutePointCount - 1)) * i)
            newPoint = involutePoint(baseCircleDia / 2.0, involuteIntersectionRadius)
            involutePoints.append(newPoint)
            
        # Get the point along the tooth that's at the pictch diameter and then
        # calculate the angle to that point.
        pitchInvolutePoint = involutePoint(baseCircleDia / 2.0, pitchDia / 2.0)
        pitchPointAngle = math.atan(pitchInvolutePoint.y / pitchInvolutePoint.x)

        # Determine the angle defined by the tooth thickness as measured at
        # the pitch diameter circle.
        toothThicknessAngle = (2 * math.pi) / (2 * numTeeth)
        
        # Determine the angle needed for the specified backlash.
        backlashAngle = (backlash / (pitchDia / 2.0)) * .25
        
        # Determine the angle to rotate the curve.
        rotateAngle = -((toothThicknessAngle/2) + pitchPointAngle - backlashAngle)
        
        # Rotate the involute so the middle of the tooth lies on the x axis.
        cosAngle = math.cos(rotateAngle)
        sinAngle = math.sin(rotateAngle)
        for i in range(0, involutePointCount):
            newX = involutePoints[i].x * cosAngle - involutePoints[i].y * sinAngle
            newY = involutePoints[i].x * sinAngle + involutePoints[i].y * cosAngle
            involutePoints[i] = adsk.core.Point3D.create(newX, newY, 0)
            #involutePoints[i] = adsk.core.Point3D.create(newX + x, newY + y, 0)

        # Create a new set of points with a negated y.  This effectively mirrors the original
        # points about the X axis.
        involute2Points = []
        for i in range(0, involutePointCount):
            involute2Points.append(adsk.core.Point3D.create(involutePoints[i].x, -involutePoints[i].y, 0))

        curve1Dist = []
        curve1Angle = []
        for i in range(0, involutePointCount):
            curve1Dist.append(math.sqrt(involutePoints[i].x * involutePoints[i].x + involutePoints[i].y * involutePoints[i].y))
            curve1Angle.append(math.atan(involutePoints[i].y / involutePoints[i].x))
        
        curve2Dist = []
        curve2Angle = []
        for i in range(0, involutePointCount):
            curve2Dist.append(math.sqrt(involute2Points[i].x * involute2Points[i].x + involute2Points[i].y * involute2Points[i].y))
            curve2Angle.append(math.atan(involute2Points[i].y / involute2Points[i].x))

        toothSketch.isComputeDeferred = True
		
        # Create and load an object collection with the points.
        pointSet = adsk.core.ObjectCollection.create()
        for i in range(0, involutePointCount):
            pointSet.add(involutePoints[i])

        # Create the first spline.
        spline1 = toothSketch.sketchCurves.sketchFittedSplines.add(pointSet)

        # Add the involute points for the second spline to an ObjectCollection.
        pointSet = adsk.core.ObjectCollection.create()
        for i in range(0, involutePointCount):
            pointSet.add(involute2Points[i])

        # Create the second spline.
        spline2 = toothSketch.sketchCurves.sketchFittedSplines.add(pointSet)

        # Draw the arc for the top of the tooth.
        midPoint = adsk.core.Point3D.create((outsideDia / 2), 0, 0)
        toothSketch.sketchCurves.sketchArcs.addByThreePoints(spline1.endSketchPoint, midPoint, spline2.endSketchPoint)     

        # Check to see if involute goes down to the root or not.  If not, then
        # create lines to connect the involute to the root.
        if( baseCircleDia < rootDia ):
            toothSketch.sketchCurves.sketchLines.addByTwoPoints(spline2.startSketchPoint, spline1.startSketchPoint)
        else:
            rootPoint1 = adsk.core.Point3D.create((rootDia / 2 - 0.001) * math.cos(curve1Angle[0] ), (rootDia / 2) * math.sin(curve1Angle[0]), 0)
            line1 = toothSketch.sketchCurves.sketchLines.addByTwoPoints(rootPoint1, spline1.startSketchPoint)

            rootPoint2 = adsk.core.Point3D.create((rootDia / 2 - 0.001) * math.cos(curve2Angle[0]), (rootDia / 2) * math.sin(curve2Angle[0]), 0)
            line2 = toothSketch.sketchCurves.sketchLines.addByTwoPoints(rootPoint2, spline2.startSketchPoint)

            baseLine = toothSketch.sketchCurves.sketchLines.addByTwoPoints(line1.startSketchPoint, line2.startSketchPoint)

            # Make the lines tangent to the spline so the root fillet will behave correctly.            
            line1.isFixed = True
            line2.isFixed = True
            toothSketch.geometricConstraints.addTangent(spline1, line1)
            toothSketch.geometricConstraints.addTangent(spline2, line2)
       
        toothSketch.isComputeDeferred = False

        ### Extrude the tooth.
        
        # Get the profile defined by the tooth.
        prof = toothSketch.profiles.item(0)

        # Create an extrusion input to be able to define the input needed for an extrusion
        # while specifying the profile and that a new component is to be created
        extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.JoinFeatureOperation)

        # Define that the extent is a distance extent of 5 cm.
        distance = adsk.core.ValueInput.createByReal(thickness)
        extInput.setDistanceExtent(False, distance)

        # Create the extrusion.
        toothExtrude = extrudes.add(extInput)

        baseFillet = None
        if rootFilletRad > 0:
            ### Find the edges between the base cylinder and the tooth.
            
            # Get the outer cylindrical face from the base extrusion by checking the number
            # of edges and if it's 2 get the other one.
            cylFace = baseExtrude.sideFaces.item(0)
            if cylFace.edges.count == 2:
                cylFace = baseExtrude.sideFaces.item(1)
    
            # Get the two linear edges, which are the connection between the cylinder and tooth.
            edges = adsk.core.ObjectCollection.create()
            for edge in cylFace.edges:
                if isinstance(edge.geometry, adsk.core.Line3D):
                    edges.add(edge)
    
            # Create a fillet input to be able to define the input needed for a fillet.
            fillets = newComp.features.filletFeatures;
            filletInput = fillets.createInput()
    
            # Define that the extent is a distance extent of 5 cm.
            radius = adsk.core.ValueInput.createByReal(rootFilletRad)
            filletInput.addConstantRadiusEdgeSet(edges, radius, False)
    
            # Create the extrusion.
            baseFillet = fillets.add(filletInput)

        # Create a pattern of the tooth extrude and the base fillet.
        circularPatterns = newComp.features.circularPatternFeatures
        entities = adsk.core.ObjectCollection.create()
        entities.add(toothExtrude)
        if baseFillet:
            entities.add(baseFillet)
        cylFace = baseExtrude.sideFaces.item(0)        
        patternInput = circularPatterns.createInput(entities, cylFace)
        numTeethInput = adsk.core.ValueInput.createByString(str(numTeeth))
        patternInput.quantity = numTeethInput
        patternInput.patternComputeOption = adsk.fusion.PatternComputeOptions.IdenticalPatternCompute        
        pattern = circularPatterns.add(patternInput)        
        
        # Create an extra sketch that contains a circle of the diametral pitch.
        diametralPitchSketch = sketches.add(xyPlane)
        diametralPitchCircle = diametralPitchSketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), pitchDia/2.0)
        diametralPitchCircle.isConstruction = True
        diametralPitchCircle.isFixed = True
        diametralPitchSketch.isVisible = False
        
        # Group everything used to create the gear in the timeline.
        timelineGroups = design.timeline.timelineGroups
        newOccIndex = newOcc.timelineObject.index
        pitchSketchIndex = diametralPitchSketch.timelineObject.index
        # ui.messageBox("Indices: " + str(newOccIndex) + ", " + str(pitchSketchIndex))
        timelineGroup = timelineGroups.add(newOccIndex, pitchSketchIndex)
        timelineGroup.name = 'Spur Gear'
        
        # Add an attribute to the component with all of the input values.  This might 
        # be used in the future to be able to edit the gear.     
        gearValues = {}
        gearValues['diametralPitch'] = str(diametralPitch * 2.54)
        gearValues['numTeeth'] = str(numTeeth)
        gearValues['thickness'] = str(thickness)
        gearValues['rootFilletRad'] = str(rootFilletRad)
        gearValues['pressureAngle'] = str(pressureAngle)
        gearValues['holeDiam'] = str(holeDiam)
        gearValues['backlash'] = str(backlash)
        attrib = newComp.attributes.add('SpurGear', 'Values',str(gearValues))
        
        newComp.name = 'Spur Gear (' + str(numTeeth) + ' teeth)'
        return newComp
    except Exception as error:
        _ui.messageBox("drawGear Failed : " + str(error)) 
        return None