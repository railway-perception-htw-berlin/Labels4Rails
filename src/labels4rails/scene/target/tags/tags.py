import dataclasses


@dataclasses.dataclass
class TagGroups:
    track_layout: list[str]
    weather: list[str]
    light: list[str]
    time_of_day: list[str]
    environment: list[str]
    additional_attributes: list[str]
