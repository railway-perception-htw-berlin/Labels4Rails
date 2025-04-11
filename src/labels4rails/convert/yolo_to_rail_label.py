import argparse
import json
import numpy as np
import os
import cv2
from src import scene, data
from src.data import IDataSet,DataSet
from src.scene import Scene, IScene, ISceneSerializer,DictSceneSerializer
from src.scene.target import ISwitch, Switch, SwitchDirection, SwitchKind
from src.utils import config
from src.utils.geometry import ImagePoint, IImagePoint


def get_parameter(label_path):
    with open(label_path, "r") as f:
        param = []
        kinds = f.readlines()
        for elem in kinds:
            x = elem.split(",")
            kind = x[0].replace("kind:_", "")
            dir = x[1].replace("_direction:_", "").replace("\n", " ")
            param.append((kind, dir))
    return param

kind_direction = []


def getListOfFiles(dirName):
    # create a list of file and sub directories and return all files with .png ending
    # names in the given directory
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)

    return allFiles

def search(image_path,images,file):
    for x in images:
        filename = x.replace(image_path,"").replace(".png","")
        if filename == file:
            return x
def get_labels(label_path):
    labels = []
    if os.path.getsize(label_path)!= 0:
        with open(label_path, "r") as f:
            an = f.readlines()
            for param in an:
                param = param.split(" ")
                kind, x, y, w, h = int(param[0]), float(param[1]), float(param[2]), float(param[3]), float(
                    param[4].replace("/n", " "))
                labels.append((kind, x, y, w, h))
    return labels


def reverse_yolo(scene_path, image, list_of_kind_dir,save_path,filename):

    labels = get_labels(scene_path)
    if len(labels)==0:
        return None

    img = cv2.imread(image)
    dh, dw, _ = img.shape
    resolution = [dh, dw]
    scene : IScene
    scene = Scene()
    id = 0

    _scene_deserializer: ISceneSerializer
    _scene_deserializer = DictSceneSerializer()

    for label in labels:
        kind_lbl, x, y, w, h = label[0], label[1],label[2],label[3],label[4]

        center_x = x * resolution[1]

        center_y = y * resolution[0]
        diffx = w * resolution[1]
        diffy = h * resolution[0]

        matrix = np.array(([1, 1, 0, 0], [0, 0, 1, 1], [1, -1, 0, 0], [0, 0, 1, -1]))
        res = np.array([center_x * 2, center_y * 2, diffx, diffy])

        ans = np.linalg.solve(matrix, res)
        x1 = round(ans[0])
        x2 = round(ans[1])
        y1 = round(ans[2])
        y2 = round(ans[3])
        mark1 :IImagePoint = ImagePoint(x1,y1)
        mark2 :IImagePoint = ImagePoint(x2,y2)


        param = list_of_kind_dir[kind_lbl]
        switch: ISwitch
        direction :SwitchDirection = None
        kind :SwitchKind = None

        for ki in SwitchKind:
            if ki.value == (param[0].strip()):
                kind = ki

        for dire in SwitchDirection:
            if (dire.value) == ((param[1]).strip()):
                direction = dire




        switch = Switch(id,kind,direction)

        switch.add_mark([mark1])
        switch.add_mark([mark2])

        scene.switches[id] = switch

        id+=1


    annotations: dict = _scene_deserializer.serialize(scene)
    annotation_path = save_path+filename+".json"
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    with open(annotation_path, "w") as file_pointer:
        json.dump(annotations, file_pointer, indent=4, sort_keys=True)







def main (label_path,image_path,save_path):
    labels = getListOfFiles(label_path)
    images = getListOfFiles(image_path)
    sub = 'labels.txt'

    labels_txt = next((s for s in labels if sub in s), None)
    labels.remove(labels_txt)

    kind_direction = get_parameter(labels_txt)
    for label in labels:
        filename = label.replace(label_path, "").replace(".txt", "")
        image = search(image_path, images, filename)
        if image is None:
            print(f"THere was no images found for label {filename}!")
            break

        reverse_yolo(label,image,kind_direction,save_path,filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create RailLabel Annotations from YOLO labels.')
    parser.add_argument('label_path', type=str, help='path to the folder containing the yolo labels')
    parser.add_argument('image_path', type=str, help='path to the original images of the yolo labels')
    parser.add_argument('save_path', type=str, help="path to the directory where the annotations should be saved")

    args = parser.parse_args()

    main(args.label_path, args.image_path, args.save_path)