import enum


class GuiEvents(enum.IntEnum):
    # General
    EXIT = 0  # Exit program
    SETTINGS_BRINGTOFRONT = enum.auto()

    NEXT = enum.auto()  # Next scene
    PREVIOUS = enum.auto()  # Previous scene
    SCENE_NAME = enum.auto()
    SCENE_COUNT = enum.auto()
    LOAD_SCENE = enum.auto()

    MARK = enum.auto()  # Set annotation
    REMOVE = enum.auto()  # Remove annotation

    DISPLAY = enum.auto()  # Initiate scene draw
    STRATEGY = enum.auto()  # Change annotation strategy

    # Track related
    TRACK_CREATE_EGO = enum.auto()
    TRACK_CREATE_LEFT = enum.auto()
    TRACK_CREATE_RIGHT = enum.auto()
    TRACK_DELETE = enum.auto()
    TRACK_SELECT = enum.auto()
    TRACK_MARKS = enum.auto()
    TRACK_SPLINES = enum.auto()
    TRACK_CONTOUR = enum.auto()
    TRACK_FILL = enum.auto()
    TRACK_LIST_UPDATE = enum.auto()
    TRACK_STENCIL_SIDE = enum.auto()  # Flip stencil side
    TRACK_UPDATE_LIST = enum.auto()
    TRACK_WIDTH_INCR = enum.auto()  # Increment stencil width
    TRACK_WIDTH_DECR = enum.auto()  # Decrement stencil width
    TRACK_ANGLE_INCR = enum.auto()  # Increment stencil angle
    TRACK_ANGLE_DECR = enum.auto()  # Decrement stencil angle
    TRACK_CREATE = enum.auto()  # Create new track
    TRACK_UPDATE_SELECTED = enum.auto()
    TRACK_CHANGE_POSITION= enum.auto()
    INDEPENDENT_MODE = enum.auto()
    AUTO_LABELING_TRACK = enum.auto()
    SEMI_AUTO_LABELING_TRACK = enum.auto()
    DRAG = enum.auto()
    DROP = enum.auto()

    # Switch related
    SWITCH_FORK_RIGHT = enum.auto()  # Create new Switch
    SWITCH_FORK_LEFT = enum.auto()  # Create new Switch
    SWITCH_FORK_UNKNOWN = enum.auto()
    SWITCH_MERGE_RIGHT = enum.auto()  # Create new Switch
    SWITCH_MERGE_LEFT = enum.auto()  # Create new Switch
    SWITCH_MERGE_UNKNOWN = enum.auto()
    SWITCH_UNKNOWN_LEFT = enum.auto()
    SWITCH_UNKNOWN_RIGHT = enum.auto()
    SWITCH_UNKNOWN_UNKNOWN = enum.auto()
    SWITCH_UPDATE_LIST = enum.auto()
    SWITCH_DELETE = enum.auto()
    SWITCH_SELECT = enum.auto()
    SWITCH_SHOW_BOX = enum.auto()
    SWITCH_SHOW_MARKS = enum.auto()
    SWITCH_SHOW_TEXT = enum.auto()
    SWITCH_LIST_UPDATE = enum.auto()
    SWITCH_UPDATE_SELECTED = enum.auto()
    SWITCH_CHANGE_SWITCH = enum.auto()
    AUTO_LABELING_SWITCH = enum.auto()

    # Tag related
    TAG_TRACK_LAYOUT = enum.auto()
    TAG_WEATHER = enum.auto()
    TAG_LIGHT = enum.auto()
    TAG_TIME_OF_DAY = enum.auto()
    TAG_ENVIRONMENT = enum.auto()
    TAG_ADDITIONAL = enum.auto()

    #TAG_TRACK_LAYOUT_LIST_UPDATE = enum.auto()
    #TAG_WEATHER_LIST_UPDATE = enum.auto()
    #TAG_LIGHT_LIST_UPDATE = enum.auto()
    #TAG_TIME_OF_DAY_LIST_UPDATE = enum.auto()
    #TAG_ENVIRONMENT_LIST_UPDATE = enum.auto()
    #TAG_ADDITIONAL_LIST_UPDATE = enum.auto()
    TAG_ALL_LISTS_UPDATE = enum.auto()
    TAG_COPY = enum.auto()
    TAG_COPY_OVERWRITE = enum.auto()
