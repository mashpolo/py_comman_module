#!/usr/bin/python
#coding=utf-8

import time
import logging
import logging.handlers

log_format = "%(name)s %(levelname)s %(asctime)s (%(filename)s: %(lineno)d) - %(message)s"


class Logger:
    logger_map = {}

    def __init__(self, name=None, filename="", log_format=log_format, maxBytes=4194304, backup_num=128):
        self.name = name
        if not filename:
            filename = "/tmp/%s.log" % time.strftime("%Y_%m_%d_%H_%M_%S")
        self.filename = filename
        if name:
            if name in Logger.logger_map.keys():
                self.logger = Logger.logger_map[name]
            else:
                self.logger = logging.getLogger(name)
                self.logger.setLevel(logging.INFO)
                formatter = logging.Formatter(log_format)
                filehandler = logging.handlers.RotatingFileHandler(self.filename,
                                                                   maxBytes=maxBytes,
                                                                   backupCount=backup_num)
                filehandler.formatter = formatter
                self.logger.addHandler(filehandler)
                Logger.logger_map[name] = self.logger

        self.info = self.logger.info
        self.warn = self.logger.warn
        self.error = self.logger.error
        self.critical = self.logger.critical

    def addConsoleHandler(self):
        consolehandler = logging.StreamHandler()
        formatter = logging.Formatter(log_format)
        consolehandler.formatter = formatter
        self.logger.addHandler(consolehandler)

    def remove(self):
        Logger.logger_map.pop(self.name)

    def modify_rotating(self, maxBytes=None, backupCount=None):
        ro_handler = self.logger.handlers[0]
        if maxBytes:
            ro_handler.maxBytes = maxBytes
        if backupCount:
            ro_handler.backupCount = backupCount