import rtoml
import json
from typing import Callable, List, Union
import time
from tqdm import tqdm
import logging
from pathlib import Path, PosixPath

from .shared import shared

colors = {
        "red": "\033[91m",
        "yellow": "\033[93m",
        "reset": "\033[0m",
        "white": "\033[0m",
        "purple": "\033[95m",
        }

def create_logger(local_file):
    """Create a logger that writes to both a file and terminal with color support.

    Args:
        local_file: Path to the log file. Must exist.

    Returns:
        Callable: A function that takes a color name and returns a logging function.
        The returned logging function accepts a string and optional kwargs, writes
        the message to the log file, prints it to terminal with color, and returns
        the original input.
    """
    assert Path(local_file).exists()
    logging.basicConfig(filename=local_file,
                        filemode='a',
                        format=f"{time.ctime()}: %(message)s",
                        force=True,
                        )
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    def get_coloured_logger(color_asked: str) -> Callable:
        """used to print color coded logs"""
        col = colors[color_asked]

        # all logs are considered "errors" otherwise the datascience libs just
        # overwhelm the logs
        def printer(string: str, **args) -> str:
            inp = string
            if isinstance(string, dict):
                try:
                    string = rtoml.dumps(string, pretty=True)
                except Exception:
                    string = json.dumps(string, indent=2)
            if isinstance(string, list):
                try:
                    string = ",".join(string)
                except:
                    pass
            try:
                string = str(string)
            except:
                try:
                    string = string.__str__()
                except:
                    string = string.__repr__()
            log.info(string)
            tqdm.write(col + string + colors["reset"], **args)
            return inp
        return printer
    return get_coloured_logger


def create_loggers(local_file: Union[str, PosixPath], colors: List[str]):
    """Create multiple colored loggers at once.

    Args:
        local_file: Path to the log file. Must exist.
        colors: List of color names to create loggers for. Each color must exist
               in the colors dictionary.

    Returns:
        List[Callable]: A list of logging functions, one for each requested color.
        Each function writes colored messages to both terminal and log file.
    """
    coloured_logger = create_logger(local_file)
    out = []
    for col in colors:
        log = coloured_logger(col)
        setattr(shared, col, log)
        out.append(log)
    return out
