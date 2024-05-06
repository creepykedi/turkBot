import logging


def get_logger(name):
    logging.basicConfig(format=(
        f"%(asctime)s - %(name)s - "
        f"%(levelname)s - %(message)s"),
        level=logging.INFO)
    return logging.getLogger(name)
