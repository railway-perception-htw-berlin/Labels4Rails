import json

def load_dict_from_json(file_path):
    """
    Load a dictionary from a JSON file.

    :param file_path: Path to the JSON file.
    :return: Dictionary loaded from the JSON file.
    """
    try:
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            return data
    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON in the file {file_path}.")
        return None

def dump_dict_to_json(data, file_path):
    """
    Dump a dictionary to a JSON file.

    :param data: Dictionary to save.
    :param file_path: Path to the JSON file.
    """
    try:
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)  # indent for pretty printing
            print(f"Dictionary successfully saved to {file_path}.")
    except TypeError:
        print("Error: The provided data is not serializable to JSON.")
    except IOError:
        print(f"Error: Could not write to file {file_path}.")

# Usage example
if __name__ == "__main__":
    # Define a sample dictionary
    sample_dict = {"name": "Alice", "age": 30, "city": "New York"}

    # Define the JSON file path
    json_file_path = "sample.json"

    # Dump the dictionary to a JSON file
    dump_dict_to_json(sample_dict, json_file_path)

    # Load the dictionary from the JSON file
    loaded_dict = load_dict_from_json(json_file_path)
    print("Loaded dictionary:", loaded_dict)
