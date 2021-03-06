# -*- coding: UTF-8 -*-
#!/usr/bin/env python
from __future__ import absolute_import, print_function, unicode_literals

# ----------------------------------------------------------------------------
# Name:         Infos Geospatial PDF
# Purpose:      Use GDAL/OGR library to extract informations about
#                   geographic data. It permits a more friendly use as
#                   submodule.
#
# Author:       Julien Moura (https://github.com/Guts/)
#
# Python:       2.7.x
# Created:      18/02/2014
# Updated:      08/04/2016
# Licence:      GPL 3
# ----------------------------------------------------------------------------

# ############################################################################
# ########## Libraries #############
# ##################################

# Standard library
from collections import OrderedDict  # Python 3 backported
from os import chdir, listdir, path  # files and folder managing
from time import localtime, strftime

# 3rd party libraries
try:
    from osgeo import gdal
    from osgeo import ogr
    from osgeo import osr
    from osgeo.gdalconst import *
except ImportError:
    import gdal
    import ogr
    import osr
    from gdalconst import *

# ############################################################
# ########### Classes ##############
# ##################################


class GdalErrorHandler(object):
    def __init__(self):
        """ Callable error handler
        see: http://trac.osgeo.org/gdal/wiki/PythonGotchas#Exceptionsraisedincustomerrorhandlersdonotgetcaught
        and http://pcjericks.github.io/py-gdalogr-cookbook/gdal_general.html#install-gdal-ogr-error-handler
        """
        self.err_level = gdal.CE_None
        self.err_type = 0
        self.err_msg = ""

    def handler(self, err_level, err_type, err_msg):
        """ Making errors messages more readable """
        # available types
        err_class = {
            gdal.CE_None: "None",
            gdal.CE_Debug: "Debug",
            gdal.CE_Warning: "Warning",
            gdal.CE_Failure: "Failure",
            gdal.CE_Fatal: "Fatal",
        }
        # getting type
        err_type = err_class.get(err_type, "None")

        # cleaning message
        err_msg = err_msg.replace("\n", " ")

        # disabling GDAL exceptions raising to avoid future troubles
        gdal.DontUseExceptions()

        # propagating
        self.err_level = err_level
        self.err_type = err_type
        self.err_msg = err_msg

        # end of function
        return self.err_level, self.err_type, self.err_msg


class OGRErrorHandler(object):
    def __init__(self):
        """Callable error handler.

        see: http://trac.osgeo.org/gdal/wiki/PythonGotchas#Exceptionsraisedincustomerrorhandlersdonotgetcaught
        and http://pcjericks.github.io/py-gdalogr-cookbook/gdal_general.html#install-gdal-ogr-error-handler
        """
        self.err_level = gdal.CE_None
        self.err_type = 0
        self.err_msg = ""

    def handler(self, err_level, err_type, err_msg):
        """Makes errors messages more readable."""
        # available types
        err_class = {
            gdal.CE_None: "None",
            gdal.CE_Debug: "Debug",
            gdal.CE_Warning: "Warning",
            gdal.CE_Failure: "Failure",
            gdal.CE_Fatal: "Fatal",
        }
        # getting type
        err_type = err_class.get(err_type, "None")

        # cleaning message
        err_msg = err_msg.replace("\n", " ")

        # disabling OGR exceptions raising to avoid future troubles
        ogr.DontUseExceptions()

        # propagating
        self.err_level = err_level
        self.err_type = err_type
        self.err_msg = err_msg

        # end of function
        return self.err_level, self.err_type, self.err_msg


class ReadGeoPDF(object):
    def __init__(self, pdfpath, dico_geopdf, tipo="pdf", txt=""):
        """ Uses GDAL & OGR functions to extract basic
        informations about geographic PDF file and store into dictionaries.

        layerpath = path to the geographic file
        dico_geopdf = dictionary for global informations
        dico_bands = dictionary for the bands informations
        txt = dictionary of txt in the selected language
        """
        # gdal specific
        gdal.AllRegister()
        # changing working directory to layer folder
        chdir(path.dirname(pdfpath))
        pdfpath = path.abspath(pdfpath)

        # handling specific exceptions
        gdalerr = GdalErrorHandler()
        errhandler = gdalerr.handler
        gdal.PushErrorHandler(errhandler)
        self.alert = 0
        # gdal.SetConfigOption(str("GTIFF_IGNORE_READ_ERRORS"), str("TRUE"))
        gdal.UseExceptions()

        # opening file
        try:
            self.geopdf = gdal.Open(pdfpath, GA_ReadOnly)
        except Exception as e:
            self.alert += 1
            self.erratum(dico_geopdf, pdfpath, "err_incomp")
            return

        # check if PDF is GDAL friendly
        if self.geopdf is None:
            self.alert += 1
            self.erratum(dico_geopdf, pdfpath, "err_incomp")
            return
        else:
            pass
        # basic informations
        dico_geopdf["format"] = tipo
        self.raster_basics(pdfpath, dico_geopdf, txt)
        # geometry information
        self.infos_geom(dico_geopdf, txt)
        # bands information
        for band_idx in range(1, self.geopdf.RasterCount):
            # new dict to store band informations
            dico_band = OrderedDict()
            # getting band infos
            self.infos_bands(band_idx, dico_band)
            # storing band into the PDF dictionary
            dico_geopdf["band_{0}".format(band_idx)] = dico_band
            # deleting dict object
            del dico_band

        # safe close (see: http://pcjericks.github.io/py-gdalogr-cookbook/)
        del self.geopdf
        # warnings messages
        dico_geopdf["err_gdal"] = gdalerr.err_type, gdalerr.err_msg

        # ##### READING INTO VECTORS LAYERS
        ogr.UseExceptions()
        try:
            geopdf_v = ogr.Open(pdfpath)
        except Exception:
            self.erratum(dico_geopdf, pdfpath, "err_corrupt")
            self.alert = self.alert + 1
            return None

        # layers count and names
        dico_geopdf["layers_count"] = geopdf_v.GetLayerCount()
        li_layers_names = []
        li_layers_idx = []
        dico_geopdf["layers_names"] = li_layers_names
        dico_geopdf["layers_idx"] = li_layers_idx

        # total fields count
        total_fields = 0
        dico_geopdf["total_fields"] = total_fields
        # total objects count
        total_objs = 0
        dico_geopdf["total_objs"] = total_objs
        # parsing layers
        for layer_idx in range(geopdf_v.GetLayerCount()):
            # dictionary where will be stored informations
            dico_layer = OrderedDict()
            # parent GDB
            dico_layer["parent_name"] = path.basename(geopdf_v.GetName())
            # getting layer object
            layer = geopdf_v.GetLayerByIndex(layer_idx)
            # layer name
            li_layers_names.append(layer.GetName())
            # layer index
            li_layers_idx.append(layer_idx)
            # getting layer globlal informations
            self.vector_basics(layer, dico_layer, txt)
            # storing layer into the GeoPDF dictionary
            dico_geopdf[
                "{0}_{1}".format(layer_idx, dico_layer.get("title"))
            ] = dico_layer
            # summing fields number
            total_fields += dico_layer.get("num_fields")
            # summing objects number
            total_objs += dico_layer.get("num_obj")
            # deleting dictionary to ensure having cleared space
            del dico_layer
        # storing fileds and objects sum
        dico_geopdf["total_fields"] = total_fields
        dico_geopdf["total_objs"] = total_objs

    def raster_basics(self, pdfpath, dico_geopdf, txt):
        """ get the global informations about the PDF """
        # files and folder
        dico_geopdf["name"] = path.basename(pdfpath)
        dico_geopdf["folder"] = path.dirname(pdfpath)
        dico_geopdf["title"] = dico_geopdf["name"][:-4].replace("_", " ").capitalize()

        # dependencies
        dependencies = [
            path.basename(filedepend)
            for filedepend in self.geopdf.GetFileList()
            if filedepend != pdfpath
        ]
        dico_geopdf["dependencies"] = dependencies

        # total size
        dependencies.append(pdfpath)
        total_size = sum([path.getsize(f) for f in dependencies])
        dico_geopdf["total_size"] = self.sizeof(total_size)
        dependencies.pop(-1)

        # metadata
        geopdf_MD = self.geopdf.GetMetadata()
        dico_geopdf["title"] = geopdf_MD.get("TITLE")
        dico_geopdf["creator_prod"] = "{0} - {1}".format(
            geopdf_MD.get("CREATOR"), geopdf_MD.get("PRODUCER")
        )
        dico_geopdf["keywords"] = geopdf_MD.get("KEYWORDS")
        dico_geopdf["dpi"] = geopdf_MD.get("DPI")
        dico_geopdf["subject"] = geopdf_MD.get("SUBJECT")
        dico_geopdf["neatline"] = geopdf_MD.get("NEATLINE")
        dico_geopdf["description"] = self.geopdf.GetDescription()

        # creation date
        creadate = geopdf_MD.get("CREATION_DATE")
        dico_geopdf["date_crea"] = "{0}/{1}/{2}".format(
            creadate[8:10], creadate[6:8], creadate[2:6]
        )

        # image specifications
        dico_geopdf["num_cols"] = self.geopdf.RasterXSize
        dico_geopdf["num_rows"] = self.geopdf.RasterYSize
        dico_geopdf["num_bands"] = self.geopdf.RasterCount

        # data type
        dico_geopdf["data_type"] = gdal.GetDataTypeName(
            self.geopdf.GetRasterBand(1).DataType
        )

        # subdatasets count
        dico_geopdf["subdatasets_count"] = len(self.geopdf.GetSubDatasets())

        # GCPs
        dico_geopdf["gcp_count"] = self.geopdf.GetGCPCount()

        # basic dates
        dico_geopdf["date_actu"] = strftime(
            "%d/%m/%Y", localtime(path.getmtime(pdfpath))
        )

        # end of function
        return dico_geopdf

    def vector_basics(self, layer_obj, dico_layer, txt):
        """ get the global informations about the layer """
        # title
        try:
            dico_layer["title"] = unicode(layer_obj.GetName())
        except UnicodeDecodeError:
            # just if you use chardet from Mozilla
            # encDet = chardet.detect(layer_obj.GetName()).get('encoding')
            # dico_layer[u'encoding_detected'] = encDet
            layer_name = layer_obj.GetName().decode("latin1", errors="ignore")
            dico_layer["title"] = layer_name

        # features count
        dico_layer["num_obj"] = layer_obj.GetFeatureCount()

        # getting geography and geometry informations
        # srs = layer_obj.GetSpatialRef()
        # self.infos_geos(layer_obj, srs, dico_layer, txt)

        # getting fields informations
        dico_fields = OrderedDict()
        layer_def = layer_obj.GetLayerDefn()
        dico_layer["num_fields"] = layer_def.GetFieldCount()
        self.infos_fields(layer_def, dico_fields)
        dico_layer["fields"] = dico_fields

        # end of function
        return dico_layer

    def infos_geom(self, dico_geopdf, txt):
        """ get the informations about geometry """
        # Spatial extent (bounding box)
        geotransform = self.geopdf.GetGeoTransform()
        dico_geopdf["xOrigin"] = geotransform[0]
        dico_geopdf["yOrigin"] = geotransform[3]
        dico_geopdf["pixelWidth"] = round(geotransform[1], 3)
        dico_geopdf["pixelHeight"] = round(geotransform[5], 3)
        dico_geopdf["orientation"] = geotransform[2]

        # # SRS
        # using osr to get the srs
        srs = osr.SpatialReference(self.geopdf.GetProjection())
        # srs.ImportFromWkt(self.geopdf.GetProjection())
        srs.AutoIdentifyEPSG()

        # srs types
        srsmetod = [
            (srs.IsCompound(), txt.get("srs_comp")),
            (srs.IsGeocentric(), txt.get("srs_geoc")),
            (srs.IsGeographic(), txt.get("srs_geog")),
            (srs.IsLocal(), txt.get("srs_loca")),
            (srs.IsProjected(), txt.get("srs_proj")),
            (srs.IsVertical(), txt.get("srs_vert")),
        ]
        # searching for a match with one of srs types
        for srsmet in srsmetod:
            if srsmet[0] == 1:
                typsrs = srsmet[1]
            else:
                continue
        # in case of not match
        try:
            dico_geopdf["srs_type"] = unicode(typsrs)
        except UnboundLocalError:
            typsrs = txt.get("srs_nr")
            dico_geopdf["srs_type"] = unicode(typsrs)

        # Handling exception in srs names'encoding
        if srs.IsProjected():
            try:
                if srs.GetAttrValue(str("PROJCS")) is not None:
                    dico_geopdf["srs"] = unicode(
                        srs.GetAttrValue(str("PROJCS"))
                    ).replace("_", " ")
                else:
                    dico_geopdf["srs"] = unicode(
                        srs.GetAttrValue(str("PROJECTION"))
                    ).replace("_", " ")
            except UnicodeDecodeError:
                if srs.GetAttrValue(str("PROJCS")) != str("unnamed"):
                    dico_geopdf["srs"] = (
                        srs.GetAttrValue(str("PROJCS"))
                        .decode("latin1")
                        .replace("_", " ")
                    )
                else:
                    dico_geopdf["srs"] = (
                        srs.GetAttrValue(str("PROJECTION"))
                        .decode("latin1")
                        .replace("_", " ")
                    )
        else:
            try:
                if srs.GetAttrValue(str("GEOGCS")) is not None:
                    dico_geopdf["srs"] = unicode(
                        srs.GetAttrValue(str("GEOGCS"))
                    ).replace("_", " ")
                else:
                    dico_geopdf["srs"] = unicode(
                        srs.GetAttrValue(str("PROJECTION"))
                    ).replace("_", " ")
            except UnicodeDecodeError:
                if srs.GetAttrValue(str("GEOGCS")) != str("unnamed"):
                    dico_geopdf["srs"] = (
                        srs.GetAttrValue(str("GEOGCS"))
                        .decode("latin1")
                        .replace("_", " ")
                    )
                else:
                    dico_geopdf["srs"] = (
                        srs.GetAttrValue(str("PROJECTION"))
                        .decode("latin1")
                        .replace("_", " ")
                    )

        dico_geopdf["EPSG"] = unicode(srs.GetAttrValue(str("AUTHORITY"), 1))

        # end of function
        return dico_geopdf

    def infos_bands(self, band, dico_bands):
        """ get the informations about fields definitions """
        # getting band object
        band_info = self.geopdf.GetRasterBand(band)

        # band statistics
        try:
            stats = band_info.GetStatistics(True, True)
        except:
            return
        if stats:
            # band minimum value
            if band_info.GetMinimum() is None:
                dico_bands["band{}_Min".format(band)] = stats[0]
            else:
                dico_bands["band{}_Min".format(band)] = band_info.GetMinimum()

            # band maximum value
            if band_info.GetMinimum() is None:
                dico_bands["band{}_Max".format(band)] = stats[1]
            else:
                dico_bands["band{}_Max".format(band)] = band_info.GetMaximum()

            # band mean value
            dico_bands["band{}_Mean".format(band)] = round(stats[2], 2)

            # band standard deviation value
            dico_bands["band{}_Sdev".format(band)] = round(stats[3], 2)
        else:
            pass

        # band no data value
        dico_bands["band{}_NoData".format(band)] = band_info.GetNoDataValue()

        # band scale value
        dico_bands["band{}_Scale".format(band)] = band_info.GetScale()

        # band unit type value
        dico_bands["band{}_UnitType".format(band)] = band_info.GetUnitType()

        # color table
        coul_table = band_info.GetColorTable()
        if coul_table is None:
            dico_bands["band{}_CTabCount".format(band)] = 0
        else:
            dico_bands["band{}_CTabCount".format(band)] = coul_table.GetCount()
            #### COMENTED BECAUSE IT'S TOO MUCH INFORMATIONS
            # for ctab_idx in range(0, coul_table.GetCount()):
            #     entry = coul_table.GetColorEntry(ctab_idx)
            #     if not entry:
            #         continue
            #     else:
            #         pass
            #     dico_bands["band{0}_CTab{1}_RGB".format(band, ctab_idx)] = \
            #                   coul_table.GetColorEntryAsRGB(ctab_idx, entry)

        # safe close (quite useless but good practice to have)
        del stats
        del band_info

        # end of function
        return dico_bands

    def infos_fields(self, layer_def, dico_fields):
        """ get the informations about fields definitions """
        for i in range(layer_def.GetFieldCount()):
            champomy = layer_def.GetFieldDefn(i)  # fields ordered
            dico_fields[champomy.GetName()] = champomy.GetTypeName()

        # end of function
        return dico_fields

    def sizeof(self, os_size):
        """ return size in different units depending on size
        see http://stackoverflow.com/a/1094933 """
        for size_cat in ["octets", "Ko", "Mo", "Go"]:
            if os_size < 1024.0:
                return "%3.1f %s" % (os_size, size_cat)
            os_size /= 1024.0
        return "%3.1f %s" % (os_size, " To")

    def erratum(self, dico_geopdf, pdfpath, mess):
        """ errors handling """
        # storing minimal informations to give clues to solve later
        dico_geopdf["name"] = path.basename(pdfpath)
        dico_geopdf["folder"] = path.dirname(pdfpath)
        dico_geopdf["error"] = mess
        # End of function
        return dico_geopdf


# #############################################################################
# ##### Stand alone program ########
# ##################################

if __name__ == "__main__":
    """ standalone execution for tests. Paths are relative considering a test
    within the official repository (https://github.com/Guts/GIS)"""
    # sample files
    dir_pdf = path.abspath(r"..\..\test\datatest\maps_docs\pdf")
    chdir(path.abspath(dir_pdf))
    li_pdf = listdir(path.abspath(dir_pdf))
    li_pdf = [
        path.abspath(pdf) for pdf in li_pdf if path.splitext(pdf)[1].lower() == ".pdf"
    ]

    # test txt dictionary
    textos = OrderedDict()
    textos["srs_comp"] = "Compound"
    textos["srs_geoc"] = "Geocentric"
    textos["srs_geog"] = "Geographic"
    textos["srs_loca"] = "Local"
    textos["srs_proj"] = "Projected"
    textos["srs_vert"] = "Vertical"
    textos["geom_point"] = "Point"
    textos["geom_ligne"] = "Line"
    textos["geom_polyg"] = "Polygon"
    # recipient datas
    dico_pdf = OrderedDict()  # dictionary where will be stored informations
    # execution
    for pdf in li_pdf:
        """ looping on pdf files """
        # reset recipient data
        dico_pdf.clear()
        # get the absolute path
        pdf = path.abspath(pdf)
        # getting the informations
        if not path.isfile(pdf):
            print("\n\t==> File doesn't exist: " + pdf)
            continue
        print("\n======================\n\t", path.basename(pdf))
        info_pdf = ReadGeoPDF(pdf, dico_pdf, path.splitext(pdf)[1], textos)
        print("\n", dico_pdf)
