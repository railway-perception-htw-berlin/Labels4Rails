import json
import os
import yaml
from labels4rails.utils import config


class TagFilter:
    def __init__(self, path, cfg: config.Labels4RailsConfig):
        """
        Tagfilter: Creates a list of files in a specified annotations folder and saves in self.annotationsList

        @param path: path to the annotations folder
        @param path_to_yaml: optional path to different yaml. default(recommended): src/conf/config.yaml

        """
        
        self.__includedTags = {
            "additional_attributes": cfg.included.additional_attributes,
            "environment": cfg.included.environment,
            "light": cfg.included.light,
            "time_of_day": cfg.included.time_of_day,
            "track_layout": cfg.included.track_layout,
            "weather": cfg.included.weather,
            }
        self.__excludedTags = {
            "additional_attributes": cfg.excluded.additional_attributes,
            "environment": cfg.excluded.environment,
            "light": cfg.excluded.light,
            "time_of_day": cfg.excluded.time_of_day,
            "track_layout": cfg.excluded.track_layout,
            "weather": cfg.excluded.weather,
            }
        self.__path = str(path)
        self.annotationList = []
        self.__createAnnotations()


    def __createAnnotations(self):
        for file in os.listdir(self.__path):
            filename = os.fsdecode(file)
            if filename.endswith(".json"):
                if all(value == [None] * len(value) for value in self.__excludedTags.values()):
                    self.__checkIncluded(file)
                elif all(value == [None] * len(value) for value in self.__includedTags.values()):
                    self.__checkExcluded(filename)
                else:
                    self.__checkIncludedAndExcluded(filename)

    def __checkIncluded(self, filename):
        with open(self.__path + "/" + filename) as file:
            bol = dict.fromkeys(self.__includedTags.keys(), True)
            data = json.load(file)["tag groups"]
            for group, tag in self.__includedTags.items():
                tag = list(filter(None, tag))
                if not all(elem.lower() in data[group] for elem in tag):
                    bol[group] = False
            if all(value == True for value in bol.values()):
                self.annotationList.append(filename.removesuffix(".json"))

    def __checkExcluded(self, filename):
        with open(self.__path + "/" + filename) as file:
            bol = dict.fromkeys(self.__includedTags.keys(), True)
            data = json.load(file)["tag groups"]

            for group, tag in self.__excludedTags.items():
                L = list(tag)
                if L != [None] * len(L):
                    tag = list(filter(None, tag))
                    if any(elem.lower() in data[group] for elem in tag):
                        bol[group] = False
            if all(value == True for value in bol.values()):
                self.annotationList.append(filename.removesuffix(".json"))

    def __checkIncludedAndExcluded(self, filename):
        with open(self.__path + "/" + filename) as file:
            bol = dict.fromkeys(self.__includedTags.keys(), True)
            data = json.load(file)
            data = data["tag groups"]
            for group, tag in self.__includedTags.items():
                incTag = list(filter(None, tag))
                excTag = list(filter(None, self.__excludedTags[group]))
                if len(excTag) == 0 and len(incTag) != 0 and not all(elem.lower() in data[group] for elem in incTag):
                    bol[group] = False
                elif not all(elem.lower() in data[group] for elem in incTag) or any(
                        elem.lower() in data[group] for elem in excTag):
                    bol[group] = False

            if all(value == True for value in bol.values()):
                self.annotationList.append(filename.removesuffix(".json"))
