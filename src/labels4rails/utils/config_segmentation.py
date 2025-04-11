from dataclasses import dataclass


@dataclass
class Images:
    path: str
    extensions: set


@dataclass
class Paths:
    camera_extrinsic: str
    images: Images
    annotations: str


@dataclass
class Data:
    paths: Paths
    tags: list[str]
    track_width: int  # mm
    rail_width: int  # mm


@dataclass
class TrackBed:
    export_mask_color: int 
    fill_color: tuple[int, int, int]  # RGB
    contour_color: tuple[int, int, int]  # RGB
    interpolation_steps: int  # Between two marks


@dataclass
class Rail:
    export_mask_color: int 
    marks_color: tuple[int, int, int]  # RGB
    splines_color: tuple[int, int, int]  # RGB
    contour_color: tuple[int, int, int]  # RGB
    fill_color: tuple[int, int, int]  # RGB
    interpolation_steps: int  # Between two marks


@dataclass
class Track:
    marks_transparency: float  # 0.0 to 1.0
    splines_transparency: float  # 0.0 to 1.0
    contour_transparency: float  # 0.0 to 1.0
    fill_transparency: float  # 0.0 to 1.0
    track_bed: TrackBed
    left_rail: Rail
    right_rail: Rail


@dataclass
class Tracks:
    ego: Track
    left: Track
    right: Track
    drawing_order: tuple[tuple[str,str]]
    selected: Track


@dataclass
class SwitchDirection:
    marks_color: tuple[int, int, int]  # RGB
    marks_radius: float  # 0.0 to 1.0 relative to image width
    box_color: tuple[int, int, int]  # RGB
    box_thickness: float  # 0.0 to 1.0 relative to image width


@dataclass
class Switch:
    left: SwitchDirection
    right: SwitchDirection
    unknown: SwitchDirection
    selected: SwitchDirection


@dataclass
class Switches:
    marks_transparency: float  # 0.0 to 1.0
    box_transparency: float  # 0.0 to 1.0
    fork: Switch
    merge: Switch
    unknown: Switch


@dataclass
class Tags:
    track_layout: tuple[str]
    weather: tuple[str]
    light: tuple[str]
    time_of_day: tuple[str]
    environment: tuple[str]
    additional: tuple[str]


@dataclass(frozen=True)
class Targets:
    tracks: Tracks
    switches: Switches
    tags: Tags


@dataclass
class TrackStencil:
    color: tuple[int, int, int]  # RGB
    thickness: float  # 0.0 to 1.0 relative to image width
    transparency: float  # 0.0 to 1.0
    hair_to_midpoint_distance: int  # in Px
    track_width: int  # mm
    rail_width: int  # mm


@dataclass
class CrossHair:
    color: tuple[int, int, int]  # RGB
    transparency: float  # 0.0 to 1.0
    thickness: float  # 0.0 to 1.0 relative to image width
    mid_point_radius: float  # 0.0 to 1.0 relative to image width
    hair_to_midpoint_distance: float  # 0.0 to 1.0 relative to image width
    mid_point_buffer: float  # 0.0 to 1.0 relative to image width


@dataclass
class AimingDevices:
    track_stencil = TrackStencil
    cross_hair = CrossHair

@dataclass
class Included:
    additional_attributes: tuple[str]
    environment: tuple[str]
    light: tuple[str]
    time_of_day: tuple[str]
    track_layout: tuple[str]
    weather: tuple[str]

@dataclass
class Excluded:
    additional_attributes: tuple[str]
    environment: tuple[str]
    light: tuple[str]
    time_of_day: tuple[str]
    track_layout: tuple[str]
    weather: tuple[str]
    
    
@dataclass
class Labels4RailsConfig:
    data: Data
    targets: Targets
    aiming_devices: AimingDevices

    # run mode
    run_mode: int
    included: Included
    excluded: Excluded
