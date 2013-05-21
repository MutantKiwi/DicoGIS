﻿# -*- coding: UTF-8 -*-
#!/usr/bin/env python
from __future__ import unicode_literals
#-------------------------------------------------------------------------------
# Name:         DicoGIS
# Purpose:      Automatize the creation of a dictionnary of geographic data
#                   contained in a folders structures.
#                   It produces an Excel output file (.xls)
#
# Author:       Julien Moura (https://github.com/Guts/)
#
# Created:      14/02/2013
# Updated:      20/05/2013
#
# Licence:      GPL 3
#-------------------------------------------------------------------------------

################################################################################
########### Libraries #############
###################################
# Standard library
from Tkinter import Tk, Label, Entry, Button, StringVar, IntVar     # GUI
from Tkinter import LabelFrame, N, S, E, W, ACTIVE, DISABLED, GROOVE, PhotoImage
from tkFileDialog import askdirectory, asksaveasfilename
from tkMessageBox import showinfo as info
from ttk import Combobox, Progressbar

from sys import exit
from os import  listdir, walk, path       # files and folder managing
from os import environ as env
from time import localtime


# Python 3 backported
from collections import OrderedDict as OD

# 3rd party libraries
from osgeo import ogr    # spatial files
from xlwt import Workbook, Font, XFStyle, easyxf, Formula   # excel library
from lxml import etree as ET

# Custom modules
from modules import InfosOGR

################################################################################
########### Variables #############
###################################

class DicoShapes(Tk):
    def __init__(self):
        u""" Constructeur de la fenêtre principale """
        # basics settings
        Tk.__init__(self)               # constructor of parent graphic class
        self.title(u'DicoGIS')
        self.iconbitmap('DicoGIS.ico')
        self.resizable(width = False, height = False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # variables
        self.li_shp = []         # list for shapefiles path
        self.li_tab = []         # list for MapInfo tables path
        self.today = unicode(localtime()[0]) + u"-" \
                     + unicode(localtime()[1]) + u"-" \
                     + unicode(localtime()[2])    # date of the day
        self.dico_layer = OD()    # dictionary where will be stored informations
        self.dico_fields = OD()    # dictionary for fields information
        self.dico_err = OD()     # errors list
        li_lang = [lg[5:-4] for lg in listdir(r'locale')]        # list of available languages
        self.blabla = OD()      # texts dictionary

        # fillfulling
        self.load_texts()

        # Frames
        self.FrPath = LabelFrame(self, name ='main', text = self.blabla.get('gui_fr1'), padx = 5, pady = 5)
        self.FrProg = LabelFrame(self, name ='progression', text = self.blabla.get('gui_prog'), padx = 5, pady = 5)

            ## Frame 1
        # variables
        self.numfiles = StringVar(self.FrPath, '')
        # target folder
        labtarg = Label(self.FrPath, text = self.blabla.get('gui_path'))
        self.target = Entry(self.FrPath, width = 35)
        browsetarg = Button(self.FrPath, text = self.blabla.get('gui_choix'), command = self.setpathtarg)
        Label(self.FrPath, text = self.blabla.get('gui_fic')).grid(row = 3, column= 1)
        self.output = Entry(self.FrPath, width = 35)
        # language switcher
        self.ddl_lang = Combobox(self.FrPath, values = li_lang, width = 5)

        # widgets placement
        labtarg.grid(row = 1, column = 1, columnspan = 1, sticky = N+S+W+E, padx = 2, pady = 2)
        self.target.grid(row = 1, column = 2, columnspan = 1, sticky = N+S+W+E, padx = 2, pady = 2)
        browsetarg.grid(row = 1, column = 3, columnspan = 1, sticky = N+S+W+E, padx = 2, pady = 2)
        Label(self.FrPath, textvariable = self.numfiles).grid(row = 2, column = 1, columnspan = 3)
        self.ddl_lang.grid(row=1, column = 4, sticky = N+S+W+E, padx = 2, pady = 2)
        self.output.grid(row = 3, column= 2)


            ## Main frame
        # Hola
        Label(self, text = self.blabla.get('hi') + env.get(u'USERNAME')).grid(row = 1, column = 1,
                                                 columnspan = 1, sticky = N+S+W+E,
                                                 padx = 2, pady = 5)
        # Imagen
        self.icone = PhotoImage(file = r'img/DicoGIS_logo.GIF')
        Label(self, borderwidth = 2, relief = 'ridge',
                                     image = self.icone).grid(row = 1,
                                                              rowspan = 4,
                                                              column = 0,
                                                              padx = 1,
                                                              pady = 1,
                                                              sticky = W)

        # Basic buttons
        self.val = Button(self, text = self.blabla.get('gui_go'),
                                relief= 'raised',
                                state = DISABLED,
                                command = self.process)
        can = Button(self, text = self.blabla.get('gui_quit'),
                                relief= 'groove',
                                command = self.destroy)

        # widgets placement
        self.val.grid(row = 5, column = 1, columnspan = 2,
                            sticky = N+S+W+E, padx = 2, pady = 5)
        can.grid(row = 5, column = 0, sticky = N+S+W+E, padx = 2, pady = 5)
        # Frames placement
        self.FrPath.grid(row = 2, column = 1, sticky = N+S+W+E, padx = 2, pady = 2)


    def load_texts(self, lang='FR'):
        u""" Load texts according to the selected language """
        # open xml cursor
        xml = ET.parse('locale/lang_' + lang + '.xml')
        # Looping and gathering texts from the xml file
        for elem in xml.getroot().getiterator():
            self.blabla[elem.tag] = elem.text
        # Fin de fonction
        return self.blabla


    def setpathtarg(self):
        """ ...browse and insert the path of target folder """
        foldername = askdirectory(parent = self,
                                  title = self.blabla.get('gui_cible'))
        # check if a folder has been choosen
        if foldername:
            try:
                self.target.insert(0, foldername)
            except:
                print self.blabla.get('nofolder')
                return
        # set the default output file
        self.output.insert(0, "DicoShapes_" + path.split(self.target.get())[1]
                            + "_" + self.today + ".xls"  )
        # calculate number of shapefiles and MapInfo files
        self.ligeofiles(foldername)
        self.numfiles.set(unicode(len(self.li_shp)) + u' shapefiles - '
                        + unicode(len(self.li_tab)) + u' tables (MapInfo)')
        self.val.config(state = ACTIVE)
        # end of function
        return foldername


    def ligeofiles(self, foldertarget):
        u""" List shapefiles and MapInfo files (.tab, not .mid/mif) contained
        in the folders structure """
        # Looping in folders structure
        for root, dirs, files in walk(foldertarget):
            for i in files:
                # Looping on files contained
                if path.splitext(path.join(root, i))[1] == u'.shp' and \
                   path.isfile(path.join(root, i)[:-4] + u'.dbf') and \
                   path.isfile(path.join(root, i)[:-4] + u'.shx') and \
                   path.isfile(path.join(root, i)[:-4] + u'.prj'):
                    # add complete path of shapefile
                    self.li_shp.append(path.join(root, i))
                elif path.splitext(path.join(root, i))[1] == u'.tab' and \
                   path.isfile(path.join(root, i)[:-4] + u'.dat') and \
                   path.isfile(path.join(root, i)[:-4] + u'.map') and \
                   path.isfile(path.join(root, i)[:-4] + u'.id'):
                    # add complete path of MapInfo file
                    self.li_tab.append(path.join(root, i))
        # Lists ordering and tupling
        self.li_shp.sort()
        self.li_shp = tuple(self.li_shp)
        self.li_tab.sort()
        self.li_tab = tuple(self.li_tab)
        # End of function
        return foldertarget, self.li_shp, self.li_tab


    def process(self):
        u""" launch the different processes """
        # check if there are some layers into the folder structure
        if len(self.li_shp) + len(self.li_tab) == 0:
            erreurStop(self.blabla.get('nodata'))
            return
        # creating the Excel workbook
        self.configexcel()
        # getting the info from shapefiles and compile it in the excel
        line = 1    # line of dictionary
        for shp in self.li_shp:
            """ looping on shapefiles list """
            # reset recipient data
            self.dico_layer.clear()
            self.dico_fields.clear()
            # getting the informations
            InfosOGR(shp, self.dico_layer, self.dico_fields, 'shape')
            # writing to the Excel dictionary
            self.dictionarize(self.dico_layer, self.dico_fields, self.feuy1, line)
            # increment the line number
            line = line +1
        # getting the info from mapinfo tables and compile it in the excel
        for tab in self.li_tab:
            """ looping on MapInfo tables list """
            # reset recipient data
            self.dico_layer.clear()
            self.dico_fields.clear()
            # getting the informations
            InfosOGR(tab, self.dico_layer, self.dico_fields, 'table')
            # writing to the Excel dictionary
            self.dictionarize(self.dico_layer, self.dico_fields, self.feuy1, line)
            # increment the line number
            line = line +1
        # saving dictionary
        self.savedico()
        # End of function
        return


    def configexcel(self):
        u""" create and configure the Excel workbook """
        # Basic configurationdu
        self.book = Workbook(encoding = 'utf8')
        self.feuy1 = self.book.add_sheet(u'Shapes', cell_overwrite_ok=True)

        # Some customization: fonts and styles
        # first line style
        self.entete = XFStyle()
        font1 = Font()
        font1.name = 'Times New Roman'
        font1.bold = True
        self.entete.font = font1

        # hyperlinks style
        self.url = easyxf(u'font: underline single')
        # errors style
        self.erreur = easyxf(u'font: name Arial, bold 1, colour red')

        # columns name
        self.feuy1.write(0, 0, self.blabla.get('nomfic'), self.entete)
        self.feuy1.write(0, 1, self.blabla.get('path'), self.entete)
        self.feuy1.write(0, 2, self.blabla.get('theme'), self.entete)
        self.feuy1.write(0, 3, self.blabla.get('geometrie'), self.entete)
        self.feuy1.write(0, 4, self.blabla.get('emprise'), self.entete)
        self.feuy1.write(0, 5, self.blabla.get('srs'), self.entete)
        self.feuy1.write(0, 6, self.blabla.get('codepsg'), self.entete)
        self.feuy1.write(0, 7, self.blabla.get('num_attr'), self.entete)
        self.feuy1.write(0, 8, self.blabla.get('num_objets'), self.entete)
        self.feuy1.write(0, 9, self.blabla.get('date_crea'), self.entete)
        self.feuy1.write(0, 10, self.blabla.get('date_actu'), self.entete)
        self.feuy1.write(0, 11, self.blabla.get('li_chps'), self.entete)
        self.feuy1.write(0, 12, self.blabla.get('format'), self.entete)
        # end of function
        return self.book, self.feuy1, self.entete, self.url, self.erreur

    def dictionarize(self, layer_infos, fields_info, sheet, line):
        u""" write the infos of the layer into the Excel workbook """
        # local variables
        champs = ""
        theme = ""
        # Name
        sheet.write(line, 0, layer_infos.get('name'))
        # Path of containing folder formatted to be a hyperlink
        link = 'HYPERLINK("' + layer_infos.get(u'folder') \
                             + '"; "' + self.blabla.get('browse') + '")'
        sheet.write(line, 1, Formula(link), self.url)
        # Name of containing folder
        # with a specific exception to adapt to PACIVUR database
        if path.basename(layer_infos.get(u'folder')) != 'shp':
            sheet.write(line, 2, path.basename(layer_infos.get(u'folder')))
        else:
            sheet.write(line, 2, path.basename(path.dirname(layer_infos.get(u'folder'))))

        # Geometry type
        sheet.write(line, 3, layer_infos.get(u'type_geom'))
        # Spatial extent
        emprise = u"Xmin : " + unicode(layer_infos.get(u'Xmin')) +\
                  u", Xmax : " + unicode(layer_infos.get(u'Xmax')) +\
                  u", Ymin : " + unicode(layer_infos.get(u'Ymin')) +\
                  u", Ymax : " + unicode(layer_infos.get(u'Ymax'))
        sheet.write(line, 4, emprise)
        # Name of srs
        sheet.write(line, 5, layer_infos.get(u'srs'))
        # EPSG code
        sheet.write(line, 6, layer_infos.get(u'EPSG'))
        # Number of fields
        sheet.write(line, 7, layer_infos.get(u'num_fields'))
        # Name of objects
        sheet.write(line, 8, layer_infos.get(u'num_obj'))
        # Creation date
        sheet.write(line, 9, layer_infos.get(u'date_crea'))
        # Last update date
        sheet.write(line, 10, layer_infos.get(u'date_actu'))
        # Format of data
        sheet.write(line, 10, layer_infos.get('type'))
        # Field informations
        for chp in fields_info.keys():
            # field type
            if fields_info[chp][0] == 'Integer' or fields_info[chp][0] == 'Real':
                tipo = u'Numérique'
            elif fields_info[chp][0] == 'String':
                tipo = u'Texte'
            elif fields_info[chp][0] == 'Date':
                tipo = u'Date'
            try:
                # concatenation of field informations
                champs = champs +\
                         chp +\
                         " (" + tipo +\
                         ", Lg. = " + unicode(fields_info[chp][1]) +\
                         ", Pr. = " + unicode(fields_info[chp][2]) + ") ; "
            except UnicodeDecodeError:
                # write a notification into the log file
                dico_err[couche] = self.blabla.get('err_encod') + \
                                   chp.decode('latin1') + \
                                   "\n\n"
                # décode le nom du champ litigieux
                champs = champs +\
                         chp.decode('utf8') +\
                         " (" + tipo +\
                         ", Lg. = " + unicode(fields_info[chp][1]) +\
                         ", Pr. = " + unicode(fields_info[chp][2]) + ") ; "

                continue

        # Once all fieds explored, write them
        sheet.write(line, 11, champs)

        # End of function
        return self.book, self.feuy1

    def savedico(self):
        u""" Save the Excel file """
        # Prompt of folder where save the file
        saved = asksaveasfilename(initialdir= self.target.get(),
                        defaultextension = '.xls',
                        initialfile = self.output.get(),
                        filetypes = [(self.blabla.get('gui_excel'),"*.xls")])
        # check if the extension is correctly indicated
        if path.splitext(saved)[1] != ".xls":
            saved = saved + ".xls"
        # save
        self.book.save(saved)


    def erreurStop(self, mess):
        u""" In case of error, close the GUI and stop the program """
        info(title = u'Erreur', message = mess)
        self.root.destroy()
        exit()

################################################################################
###### Stand alone program ########
###################################

if __name__ == '__main__':
    app = DicoShapes()
    app.mainloop()


################################################################################
######## Former codelines #########
###################################