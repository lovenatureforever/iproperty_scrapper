import datetime
import logging
import pathlib

def main_logger(module_name: str = "default") -> logging.Logger:
    log = logging.getLogger(module_name)
    log.setLevel(logging.DEBUG)
    log.propagate = False

    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)

    work_dir = pathlib.Path(__file__).parent.absolute()
    logs_dir = work_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / f'{module_name}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
    full_path = str(log_file.resolve())
    fh = logging.FileHandler(full_path)
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(funcName)s - %(message)s"
    )
    sh.setFormatter(formatter)
    fh.setFormatter(formatter)

    log.addHandler(sh)
    log.addHandler(fh)
    return log
