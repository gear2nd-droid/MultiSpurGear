import adsk.core
import os
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface
from .spur_gear import *


# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'Multi spur Gear'
CMD_Description = 'Selected pitch circles to spur gears.'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    #futil.log(f'{CMD_NAME} Command Created Event')

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # TODO Define the dialog for your command by adding different inputs to the command.

    # select circle button
    sel_circles = inputs.addSelectionInput('circles_select', 'Circles', 'Select circles')
    sel_circles.selectionFilters = ['SketchCircles']
    sel_circles.setSelectionLimits(0, 0)
    inputs.addValueInput('pressure_angle', 'Pressure angle', 'degree',  adsk.core.ValueInput.createByReal(math.radians(20.0)))
    inputs.addValueInput('module', 'Module', 'mm',  adsk.core.ValueInput.createByReal(0.1))
    inputs.addValueInput('backlash', 'Backlash', 'mm',  adsk.core.ValueInput.createByReal(0.0))
    inputs.addValueInput('root_filter_rad', 'Root filter radius', 'mm',  adsk.core.ValueInput.createByReal(0.05))
    inputs.addValueInput('thickness', 'Thickness', 'mm',  adsk.core.ValueInput.createByReal(0.1))
    inputs.addValueInput('hole_diam', 'Hole diameter', 'mm',  adsk.core.ValueInput.createByReal(0.1))

    # TODO Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')
    des = adsk.fusion.Design.cast(app.activeProduct)
    rootComp = des.rootComponent
    features = rootComp.features

    # TODO ******************************** Your code here ********************************

    # Get a reference to your command's inputs.
    inputs = args.command.commandInputs
    sel_circles: adsk.core.SelectionCommandInput = inputs.itemById('circles_select')    
    pressure_angle: adsk.core.ValueCommandInput = inputs.itemById('pressure_angle')
    module: adsk.core.ValueCommandInput = inputs.itemById('module')
    backlash: adsk.core.ValueCommandInput = inputs.itemById('backlash')
    root_filter_rad: adsk.core.ValueCommandInput = inputs.itemById('root_filter_rad')
    thickness: adsk.core.ValueCommandInput = inputs.itemById('thickness')
    hole_diam: adsk.core.ValueCommandInput = inputs.itemById('hole_diam')

    # create gear
    cnt = sel_circles.selectionCount
    ents = [sel_circles.selection(i).entity for i in range(sel_circles.selectionCount)]
    
    # param
    val_pressure_angle = pressure_angle.value
    val_module = 25.4 / module.value / 10.0
    val_backlash = backlash.value
    val_root_filter_rad = root_filter_rad.value
    val_thickness = thickness.value
    val_hole_diam = hole_diam.value

    pxs = []
    pys = []
    pzs = []
    sxs = []
    sys = []
    x_dirs = []
    y_dirs = []
    nxs = []
    nys = []
    nzs = []
    rs = []
    ts = []
    angles = []
    pairs = []

    for ent in ents:
        ent = adsk.fusion.SketchCircle.cast(ent)
        r = ent.radius
        rs.append(r)
        t = round(r * 2.0 / module.value)
        ts.append(t)
        # get position
        sxs.append(ent.centerSketchPoint.geometry.x)
        sys.append(ent.centerSketchPoint.geometry.y)
        pxs.append(ent.centerSketchPoint.worldGeometry.x)
        pys.append(ent.centerSketchPoint.worldGeometry.y)
        pzs.append(ent.centerSketchPoint.worldGeometry.z)
        pairs.append(-1)
        angles.append(0.0)
        x_dir = ent.parentSketch.xDirection
        y_dir = ent.parentSketch.yDirection
        x_dirs.append(x_dir)
        y_dirs.append(y_dir)
        # calc norm
        nx = x_dir.y * y_dir.z - x_dir.z * y_dir.y
        ny = x_dir.z * y_dir.x - x_dir.x * y_dir.z
        nz = x_dir.x * y_dir.y - x_dir.y * y_dir.x
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        nx = nx / ln
        ny = ny / ln
        nz = nz / ln
        #futil.log('nx{0},ny{1},nz{2}'.format(nx, ny, nz))
        nxs.append(nx)
        nys.append(ny)
        nzs.append(nz)

    
    for i in range(1, len(ents)):
        for j in range(0, i):
            #futil.log('nxsi{0},nxsj{1},nysi{2},nysj{3},nzsi{4},nzsj{5}'.format(nxs[i],nxs[j],nys[i],nys[j],nzs[i],nzs[j]))
            if nxs[i]==nxs[j] and nys[i]==nys[j] and nzs[i]==nzs[j]:
                d = math.sqrt((sxs[i]-sxs[j])**2 + (sys[i]-sys[j])**2)
                if round(d / module.value * 2.0) == (ts[i] + ts[j]):
                    #futil.log('{0}pair{1}'.format(i,j))
                    pairs[i] = j
                    break
                    
    for i in range(len(ents)):
        buf = drawGear(des, val_module, ts[i], val_thickness, val_root_filter_rad, val_pressure_angle, val_backlash, val_hole_diam)
        gearComp = adsk.fusion.Component.cast(buf)

        features = gearComp.features 
        moveFeats = features.moveFeatures
        target = adsk.core.ObjectCollection.create()
        target.add(gearComp.bRepBodies.item(0))

        # rotate
        if pairs[i]!=-1:
            j = pairs[i]
            base_angle = -(angles[j] - math.pi / 2.0 / ts[j]) * ts[j] / ts[i] + math.pi / 2.0 / ts[i]
            delta_angle = math.atan2(sys[i] - sys[j], sxs[i] - sxs[j])
            rot_angle = delta_angle * (1 + ts[j] / ts[i])
            angle = math.pi + base_angle + rot_angle
            angles[i] = angle
            #futil.log('angleA{0}'.format(angle))
        else:
            angle = math.pi / 2.0 / ts[i]
            angles[i] = angle
            #futil.log('angleB{0}'.format(angle))
        rotTrans = adsk.core.Matrix3D.create()
        rotTrans.setToRotateTo(adsk.core.Vector3D.create(1,0,0), adsk.core.Vector3D.create(math.cos(angle), math.sin(angle), 0.0))
        moveFeatureInput = moveFeats.createInput(target, rotTrans)
        moveFeats.add(moveFeatureInput)

        # plane change
        if nxs[i]!=0 or nys[i]!=0 or nzs[i]!=1:
            rotTrans = adsk.core.Matrix3D.create()
            rotTrans.setToRotateTo(adsk.core.Vector3D.create(0,0,1), adsk.core.Vector3D.create(nxs[i],nys[i],nzs[i]))
            moveFeatureInput = moveFeats.createInput(target, rotTrans)
            moveFeats.add(moveFeatureInput)

        # transform
        if pxs[i]!=0 or pys[i]!=0 or pzs[i]!=0:
            moveTrans = adsk.core.Matrix3D.create()
            vector = adsk.core.Vector3D.create(pxs[i], pys[i], pzs[i])
            moveTrans.translation = vector
            moveFeatureInput = moveFeats.createInput(target, moveTrans)
            moveFeats.add(moveFeatureInput)



# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    #futil.log(f'{CMD_NAME} Command Preview Event')
    inputs = args.command.commandInputs


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs

    # General logging for debug.
    #futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    #futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs
    enflag = True
    # inputs
    sel_circles: adsk.core.SelectionCommandInput = inputs.itemById('circles_select')    
    pressure_angle: adsk.core.ValueCommandInput = inputs.itemById('pressure_angle')
    module: adsk.core.ValueCommandInput = inputs.itemById('module')
    backlash: adsk.core.ValueCommandInput = inputs.itemById('backlash')
    root_filter_rad: adsk.core.ValueCommandInput = inputs.itemById('root_filter_rad')
    thickness: adsk.core.ValueCommandInput = inputs.itemById('thickness')
    hole_diam: adsk.core.ValueCommandInput = inputs.itemById('hole_diam')
    # check
    if sel_circles.selectionCount == 0:
        enflag = False
    if pressure_angle.value <= 0:
        enflag = False
    if module.value <= 0:    
        enflag = False
    if backlash.value < 0:    
        enflag = False
    if root_filter_rad.value < 0:    
        enflag = False
    if thickness.value <= 0:    
        enflag = False
    if hole_diam.value <= 0:    
        enflag = False
    # enable
    args.areInputsValid = enflag
        

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []
