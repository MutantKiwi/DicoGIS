# -*- coding: UTF-8 -*-
#!/usr/bin/env python
from __future__ import (absolute_import, print_function, unicode_literals)
# ------------------------------------------------------------------------------
# Name:         Isogeo to Microsoft Excel 2010
# Purpose:      Get metadatas from an Isogeo share and store it into
#               a Excel worksheet. It's one of the submodules of
#               isogeo2office (https://bitbucket.org/isogeo/isogeo-2-office).
#
# Author:       Julien Moura (@geojulien)
#
# Python:       2.7.x
# Created:      14/08/2014
# Updated:      15/04/2016
# ------------------------------------------------------------------------------

# ##############################################################################
# ########## Libraries #############
# ##################################

# Python 2 and 3 compatibility
from future.standard_library import install_aliases
install_aliases()

# Standard library
import logging
from os import listdir, path, walk

# ##############################################################################
# ########## Classes ###############
# ##################################


class Utils(object):
    """TO DOC"""
    def __init__(self, ds_type="flat"):
        """Instanciate Utils class."""
        self.ds_type = ds_type
        super(Utils, self).__init__()

    def list_dependencies(self, main_file_path, exclude=""):
        """List dependant files around a main file."""
        if exclude == "auto":
            exclude = path.splitext(path.abspath(main_file_path).lower())[1]
        else:
            pass
        # dependencies
        dependencies = [f for f in listdir(path.dirname(main_file_path))
                        if path.splitext(path.abspath(f))[0] == path.splitext(main_file_path)[0]
                        and not path.splitext(path.abspath(f).lower())[1] == exclude]

        return dependencies

    def sizeof(self, source_path, dependencies=[]):
        """Calculate size in different units depending on size.

        see: http://stackoverflow.com/a/1094933
        """
        if path.isfile(source_path):
            dependencies.append(source_path)
            total_size = sum([path.getsize(f) for f in dependencies])
            dependencies.pop(-1)
        elif path.isdir(source_path):
            # sum files size
            total_size = 0
            for chemins in walk(path.realpath(source_path)):
                for file in chemins[2]:
                    chem_complete = path.join(chemins[0], file)
                    if path.isfile(chem_complete):
                        total_size = total_size + path.getsize(chem_complete)
                    else:
                        pass
        else:
            return None

        # prettify units
        for size_cat in ('octets', 'Ko', 'Mo', 'Go'):
            if total_size < 1024.0:
                return "%3.1f %s" % (total_size, size_cat)
            total_size /= 1024.0

        return "%3.1f %s" % (total_size, " To")

    def erratum(self, ctner=dict(), src="", ds_lyr=None, mess_type=1, mess=""):
        """Handle errors message and store it into __dict__."""
        if self.ds_type == "flat":
            # local variables
            ctner['name'] = path.basename(src)
            ctner['folder'] = path.dirname(src)
            ctner['error'] = mess
            # method end
            return ctner
        elif self.ds_type == "postgis":
            ctner['name'] = mess_type
            ctner['error'] = mess
            # method end
            return ctner
        else:
            pass