import pathlib
import argparse
import hydra.core.config_store
from hydra import compose, initialize
from typing import Optional
from labels4rails import scene, label_conversion, data
from labels4rails.utils.config import Labels4RailsConfig

config_store = hydra.core.config_store.ConfigStore.instance()
config_store.store(name="rail_label_config", node=Labels4RailsConfig)

def main(data_path_in : str, data_path_out : str, cfg_file : Optional[str]):
    cfg: Labels4RailsConfig = None
    if cfg_file:
        if pathlib.Path(cfg_file).is_absolute():
            cfg_file = pathlib.Path(cfg_file).relative_to(pathlib.Path(__file__).parent)
        initialize(config_path=str(pathlib.Path(cfg_file).parent))
        cfg = compose(config_name=pathlib.Path(cfg_file).name)

    # Call from ML Experiment
    output_pth = pathlib.Path(data_path_in).joinpath(data_path_out)
    if output_pth.exists() == False:
        output_pth.mkdir(parents=True, exist_ok=True)
    
    directions = [
        scene.target.SwitchDirection.LEFT,
        scene.target.SwitchDirection.RIGHT,
        scene.target.SwitchDirection.UNKNOWN,
    ]
    kinds = [
        scene.target.SwitchKind.FORK,
        scene.target.SwitchKind.MERGE,
        #scene.target.SwitchKind.UNKNOWN,
    ]

    dataset: data.IDataSet = data.DataSet(None, data_path_in)
    label_converter_yolo = label_conversion.LabelConverterYOLO(dataset, cfg)
    label_converter_yolo.generate_switch_labels(output_pth, kinds, directions)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create YOLO labels.')
    parser.add_argument('in_data_path', type=str, nargs='+', help='path to data batch (the directory that contains images, annotations and camera)')
    parser.add_argument('out_data_path', type=str, nargs='+', help='path to resulting Yolo labels relative to in_data_path')
    parser.add_argument('-c', '--config_file', type=str, help="relative path to config file")
    
    args = parser.parse_args()
    main(args.in_data_path[0], args.out_data_path[0], args.config_file)

#Aufrufen mit D:\data\test_000 YOLO 