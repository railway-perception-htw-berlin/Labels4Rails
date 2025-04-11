#!/usr/bin/env python3
import hydra.core.config_store
from hydra import compose, initialize
from typing import Optional
import argparse
import pathlib

from src import data
from src import label_conversion
from src.utils.config import Labels4RailsConfig

config_store = hydra.core.config_store.ConfigStore.instance()
config_store.store(name="rail_label_config", node=Labels4RailsConfig)

def main(data_path_in_list, data_path_out, cfg_file: Optional[str]): 
    cfg: Labels4RailsConfig = None
    if cfg_file:
        if pathlib.Path(cfg_file).is_absolute():
            cfg_file = pathlib.Path(cfg_file).relative_to(pathlib.Path(__file__).parent)
        initialize(config_path=str(pathlib.Path(cfg_file).parent))
        cfg = compose(config_name=pathlib.Path(cfg_file).name)
    for data_path_in in data_path_in_list:
        output_pth = pathlib.Path(data_path_in).joinpath(data_path_out)
        if output_pth.exists() == False:
            output_pth.mkdir(parents=True, exist_ok=True)

        label_converter_pm = label_conversion.label_converter.LabelConverterPixelmask(None, cfg, data_path_in)
        label_converter_pm.generate_track_labels(output_pth)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create pixelmasks.')
    parser.add_argument('in_data_path', type=str, nargs='+', help='path to data batch (the directory that contains images, annotations and camera)')
    parser.add_argument('out_data_path', type=str, help='path to resulting Yolo labels relative to in_data_path')
    parser.add_argument('-c', '--config_file', type=str, help="relative path to config file")
    
    args = parser.parse_args()

    main(args.in_data_path, args.out_data_path, args.config_file)
