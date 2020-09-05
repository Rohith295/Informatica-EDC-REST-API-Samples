import logging

from metadata_utilities import generic_settings
from datetime import datetime

class MULogging:
    code_version = "0.1.0"
    VERBOSE = 6
    DEBUG = 5
    INFO = 4
    WARNING = 3
    ERROR = 2
    FATAL = 1
    generic = generic_settings.GenericSettings()
    generic.get_config()
    logger = logging.getLogger("metadata_utilities")
    logging_log_level = logging.DEBUG
    log_level = DEBUG
    right_now = datetime.now().isoformat(timespec="microseconds")
    # add prefix. Allow for limited numer of functions
    if generic.log_filename_prefix == "{{timestamp}}":
        log_path = generic.log_directory + right_now + "-" + generic.log_filename
    else:
        log_path = generic.log_directory + generic.log_filename
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging_log_level)
    ch = logging.StreamHandler()
    ch.setLevel(logging_log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    def __init__(self):
        self.determine_log_level(self.generic.log_level)
        self.logger.setLevel(self.logging_log_level)

    def determine_log_level(self, configured_log_level):
        if configured_log_level == "VERBOSE":
            self.log_level = self.VERBOSE
            self.logging_log_level = logging.DEBUG
        elif configured_log_level == "DEBUG":
            self.log_level = self.DEBUG
            self.logging_log_level = logging.DEBUG
        elif configured_log_level == "INFO":
            self.log_level = self.INFO
            self.logging_log_level = logging.INFO
        elif configured_log_level == "WARNING":
            self.log_level = self.WARNING
            self.logging_log_level = logging.WARNING
        elif configured_log_level == "ERROR":
            self.log_level = self.ERROR
            self.logging_log_level = logging.ERROR
        elif configured_log_level == "FATAL":
            self.log_level = self.FATAL
            self.logging_log_level = logging.FATAL
        else:
            print(f"invalid log level >{configured_log_level}< in config.json. Defaulting to DEBUG")
            self.log_level = self.DEBUG
            self.logging_log_level = logging.DEBUG

    def log(self, level=DEBUG, msg="no_message", method = "undetermined"):
        if level <= self.log_level:
            message = method + " - " + msg
            if level == self.FATAL:
                self.logger.critical(message)
            elif level == self.ERROR:
                self.logger.error(message)
            elif level == self.WARNING:
                self.logger.warning(message)
            elif level == self.INFO:
                self.logger.info(message)
            elif level == self.DEBUG:
                self.logger.debug(message)
            else:
                self.logger.debug(message)
