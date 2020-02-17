# -*- coding: utf-8 -*-
"""
Created on Wed Dec  4 17:42:05 2019

Item library

v1
    eraseItems - permite borrar toda una jerarquía de hijos y sus atributos
    copyAttsExtended - crea un formato RAW de instancia Item para poder ser grabados como DF (es una especie de Matriz)

@author: Fernando
"""


# -*- coding: utf-8 -*-
# File: GA BUDGET.py
#    GA to provide budget solutions based on constrains
#
# Author: Fernando Garcia Varela <fernando.garcia.varela@seachad.com>
# Copyright (c) 2019 Fernando Garcia Varela
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

import unittest
import datetime
# import genetic_fitness_annealing as genetic
import random
import sys
import pandas as pd
import matplotlib.pyplot as plt
import statistics
import os
from datetime import datetime
import re # para las expresiones regulares

_debug = True # esto quita o saca mensajes por consola

_start = datetime.now()

#==============================================================================
# ---- CONFIGURACION
#==============================================================================

# =============================================================================
# ---- DATABASEINFO.XLSX
# =============================================================================
# esta hoja excel ha de existir con este nombre
DFN_TYPEITEM = "TypeItem" # contiene info sobre el tipo de item. Realmente no se usa
DFN_ITEMNAME = "ItemName" # Es el nombre interno de la dataset, para que luego se pueda usar en el fichero struct
DFN_VALUE = "Value" # es el nombre real del dataset tal y como aparece en el sistema (no se le engancha el directorio raiz...)
DFN_NOTES = "Notes" # Cualquier documentación que se quiera poner

DFN_STRUCT = "_STRUCT" # apunta al dataset struct para definir todas las estructuras de información
DFN_EXECUTE = "_EXECUTE" # apunta al dataset que especifica acciones a tomar con toda la información ya leída (OJO, todo lo que se ponga aquí tiene que estar acorde con _STRUCT)

# =============================================================================
# ---- STRUCT.XLSX
# =============================================================================
# esta hoja excel ha de existir con este nombre
STR_ITEMNAME = "Item" # nombre interno del item que contendrá la información
STR_DATASET = "Dataset" # nombre interno de la dataset a usar (es la clave de entrada en el fichero )
STR_ATTR_NAME = "AttrName" # nombre del atributo y configuración de si es valor o está mapeado a una columna del dataset
STR_ATTR_DATASETCOLUMN = "AttrDatasetColumn" # columna del dataset que contiene info a cargar
STR_ATTR_VALUE = "AttrValue" # valor del atributo
STR_PARENT = "Parent" # item parent al que se cuelga el item que se está definiendo (tiene que haber sido definido antes)
STR_ATTS = "Attr" # cadena con nombres de atributos separados por "|" (han de haber sido definidos antes). Si le queremos poner un valor al atributo diferente del valor estandar, se lo pondremos con un ":" - ejemplo: _sold_FY|mp|Mp|mv|Mv|goal_P|goal_V:116000000|strategy
STR_EXPR = "Expression" # cadena con nombres de atributos separados por "|" (han de haber sido definidos antes). Si le queremos poner un valor al atributo diferente del valor estandar, se lo pondremos con un ":" - ejemplo: _sold_FY|mp|Mp|mv|Mv|goal_P|goal_V:116000000|strategy
STR_REST = "Restriction" # cadena con nombres de atributos separados por "|" (han de haber sido definidos antes). Si le queremos poner un valor al atributo diferente del valor estandar, se lo pondremos con un ":" - ejemplo: _sold_FY|mp|Mp|mv|Mv|goal_P|goal_V:116000000|strategy
STR_NOTES = "NOTES" # documentación que se quiera poner

# vocabulario en STRUCT
STR_ATTR = "_attr" # es un atributo
STR_ALIAS = "_alias" # notifica en qué columna del dataset se busca el item, un item puede tener varios alias (uno por cada dataset en que pueda ser buscado) - ejemplo Cuenta puede ser Account Name en Capgemini y puede ser Acc Name en CuentasInfo
STR_DBATTR = "_database_attr" # el atributo se corresponde con una columna del dataset
STR_DBLOAD = "_database_load" # carga los elementos del dataset
STR_DBUNIQUE = "_database_unique" # carga los elementos pero discriminando cuando cada registro que se le pasa es unique en el dataset (para coger el conjunto de filas que se corresponden con el valor)
STR_EXP = "_exp" # es una expresion
STR_REST = "_restriction" # es una restriccion
STR_ITEM = "_item" # es un item
STR_IMPORT = "_import" # quiere importar una librería
STR_PROPAGATE = "_propagate" # quiero propagar atributos de una entidad a toda su jerarquía

# =============================================================================
# ---- VOCABULARY
# =============================================================================
# ---- en construcción
STR_ROOT = "_ROOT" # raiz de todos los items
STR_ACTION = "_action"
STR_RESPONSE = "_response"
STR_RESTRICTION = "_restriction"

# =============================================================================
# ---- ROOT
# =============================================================================
ROOT = "ROOT" # obligatoriamente se denomina así al elemento raiz, para poder ejecutar toda la jerarquía

#==============================================================================
# END CONFIGURACION
#==============================================================================

# ---- fGEN
#==============================================================================
# class Item
#
# name = name of item
# soldFY_ = total sold last year (basis for the budget)
# m = lower limit fork
# M = upper limit fork
# goal_P = goal in growth percentage
# goal_V = quantity goal
# items = dict of items (nested) for budget guideline definition
# strategy = resolution strategy based on last year data if appropiate ("N", "R", "D") -> "N" normal (guideline applied), "R" rest (rest applied), "D" default (default strategy applied)
#==============================================================================

import uuid

allItemsByUUID = {} # todos los items
allItemsByName = {} # todos los items

# =============================================================================
# Devuelve un item por su nombre
# =============================================================================
def _h_getItemByName( name ):
    """
    Devuelve un item por su nombre si lo encuenta, en otro caso error

    Parameters
    ----------
    name : TYPE string
        DESCRIPTION.
        Nombre del item que se pretende recuperar
    Returns
    -------
    Item si todo OK.
    False si ha habido un error

    """
    try:
        return(allItemsByName[name])
    except:

        cadena = "\nERROR: El item {} no existe".format(
            name
            )
        _Debug(cadena)
        return False


allAttsByUUID = {} # todos los atributos
allAttsByName = {} # todos los atributos

allAliasByName = {} # todos los alias creados
allItemsWithAtt = {} # enlaza los atributos a los items que los usan
# =============================================================================
# ---- Patrones para construir las fórmulas
# =============================================================================

updateFormulaInAtts = True # PENDIENTE esto habrá que cambiarlo, está para que funcione por defecto (dice si un atributo se recalcula o se coge sólo su valor, así es más eficiente)
# construimos cómo se piden los valores a los items, envolviendo la info que nos viene del fichero en la fórmula
_EXP_PATTERN_PRE_ITEM_GET = 'item.getAtt("'
_EXP_PATTERN_PRE_CHILD_GET = 'itemChild.getAtt("'
_EXP_PATTERN_AGGREGATABLE_PRE_CHILD_GET = 'itemChild.getAtt("'
if updateFormulaInAtts == True:
    _EXP_PATTERN_POS_CHILD_GET = '").getValue(True)'
else:
    _EXP_PATTERN_POS_CHILD_GET = '").getValue()'

# patron para el pre
_EXP_PATTERN_AGGREGATABLE_PRE_CHILDREN_SET = 'itemChild.setAtt("'
_EXP_PATTERN_AGGREGATABLE_POS_CHILDREN_SET = '")'

# =============================================================================
# # devuelve el atributo sin identificadores
# =============================================================================
def cleanIdentifiers(att):
    regex_children_clean = r":{1}Children" # solo limpio el identificador
    regex_agregar_clean = r":{1}Aggregate" # solo limpio el identificador
    # quito el identificador
    att = re.sub(regex_children_clean,"",att)
    att = re.sub(regex_agregar_clean,"",att)
    return att

# =============================================================================
# # llega la fórmula completa, con código inyectado Python si lo tiene
# =============================================================================
def putItemGetAtt( formula ):
    # quito el código inyectado de python para que no maree
    # me quedo con una fórmula back (que contiene el código python inyectado) para hacer los cambios sobre esta

    # 1) Detectamos los que no tienen indicador :Aggregate ni :Children y le ponemos el indicador de :Item
    formula_back = formula
    _EXP_PATTERN_PRE_ITEM_GET = 'item.getAtt("'
    _EXP_PATTERN_POS_ITEM_GET = '").getValue(True)'

    # formula contiene la parte sin el código python para poder encontrar los nombres de atributos fácilmente
    # ··········································································
    # quitamos codigo inyectado de Python y lo sustituimos por :
    # ··········································································
    # significa una expresión que comience con @  siga con [cualquier whitespace, word character o digito, apertura o cierre de paréntesis, signos de puntuación y punto], que aparezcan tantes veces como quieran seguidos de un @
    regex_python = r"@[\s\w\d\(\)*+\-\\\.]+@"
    formula = re.sub(regex_python,":", formula) # lo sustituyo por ":"
    # quito todos los espacios
    formula = re.sub(r"\s+", "", formula)
    # también limpio espacios en la fórmula back para poder hacer los cambios
    formula_back = re.sub(r"\s+", "", formula_back)

    # significa, expresión que no comienza por ' o + luego tiene un caracter apertura de paréntesis o signos de operación, cualquier combinzación de letras,
    # puede o no tener dígitos, siguen letras, no siguen : ni más letras y no siguen un ' o +
    regex_atributo_y_con_indicadores_no_code = r"(?!'+)[\(\*\+\-\\]{1}[A-Za-z]+[\d]*\w+(?!:)(?!\w+)(?!'+)"
    res = re.findall(regex_atributo_y_con_indicadores_no_code, formula)

    # por cada atributo que he detectado, hago algo de cooking y le meto la parte de código que necesita para operar a nivel ITEM
    for r in res:
        # buscamos un atributo
        attr = re.findall(r"\w+", r)
        resultado = item.getAttValue(attr[0])
        my_string = str(resultado)
        # # le añadimos el código necesario para que resuelva que va a buscar en un ITEM y no agrega ni children
        # my_string = _EXP_PATTERN_PRE_ITEM_GET + attr[0] + _EXP_PATTERN_POS_ITEM_GET
        # cambiamos el atributo (que tiene el símbolo matemático) por el atributo con todo el código para que resuelva en ITEM
        # my_string = re.sub(r, my_string, r)
        operation = re.findall(r"\W", r)[0]
        # cambiamos en la fórmula original
        # tenemos que añadir el caracter de escape para que el simbolo matemático no lo tome como una orden de regex... :-()
        regex = "\{}(?!:)".format(r) # voy a buscar todos los que no tienen indicator (:)
        formula_back = re.sub(regex, operation+my_string, formula_back)

    formula = formula_back

    return formula


def _Debug( cadena ):
    global _debug
    if _debug == True:
        print(cadena)

# =============================================================================
# # le llega una fórmula que ya ha pasado previamente por putItemGetAtt()
# =============================================================================
# devuelve si el att resultado de la fórmula (la izquierda de =) si debe operar o no en Children y la fórmula que está a la derecha
# return
# att = nombre del atributo que habrá que poner en item.setAtt o en itemChild.setAtt dependiendo del valor de set_on_children
# set_on_children = True o False. Si es true habrá que usar itemChild.setAtt. Si es false habrá que usar item.setAtt porque se actualiza en el item en que estamos
# pos : la parte de la derecha de la fórmula sin tocar nada
def resultOperateOnChildren(formula):
    # ··········································································
    # RESULT OF FORMULA : update on children del resultado?
    # ··········································································
    # separamos la fórmula en dos partes


    # 1) primero separamos el atributo RESULTADO del resto. Para ello buscamos el "=" que es lo que separa las dos partes de la fórmula
    #formula = "_sold_FY = (mp*Mp:True)*((100-goal_P)/100)"
    pre = formula.split("=")[0]
    pos = formula.split("=")[1]
    pre = pre.strip(" ")
    pos = pos.strip(" ")

    attRes = pre

    # significa: coger lo que tenga un : y Aggregate
    regex_agregar = r":{1}Aggregate" # miramos si hay attr que haya que agregar valor desde sus Children
    true_false = re.findall(regex_agregar, pre)
    set_on_children = False # por defecto no hay que actualizar en los hijos, se actualizará en el item
    if len(true_false) > 0: # hay que agregar información de este atributo/expression proviniente de los hijos?
        set_on_children = True # tenemos que agregar información
    # limpio pre
    pre = re.sub(regex_agregar,"",pre)
    att = pre


    pos_aggregate = pos # me guardo pos con la información de los atributos



    return att, set_on_children, pos


# =============================================================================
# # cambia cualquier patron que contenga :Aggregate por el valor de agregar todo los atributos de item y ejecutar la sentencia
# =============================================================================
def getAggregateFormula(item, formula):
    pos = formula
    # pseudo:
    # 1) primero encontramos todos los :Aggregate que hay en la formula
    # 2) ejecutamos cada uno
    # 3) cambiamos en la fórmula esa sentencia por el valor obtenido

    aggregateItem = {}
    # 1) primero encontramos todos los :Aggregate que hay en la formula
    # significa, coge todas las letras y un : seguido de Aggregate
    regex_agregar = r"\w+:{1}Aggregate" # cojo el elemento completo para poder actualizar el diccionario updateItemOrChildren
    # puede que haya que ponerle  r"\w+:{1}Aggregate[(:T)]" porque puede venir acompañado de un T para actualizar valores cuando se ejecuta
    # significa coge desde : siempre y cuando lleve Aggregate
    regex_agregar_clean = r":{1}Aggregate" # solo limpio el identificador
    res = re.findall(regex_agregar, pos)

    # 2) buscamos los atributos y los vamos ejecutamos uno a uno
    if len(res) > 0: # hay que agregar información de este atributo/expression proviniente de los hijos?
        # limpio el identificador y lo añado a la lista de campos que tienen que ser obtenidos de los hijos
        for r in res:
            nameAtt = re.findall(r"\w+", r) # limpiamos el atributo para obtener su nombre
            acumulado = 0
            for n in item.cItems: # iteramos por los hijos de este item

                itemChild = allItemsByName[n]
                acumulado += itemChild.getAttValue(nameAtt[0])
            aggregateItem[r] = acumulado

    # 3) cambiamos en la fórmula esa sentencia por el valor obtenido
    for r in res:
        pos = re.sub(r, str(aggregateItem[r]), pos)

    return pos

# =============================================================================
# # limpia de identificadores de inyección de código "@"
# =============================================================================
def cleanPythonInyectedCodeIdentifiers( formula ):
    pos = formula

    pos = re.sub("@", "", pos)

    return pos

# =============================================================================
# # ejecuta todos los pasos para ejecutar cualquier fórmula
# =============================================================================
def computeFormula(item, formula, updateAtt): # ojo, updateAtt todavía no se utiliza!
    formula = putItemGetAtt(formula) # ponemos itemGetAtt() dónde corresponde
    attTargetName, operateOnChildren, formula = resultOperateOnChildren(formula) # opera la fórmula en los children de la entidad
    formula = getAggregateFormula(item, formula) # resuelve si hay que hacer agregados desde los hijos
    formula = cleanPythonInyectedCodeIdentifiers(formula) # limpia el código python inyectado
    return attTargetName, formula

# =============================================================================
# # cualquier atributo que pueda tener un item
# =============================================================================
# los atributos VIVEN dentro de un ITEM
class Att:

        def __init__(self, name, value = 0, tipo = "_attr", dataset = "", datasetColumn = "", formula = "", propagate = False): # los atributos, por defecto, son no propagables
            self.UUID = uuid.uuid1()
            self.name = name
            self.timestamp = datetime.now()
            self.value = value
            self.tipo = tipo
            self.dataset = dataset
            self.datasetColumn = datasetColumn # por si está mapeado a una columna de un dataset, si es un datasetColumn, se ignora la fórmula
            self.formula = formula # un atributo puede contener una fórmula, de tal manera que su valor es el resultado de ejecutar una operación sobre otros elementos
            self.propagate = propagate
            allAttsByUUID[self.UUID] = self
            allAttsByName[self.name] = self


        def evaluate(self, item, formula = "", updateAtt = True): # si updateAtt está a True, actualizamos el valor en el aributo que nos piden
                if formula != "":
                    the_formula = formula
                else:
                    the_formula = self.formula


                attTargetName, result = computeFormula(item, the_formula, updateAtt)

                result = eval(result)

                if updateAtt == True: # si nos piden actualizar la información, así lo hacemos
                    # cargamos en el atributo que nos decía la fórmula, el resultado
                    att = item.getAtt(attTargetName)
                    att.value = result
                    self.value = result

                return result

# =============================================================================
# Devuelve el nombre del atributo sin el nombre del item al que pertenece
# =============================================================================
        def agnosticName(self):
            regex_patron = ":"
            nombre = re.split(regex_patron, self.name)
            return nombre[-1]
# =============================================================================
# Devuelve el valor del atributo
# =============================================================================
        def getValue(self, updateFormula = False): # si queremos que ejecute la formula y esta existe, entonces lo ponemos a True
                if updateFormula == True:
                    return self.evaluate()
                else:
                    return self.value


# sobrecarga de operadores
# source: https://es.stackoverflow.com/questions/188145/overloading-sobrecargar-operadores-en-python


# helpers

        def __str__(self):
               cadena = ""

               #if self.items != None:
               title = ""
               cadena = self.formatea(title)
               return cadena

        def __repr__(self):
               return self.__str__()

        def formatea(self, title = None ): # formatea la salida de la informacion
           if title == None:
                  title = "--- formatea"

           cadena = "\n\t\t\tUUID:\t\t{} \n\t\t\tTimestamp:\t{} \n\t\t\tName:\t\t{} \n\t\t\tValue:\t\t{} \n\t\t\tTipo:\t\t{} \n\t\t\tDataset:\t\t{} \n\t\t\tDatasetColumn:\t\t{} \n\t\t\tFormula:\t\t{} \n\t\t\tPropagate:\t\t{}".format(
                          self.UUID,
                          self.timestamp,
                          self.name,
                          self.value,
                          self.tipo,
                          self.dataset,
                          self.datasetColumn,
                          self.formula,
                          self.propagate
                          )
           return cadena


countShortName = 0

_itemRoot = ""

# =============================================================================
# # un Item tiene padres e hijos, y puede tener atributos
# =============================================================================
# la estructura permite realizar las relaciones entre atributos de diferentes items
# abstract item significa que tiene es un item que es probable que no tenga información aún
class Item:
        def __init__(self, name, datasetColumn = "", datasetName ="", shortName = -1, abstract = -1):
               global countShortName
               global _itemRoot # puntero al itemRoot

               self.UUID = uuid.uuid1()
               if shortName == -1:
                   self.shortName = countShortName # nombre corto para ahorrar tiempo al codificar
               else:
                   self.shortName = shortName # si mandamos un shortName, nos lo quedamos
               self.name = name

               if datasetName != "": # si viene info de dataset, le creo un alias para que sepa buscarlo
                   self.setAlias(datasetName, datasetColumn) # crea un alias para este item

               # self.datasetColumn = datasetColumn # esto hay que revisarlo porque me temo que para eso están los alias...
               self.timestamp = datetime.now()
               # self.abstract = abstract
               self.pItems = {}
               self.cItems = {}
               self.atts = {} # contiene cualquier tipo de atributo para las restricciones de presupuesto (está pensado para poder prescindir de cualquier variable interna)
               self.allAliasByName = {} # diccionario autocontenido para rastrear los alias que puede tener este item en cada dataset
               self.contadorPropagate = 0

               allItemsByUUID[self.UUID] = self
               allItemsByName[self.name] = self
               countShortName += 1

               # singleton de _itemRoot
               try:
                   _itemRoot = allItemsByName[STR_ROOT]
                   # hacemos que este item sea hijo del _ROOT
               except:
                   _itemRoot = Item(STR_ROOT)
               self.setParent(_itemRoot) # todos los items son hijos de _ROOT




        def linkParentToChild(self, parent, child, link = True):
               parent.addChild(child, False) # lo pongo a False para que no se propague

        def linkChildToParent( self, parent, child, link = True):
               child.setParent(parent, False) # evito propagación

        def unlinkParentToChild( self, parent, child, link = True ):
               parent.delChild(child, False) # evito propagación

        def unlinkChildToParent( self, parent, child, linkf = True ):
               child.delParent(parent, False) # evito propagación


        # =============================================================================
        # # Propagación de definición de atributos
        # =============================================================================
        def propagate(self, copyValue = False, recursive = False):
            global contadorPropagate
            """


            Parameters
            ----------
            copyValue : TYPE, optional
                DESCRIPTION. The default is False.
            recursive : TYPE, optional
                DESCRIPTION. The default is False. Si es True, entonces propagará la información a hijos e hijos de sus hijos

            Returns
            -------
            None.

            """
            for k,v in self.cItems.items():
                self.contadorPropagate += 1
                itemChild = allItemsByName[k]
                itemChild.addAtts(self, copyValue)
                if recursive == True:
                    itemChild.propagate( copyValue, recursive )
            cadena = "\nitem {} ha propagado a {} miembros".format(
                self.name,
                self.contadorPropagate)
            _Debug(cadena)
            self.contadorPropagate = 0


# ---- Parents

        def addParent( self, item, link = True ):
           if self.UUID == item.UUID: # no permitimos que un item sea padre de si mismo
                  cadena ="\nItem:addParent:\tUn elemento no puede ser padre de si mismo"
                  _Debug(cadena)
                  return False
           else:
                  try:
                         child = self.cItems[item.name]  # si el elemento ya es hijo, no puede ser padre!!!!
                         cadena = "\nItem:addParent:\tEl elemento {} ya es hijo, no puede ser padre".format(item.name)
                         _Debug(cadena)
                         return False
                  except:
                         self.pItems[item.name] = item.UUID
                         if link == True:
                                self.linkParentToChild(item, self) # evito la propagación
                         return True


        def setParent(self, item, link = True ): # para que sea readable
           self.addParent(item, link)

        def eraseParents(self, link = True ):
           for name in self.pItems: # quitamos a todos los padres este hijo
                  parent = allItemsByName[name]
                  self.unlinkParentToChild(parent, self, False) # evito la propagación
           self.pItems.clear() # limpio la lista de padres

        def addParents( self, item, link = True ):
           for k, uuid in item.pItems.items():
                  parent = allItemsByUUID[uuid]
                  self.addParent(parent)


        def delParent(self, item, link = True ):
           del self.pItems[item.name]
           if link == True:
                  self.unlinkParentToChild( item, self, False)

        def getParents(self):
           return self.pItems

        def copyParents( self, item, link = True ): # copia los parents de un item
              self.eraseParents()
              self.addParents( item, link )

        def getParent( self, name ):
           try:
                  return self.pItems[name]
           except:
                  cadena = "\nItem:getParent:\tEl elemento : {}  no existe ".format(
                      name)
                  _Debug(cadena)

# ---- Children

        def addChild( self, item, link = True ):
           if self.UUID == item.UUID: # no permitimos que un item sea hijo de si mismo...
                  cadena = "\nItem:addChild:\tUn elemento no puede ser hijo de si mismo"
                  _Debug(cadena)
                  return False
           else:
                  try:
                         padre = self.pItems[item.name]  # si el elemento ya es padre, no puede ser hijo!!!!
                         cadena = "\nItem:addChild:\tEl elemento {} ya es padre, no puede ser hijo".format(
                             item.name)
                         _Debug(cadena)
                         return False
                  except:
                         self.cItems[item.name] = item.UUID
                         if link == True:
                                self.linkChildToParent(self, item) # evito la propagación
                         return True


        def setChild(self, item, link = True ): # para que sea readable
           self.addChild(item)

        def eraseChildren(self, delete = False ):
           for name in self.cItems: # quitamos a todos los hijos este padre
                  child = allItemsByName[name]
                  self.unlinkChildToParent(self, child, False) # desenlazo este hijo de su padre (que desenlazará este padre del hijo también)
                  # llamo recursivamente a todos los hijos de este hijo también
                  child.eraseChildren(delete)
                  # si delete es True significa que tengo que borrarlo
                  if delete == True:
                      del allItemsByName[name]
                      child.eraseAtts() # podría haber un problema cuando es una expresión...
                      del child
           self.cItems.clear() # cuando he terminado borro la lista de hijos

        def addChildren( self, item, link = True ):
           for k, uuid in item.cItems.items():
                  child = allItemsByUUID[uuid]
                  self.addChild(child)

        def delChild(self, item, link = True ):
           del self.cItems[item.name]
           if link == True:
                 self.unlinkChildToParent( self, item, False)

        def getChildren(self):
           return self.cItems

        def copyChildren( self, item, link = True ): # copia los children de un item
              self.eraseChildren()
              self.addChildren( item, link )

        def getChild( self, name ):
           try:
                  return self.cItems[name]
           except:
                  cadena = "\n\tItem:getChild:\tChildren: El elemento : {} no existe ".format(
                      name)
                  _Debug(cadena)



# ---- Attributes

        def addAtt( self, name, value, tipo, dataset, datasetColumn, formula = "", propagate = False ):
            """

            Parameters
            ----------
            name : TYPE
                DESCRIPTION.
            value : TYPE
                DESCRIPTION.
            tipo : TYPE
                DESCRIPTION.
            dataset : TYPE
                DESCRIPTION.
            datasetColumn : TYPE
                DESCRIPTION.
            formula : TYPE, optional
                DESCRIPTION. The default is "".
            propagate : TYPE, optional
                DESCRIPTION. The default is False.

            Returns
            -------
            None.

            """
            tag = self.buildTag(name)

            self.linkAttToItem(name) # enlazo el Att al Item en un diccionario global

            if tipo == "_exp":
                self.atts[tag] = allAttsByName[name] # es una _expr, no lo vuelvo a crear, sólo me quedo con un puntero a su identificador
            else: # cualquier otra cosa la creo (_attr, _dataset, ...)
                self.atts[tag] = Att(tag, value, tipo, dataset, datasetColumn, formula, propagate)

# =============================================================================
# Añadimos atributos en base a una list de atributos que nos llegan
# =============================================================================
        def addAttsFromDict(self, listOfAtts ):

            for att in listOfAtts:
                # print(f"Rastreando atributo {k}")
                # buscamos el atributo

                name = att.name
                tag = self.buildTag(name)

                self.linkAttToItem(name) # enlazo el Att al Item en un diccionario global

                if att.tipo == "_exp":
                    self.atts[tag] = allAttsByName[name] # es una _expr, no lo vuelvo a crear, sólo me quedo con un puntero a su identificador
                else: # cualquier otra cosa la creo (_attr, _dataset, ...)
                    # print(f"Creando el atributo {k}")
                    self.atts[tag] = Att(tag, att.value, att.tipo, att.dataset, att.datasetColumn, att.formula, att.propagate)




            # if tipo == "_attr":
            #     self.atts[tag] = Att(tag, value, tipo, dataset, datasetColumn, formula, propagate)
            # else:
            #     self.atts[tag] = allAttsByName[name] # es una _expr, no lo vuelvo a crear, sólo me quedo con un puntero a su identificador

        def addAtts( self, item, copyValue = False ):
            """


            Parameters
            ----------
            item : TYPE
                DESCRIPTION.

            Returns
            -------
            None.

            """
            a = ""
            # for k, v in item.atts.items():
            #        tag = k.split(":") # hay que quitarle el nombre del ITEM, así que lo limpio
            #        self.addAtt( tag[0], v)
            for k,v in item.atts.items():
                # print(f"\natt:{k}")
                try: # si es un _attr lo encontraré
                    a = allAttsByName[k]
                    tag = a.name.split(":") # hay que quitarle el nombre del ITEM, así que lo limpio

                except: # en otro caso es que es un _expr con lo que no se le agrega el nombre del item: se lo quitamos
                    name = k.split(":") # hay que quitarle el nombre del ITEM, así que lo limpio
                    a = allAttsByName[name[1]]
                    tag = name

                v = a.value
                tipo = a.tipo
                dataset = a.dataset
                datasetColumn = a.datasetColumn
                formula = a.formula
                propagate = a.propagate
                if copyValue == True:
                    self.addAtt( tag[1], v, tipo, dataset, datasetColumn, formula, propagate)
                else:
                    self.addAtt( tag[1], 0, tipo, dataset, datasetColumn, formula, propagate)

# =============================================================================
# Añade todos los atributos recursivamente (de toda su jerarquía) a itemTarget
# Para agregar las columnas coge la jerarquía de un hijo completo
# =============================================================================
        def addAttsExtended_BACK( self, itemTarget, itemSource, prefix_list = "", copyValue = False):
            """


            Parameters
            ----------
            itemTarget : TYPE - item al que se agregará el primer nivel de hijos de itemSource (que actúa como contenedor)
                DESCRIPTION.
            itemSource : TYPE - item contenedor - se crean todos los atributos de su primera jerarquía de hijos y luego se crean tantos hijos como su primer nivel dentro de itemTarget
                DESCRIPTION.
            prefix_list : TYPE, optional - lista de prefijos para cada atributo, dependiendo del nivel de jerarquía dentro de itemSource, si no llega nada, se construye un nombre de atributo con el nombre de target
                DESCRIPTION. The default is "" erase = False.
            copyValue : TYPE, optional
                DESCRIPTION. The default is True. Se copian los valores originales o no.

            Returns
            -------
            None.

            """
            a = ""
            # agrego todos los atributos de este elemento al itemTarget
            for k,v in itemSource.atts.items():
                # print(f"\natt:{k}")
                try: # si es un _attr lo encontraré
                    a = allAttsByName[k]
                    #tag = a.name.split(":") # hay que quitarle el nombre del ITEM, así que lo limpio
                    tag = k

                except: # en otro caso es que es un _expr con lo que no se le agrega el nombre del item: se lo quitamos
                    name = k.split(":") # hay que quitarle el nombre del ITEM, así que lo limpio
                    a = allAttsByName[name[1]]
                    #tag = name
                    tag = k

                print(f"Trabajando con el atributo {tag}")
                v = a.value
                tipo = a.tipo
                dataset = a.dataset
                datasetColumn = a.datasetColumn
                formula = a.formula
                propagate = a.propagate

                if copyValue == True:
                    itemTarget.addAtt( tag, v, tipo, dataset, datasetColumn, formula, propagate)
                else:
                    itemTarget.addAtt( tag, 0, tipo, dataset, datasetColumn, formula, propagate)


            for the_key, the_value in itemSource.cItems.items(): # rastreamos los hijos
                print(f"Trabajando con el item {the_key}")
                itemChild = allItemsByName[the_key]
                self.addAttsExtended(itemTarget, itemChild, copyValue)


        def addAttsExtended( self, itemTarget, itemSource, prefix_list = "", copyValue = False):
            """


            Parameters
            ----------
            itemTarget : TYPE - item al que se agregará el primer nivel de hijos de itemSource (que actúa como contenedor)
                DESCRIPTION.
            itemSource : TYPE - item contenedor - se crean todos los atributos de su primera jerarquía de hijos y luego se crean tantos hijos como su primer nivel dentro de itemTarget
                DESCRIPTION.
            prefix_list : TYPE, optional - lista de prefijos para cada atributo, dependiendo del nivel de jerarquía dentro de itemSource, si no llega nada, se construye un nombre de atributo con el nombre de target
                DESCRIPTION. The default is "" erase = False.
            copyValue : TYPE, optional
                DESCRIPTION. The default is True. Se copian los valores originales o no.

            Returns
            -------
            None.

            """
            a = ""
            # agrego todos los atributos de este elemento al itemTarget
            for k,v in itemSource.atts.items():
                # print(f"\natt:{k}")
                try: # si es un _attr lo encontraré
                    a = allAttsByName[k]
                    #tag = a.name.split(":") # hay que quitarle el nombre del ITEM, así que lo limpio
                    tag = k

                except: # en otro caso es que es un _expr con lo que no se le agrega el nombre del item: se lo quitamos
                    name = k.split(":") # hay que quitarle el nombre del ITEM, así que lo limpio
                    a = allAttsByName[name[1]]
                    #tag = name
                    tag = k

                print(f"Trabajando con el atributo {tag}")
                v = a.value
                tipo = a.tipo
                dataset = a.dataset
                datasetColumn = a.datasetColumn
                formula = a.formula
                propagate = a.propagate

                if copyValue == True:
                    itemTarget.addAtt( tag, v, tipo, dataset, datasetColumn, formula, propagate)
                else:
                    itemTarget.addAtt( tag, 0, tipo, dataset, datasetColumn, formula, propagate)


            for the_key, the_value in itemSource.cItems.items(): # rastreamos los hijos
                print(f"Trabajando con el item {the_key}")
                itemChild = allItemsByName[the_key]
                self.addAttsExtended(itemTarget, itemChild, copyValue)



        # =============================================================================
        # Enlazo al diccionario global, el atributo al item
        # =============================================================================
        def linkAttToItem(self, name):
            internalDictionary = {}
            if name not in allItemsWithAtt.keys(): #▼ si el atributo no existe en el diccionario global, creo una nueva entrada
                allItemsWithAtt[name] = internalDictionary

            allItemsWithAtt[name][self.name]=self # añado al diccionario global el atributo diciendo a qué item pertenece

        # =============================================================================
        # Desenlazo al diccionario global, el atributo del item
        # =============================================================================
        def unlinkAttToItem(self, name):
            # localicalizo el att en el diccionario de atributos por item
            try:
                it = allItemsWithAtt[name] # recupero el diccionario de este atributo, que contendrá la ristra de items en que aparece
                del it[self.name] # borro específicamente la entrada al diccionario
                return True
            except:
                return False


        def copyAtt( self, attSource, copyValue = False):
            """
            Copia toda la información de attSource a itemAtt

            Parameters
            ----------
            itemAtt : TYPE
                DESCRIPTION.
            attSource : TYPE
                DESCRIPTION.

            Returns
            -------
            None.

            """
            a = attSource
            tag = a.name.split(":") # hay que quitarle el nombre del ITEM, así que lo limpio
            if copyValue == True:
                v = a.value
            else:
                v = 0
            tipo = a.tipo
            dataset = a.dataset
            datasetColumn = a.datasetColumn
            formula = a.formula
            propagate = a.propagate
            self.addAtt( tag[0], v, tipo, dataset, datasetColumn, formula, propagate)


        def setAtt( self, name, value, tipo = "_attr", dataset = "", datasetColumn = "", formula = "", propagate = False):
            """


            Parameters
            ----------
            name : TYPE
                DESCRIPTION.
            value : TYPE
                DESCRIPTION.
            tipo : TYPE, optional
                DESCRIPTION. The default is "_attr".
            dataset : TYPE, optional
                DESCRIPTION. The default is "".
            datasetColumn : TYPE, optional
                DESCRIPTION. The default is "".
            formula : TYPE, optional
                DESCRIPTION. The default is "".
            propagate : TYPE, optional
                DESCRIPTION. The default is False.

            Returns
            -------
            None.

            """
            self.addAtt( name, value = value, tipo = tipo, dataset = dataset, datasetColumn = datasetColumn, formula = formula, propagate = propagate )


# =============================================================================
# Borra todos los atributos
# =============================================================================
        def eraseAtts(self):
            """


            Returns
            -------
            None.

            """

            # rastreo todos los atributos de este item
            for k,v in self.atts.items():
                # self.unlinkAttToItem(k) # desenlazo el item
                self.delAtt(k)

            self.atts.clear() # limpio el diccionario local

# =============================================================================
# Borra un atributo
# =============================================================================
        def delAtt(self, name):
            """


            Parameters
            ----------
            name : TYPE
                DESCRIPTION.

            Returns
            -------
            None.

            """
            tag = self.buildTag(name)

            self.unlinkAttToItem(name)

            atributo = self.atts[name] # borro el atributo
            del atributo

        def getAtts( self ):
            """


            Returns
            -------
            TYPE
                DESCRIPTION.

            """
            return self.atts

# =============================================================================
# copia en el elemento los atributos de otro item
# Si erase está a True, elimina los atributos anteriores
# =============================================================================
        def copyAtts( self, item, erase = False, copyValue = False ): #• si copyValue está a False, sólo copia la estructura, no los valoes (tiene sentido!)
            """


            Parameters
            ----------
            item : TYPE
                DESCRIPTION.

            Returns
            -------
            None.

            """
            if erase == True:
                self.eraseAtts()
            self.addAtts( item, copyValue)

# =============================================================================
# Copia atributos entre dos items, manteniendo el itemTarget
# =============================================================================
        def copyAttsExtended(self, itemTarget, itemSource, prefix_list = "", erase = False, copyValue = True):
            if erase == True:
                itemTarget.eraseAtts()

            self.addAttsExtended( itemTarget, itemSource, prefix_list, copyValue)


# =============================================================================
# Obtiene un atributo por nombre
# =============================================================================
        def getAtt( self, name ):
            """


            Parameters
            ----------
            name : TYPE
                DESCRIPTION.

            Returns
            -------
            TYPE
                DESCRIPTION.

            """
            try:
                   tag = self.buildTag(name)
                   return self.atts[tag]
            except:
                   cadena = "\n\tItem:getAtt:\tAtts: El elemento : {}  no existe ".format( name)
                   _Debug(cadena)
                   return False
# =============================================================================
# Obtiene un atributo por su tag
# =============================================================================
        def getAttByTag(self, tag): # se le manda el tag completo

            try:
                   return self.atts[tag]
            except:
                   cadena = "\n\tItem:getAttByTag;\tAtts: El elemento : {}  no existe ".format(
                       name)
                   _Debug(cadena)

                   return False
# =============================================================================
# Obtiene el valor de un atributo
# =============================================================================
        # si update == True entonces forzamos que el atributo resuelva su valor (expresion o _database)
        def getAttValue( self, name, update = False ):

            att = self.getAtt(name)
            if att != False:
                if att.tipo == STR_DBATTR:
                    self.resolveAttValueInDataset( att ) # pongo el valor en el atributo
                return att.value
            else:
                return False

# =============================================================================
# Sabe recoger la info de la dataset y ponerlo como valor del atributo
# =============================================================================
        def resolveAttValueInDataset( self, att ):
            global _debug
            if len(self.cItems) == 0: # y es el último de la fila (es decir, no tiene hijos, porque si no será una entidad de agregación)
                data = allDatasetsByName[att.dataset] # cogemos el dataset (que está cargado en memoria)
                # el atributo buscado en un dataset tiene que tener ligado el item.name como alias en ese dataset
                aliasName = self.createAliasName(att.dataset)
                index = allAliasByName[aliasName] # encuentra el campo por el que se busca en la tabla correspondiente
                value = self.name
                columns = att.datasetColumn

                resultado = _h_getDatasetValue("", data, index, value, columns)

                cadena = "\nresolveAttValueInDataset\t\titem\t{}data\t{}\taliasName\t{}\tindex\t{}\tvalue\t{}\tcolumns\t{}\tresultado{}".format(
                    self.name,
                    att.dataset,
                    aliasName,
                    index,
                    value,
                    columns,
                    resultado)

                _Debug(cadena)

                if len(resultado)>0:
                    # como resultado será seguramente un Series de Python (una matrix unidimensional que contiene cualquier tipo de dato)
                    # vamos a obligarle a coger el primer elemento. Esta es la sintaxis para hacerlo
                    att.value = resultado.iat[0]
                else:
                    att.value = 0


# =============================================================================
# # actualiza el valor del atributo (cuando es una expresión o carga info de base de datos)
# ojo, sólo se podrá actualizar si no tiene hijos (en otro caso será un agregador y no tendría sentido)
# =============================================================================
        def updateAtt(self, name, update = True):
            try:
                att = self.getAtt(name)
            except:
                cadena = "\n\n\tItem:updateAtt:\tEl atributo {} no se resuelve correctamente! en el item {}".format(
                    name,
                    self.name
                    )
                _Debug(cadena)

            if att.tipo == STR_DBATTR: # si es un atributo ligado a un dataset
                if len(self.cItems) == 0: # y es el último de la fila (es decir, no tiene hijos, porque si no será una entidad de agregación)
                    # data = allDatasetsByName[att.dataset] # cogemos el dataset (que está cargado en memoria)
                    # # el atributo buscado en un dataset tiene que tener ligado el item.name como alias en ese dataset
                    # aliasName = self.createAliasName(att.dataset)
                    # index = allAliasByName[aliasName] # encuentra el campo por el que se busca en la tabla correspondiente
                    # value = self.name
                    # columns = att.datasetColumn
                    # value = _h_getDatasetValue("", data, index, value, columns)
                    # att.value = value[0]
                    self.resolveAttValueInDataset( att ) # pongo el valor en el atributo
            if att.tipo == STR_EXP: # si es una expresión, puede hacerse aunque tenga hijos
                att.evaluate(self, "", update)
                # ---- pendiente
                return


# =============================================================================
# # actualiza el valor de todos los atributos (cuando es una expresión o carga info de base de datos)
# =============================================================================
        def updateAtts(self, updateAtt = True):
            for k,v in self.atts.items():
                self.updateAtt(self.getAttrName(k), updateAtt)


# =============================================================================
# Actualiza todos los hijos de este padre
# =============================================================================
        def updateAttsChildren( self ):
            contador = 0
            for k,v in self.cItems.items(): # rastreamos todos los hijos
                cadena = "\n\tupdateAttsChildren: Actualizando atributos de \t{}".format(
                    k
                    )
                _Debug(cadena)
                contador += 1
                itemChild = getItemByName(k) # apuntamos al item hijo
                itemChild.updateAtts() # actualizamos sus atributos
            cadena = "\n\tItem:updateAttsChildren:\tActualizados {} hijos ".format(
                contador)
            _Debug(contador)

# ---- Alias


        def createAliasName(self, datasetName):
            return self.name+":"+datasetName

        def setAlias(self, dataset, datasetcolumn):
            """


            Parameters
            ----------
            dataset : TYPE
                DESCRIPTION.
            datasetcolumn : TYPE
                DESCRIPTION.

            Returns
            -------
            None.

            """
            aliasName = self.createAliasName(dataset)
            allAliasByName[aliasName] = datasetcolumn
            self.allAliasByName[aliasName] = datasetcolumn # sólo para ver qué alias tiene este elemento

        # le doy el nombre del dataset y el alias y me devuelve en qué columna hay que mirar para obtener el valor
        # importante para _database_unique
        def getAlias( self, dataset):
            aliasName = self.createAliasName(dataset)
            datasetColumn = allAliasByName[aliasName]
            return datasetColumn


        # evalua una expresion
        def evaluate(self, name, formula = "", updateAtt = True):

            tag = self.buildTag(name)
            try:
                att = allAttsByName[tag] # si existe es que es un atributo porque contendrá primero el nombre del item
            except:
                att = allAttsByName[name]
                formula = att.formula

            value = att.evaluate(self, formula, updateAtt)
            return value


# ---- helpers

        def buildTag(self, name): # construye un tag único para evitar que un ATT con un valor diferente machaque el que ya tiene el valor por defecto
            tag = "{}:{}".format(
               self.name,
               name)
            return tag

        def getAttrName(self, tag): # devolvemos el nombre del atributo sin la construcción del tag (necesario para el mapeo de columnas en bases de datos)
            text = tag.split(":")
            return text[1]

        # =============================================================================
        # Devuelve un nuevo Item con toda su información o incluyendo toda sus jerarquía de hijos
        # como un dataframe
        # =============================================================================
        def toRaw( self, name, recursive = False ):
            # ceamos el item a devolver
            try:
                item = allItemsByName[name]
            except:
                item = Item(name) # si el item existe lo reutiliza!

            # como es un item contenedor vamos a crear elementos adicionales por cada children y a copiarle todos sus atributos
            itemLinea = Item(self.name+"_L") # cada uno de estos items tienen que replicar TODOS los atributos que contienen sus hijos y los hijos de sus hijos (replicar hacia arriba)
            itemLinea.setParent(item)
            # copiamos todos los atributos y sus valores al nuevo item
            item.copyAtts( self, erase=False, copyValue=True)
            if recursive == True: # tenemos que rastrear todos sus hijos y los hijos de sus hijos?
                for k,v in self.cItems.items():
                    itemChild = allItemsByName[k]
                    itemChild.toRaw(name, recursive)
            return item


# ---- Representation

        def __str__(self):
               cadena = ""
               cadena_dict = ""
               #if self.items != None:
               title = "ITEM : ------------------------------------------------------------------------------------------------------ "
               cadena = self.formatea(title)
               return cadena



        def __repr__(self):
               return self.__str__()

        def formatea(self, title = None ): # formatea la salida de la informacion
           if title == None:
                  title = "--- formatea"

           cadena = "\n{} \nName:\t\t{} \nshortName:\t\t{} \nUUID:\t\t{} \nTimestamp:\t{} \n".format(
                          title,
                          self.name,
                          self.shortName,
                          self.UUID,
                          self.timestamp
                          )

           cadena += "\n\n\t Atts : "
           for k,v in self.atts.items():
                     cadena += "\n{}".format( v )

           # cadena += "\n\n\t Atts : \n\t\t\t\t : \t{}".format(
           #               self.atts
           #               )

           cadena += "\n\n\t Parents : "
           for k,v in self.pItems.items():
                     cadena += "\n\t\t\t\t : \t {} \t\t{}".format( k, v )

           cadena += "\n\n\t Children :"
           for k,v in self.cItems.items():
                     cadena += "\n\t\t\t\t : \t {} \t\t{}".format( k, v )

           # cadena += "\n\n\t Relationships :"
           # for k,v in self.attsRelationships.items():
           #           cadena += "\n\t\t\t\t : \t {} \t\t{}".format( k, v )

           cadena += "\n\n\t Alias :"
           for k,v in self.allAliasByName.items():
                     cadena += "\n\t\t\t\t : \t {} \t\t{}".format( k, v )

                     # regex_sub_k = r"\w+" # solo muestro si parte de la clave pertenece a este nombre
                     # _sub_k = re.findall(regex_sub_k, k)
                     # if _sub_k[0] == self.name: # si la primera parte de la clave contiene este nombre (el del item)
                     #     cadena += "\n\t\t\t\t : \t {} \t\t{}".format( k, v )

           # mostramos lista de atributos en formato sintetizado
           cadena += "\n\n\t Atts Sintetizado :\n\t\t\t"
           for k,v in self.atts.items():
                     sintetico = k.split(":")
                     if len(sintetico) > 0:
                         texto = sintetico[len(sintetico)-1] # por si tiene más de un :
                     else:
                         texto = k
                     cadena += "{},  ".format( texto )

           cadena += "\n\n\t Totals : Atts:\t{}\tParents:\t{}\tChildren:\t{}\tAlias:\t{}".format(
               len(self.atts),
               len(self.pItems),
               len(self.cItems),
               len(self.allAliasByName)
               )

           return cadena

# ---- Vocabulary
            # =============================================================================
            # Devuelve un Item respuesta (se puede haber creado en una acción) si existe, en otro caso False
            # =============================================================================
           def getResponse(self, name):
               try:
                   item = allItemsByName[name]
                   return item
               except:
                   return False

           def executeAction(self, name, action):
               try:
                   item = allItemsByName[name] # si la acción existe
                   # ejecuta la acción
                   return item # devuelve el resultado
               except:
                  item = Item(name)
                  att = Att(name, 0, STR_ACTION, formula = action)
                  self.linkAttToItem(name)
                  # ejecuta la acción
                  return item # devuelve el resultdo


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Filtrado de base de datos por valores en columnas
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# Attributes By Default
# creamos una estructura de atributos por defecto
def _h_budgetStructByDefault( item, atts = "" ):
    item.setAtt("Default", -1, "_attr", "", "")

# Una vez creados el item raiz le pone la estructura de atributos
def _h_createItemRaiz( itemRaiz, attsStructFunction = _h_budgetStructByDefault):
        attsStructFunction(itemRaiz)

# =============================================================================
# ---- CHILD ITEMS
# =============================================================================
#
# crea items children para el item raiz, tantos como líneas unique de la columna requerida del dataset
#
# name: nombre del item
# itemRaiz: "Cuenta" (item raiz, ya creado, que va a ser el padre de los items que creemos ahora)
# dataset: df_Cap (database que contiene la info de los items)
# datasetIndex: el campo que se usará cuando queramos recuperar información de este elemento
# datasetColumn: "Account Name" (columna que contiene los nombres de los items - no coge repeticiones)
# atts: atributos para mandarlos a la función de parsing y que le cree los atributos que vienen del fichero de configuración
# attsStructFunction = función para crear los atributos a cada item
#
# Esta función crea un Alias por cada elemento en la database de la que se extrae
#
def _h_createChildsItemRaiz( name, itemRaiz, dataset, datasetName, datasetColumn, datasetColumnParent, atts, attsStructFunction = _h_budgetStructByDefault):
    """

    Parameters
    ----------
    itemRaiz : TYPE string
        DESCRIPTION. Nombre del item al que se adhieren como children los items que crea la función
    dataset : TYPE DataFrame
        DESCRIPTION. Dataset desde la que se lee la información para crear los items
    datasetColumn : TYPE string
        DESCRIPTION. Nombre de la columna del dataset a leer
    datasetColumnParent : TYPE string
        DESCRIPTION. Columna en el dataset que contiene el parent al que se agregan
    atts : TYPE string
        DESCRIPTION. Atributos a crear
    attsStructFunction : TYPE, optional - function
        DESCRIPTION. The default is _h_budgetStructByDefault. A esta función se la llama por cada item creado para crearle sus atributos.

    Returns
    -------
    None.

    """
    aggregateParent = allItemsByName[itemRaiz] # padre del que todos los items que creemos van a colgar
    for r in dataset[datasetColumnParent].unique():
        # print("_h_createChildsItemRaiz")

        # si el item existe, lo actualiza
        try:
            item = allItemsByName[r]
        except:
            item = Item(r, datasetColumn ) # creo el item


        #item = Item(r, datasetColumn ) # creo el item

        item.setAlias(datasetName, datasetColumn)
        item.setParent(aggregateParent)
        attsStructFunction(item, "_item", atts) # le cargamos los atributos

# helper
# mostramos la info de un item buscándolo por nombre
def _h_showElementsOfItem(entidad):
    """

    Parameters
    ----------
    itemName : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    print(allItemsByName[entidad])


# coge, en este caso de la base de datos de movimientos, porque es la que me interesa, y pone como hijos los ITEMS ya creados, colgando de su PADRE
# el ITEM PADRE se coge como el valor de la datasetColumnParent, ya que es el nombre asignado al ITEM creado anteriormente
#
# Esta función crea un alias automáticamente para cada elemento en el dataset que se está buscando
#
def _h_linkItemToParent( datasetName, datasetColumn, datasetColumnParent, datasetColumnChild, atts, attsStructFunction = _h_budgetStructByDefault):
    """

    Parameters
    ----------
    datasetName : TYPE
        DESCRIPTION.
    datasetColumn : TYPE
        DESCRIPTION.
    datasetColumnParent : TYPE
        DESCRIPTION.
    datasetColumnChild : TYPE
        DESCRIPTION.
    atts : TYPE
        DESCRIPTION.
    attsStructFunction : TYPE, optional
        DESCRIPTION. The default is _h_budgetStructByDefault.

    Returns
    -------
    None.

    """

    allParents = ""
    dataset = allDatasetsByName[datasetName] # get the dataset

    try:
        allParents = dataset[datasetColumnParent].unique() # me quedo con cada elemento parent
        columnParent = datasetColumnParent
    except:
        # tenemos que trabajar con el alias porque no está mapeado con el mismo nombre
        columnParent = allItemsByName[datasetColumnParent].getAlias(datasetName)
        allParents = dataset[columnParent].unique() # me quedo con cada elemento parent

    for r in allParents: # me quedo con cada elemento parent
        itemParent = allItemsByName[r] # cojo el item con el nombre recuperado
        items = dataset[dataset[columnParent]==r][datasetColumnChild] # cojo todos sus hijos
        for i in items:
            try: # si no existe el item, lo tengo que crear
                item = allItemsByName[i]
            except: # creo el Item y le asigno todos sus atributos
                item = Item(i)
                attrsText = atts
                _h_parsingAtts(item, "_attr", attrsText, datasetName)
            # print("_h_linkItemToParent")
            item.setParent(itemParent)
            item.setAlias(datasetName, datasetColumn) # le creo un alias para poder acceder posteriormente por clave
            attsStructFunction(item, "_item", atts)

# crea todos los elementos y sus atributos, tal y como se le informa en la hoja de configuración STRUCT
# def createElements(dataset):
#     df = dataset.set_index("Item")
#     for r in df[df].unique():
#         item = Item(r)

import numpy as np


# =============================================================================
# Devuelve True si x es nan o ""
# =============================================================================
def _h_is_nan(x):
    """

    Parameters
    ----------
    x : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    """



    return (x is np.nan or x != x or x == "")

# =============================================================================
# # añade, recursivamente, todas las columnas de un dataset concreto como atributos a cada item
# =============================================================================
def _h_addColumnsAsAttributes( item, datasetName, propagate = False ):
    """


    Parameters
    ----------
    item : TYPE
        DESCRIPTION.
    datasetName : TYPE
        DESCRIPTION.
    propagate : TYPE, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    None.

    """

    dataset = allDatasetsByName[datasetName] # direccionamos el dataset
    columnas = dataset.columns[:] # cogemos todas las columnas
    for r in columnas:
        item.addAtt(r, 0, STR_DBATTR, datasetName, r, propagate = propagate) # creamos un atributo y notificamos que pertenece a una dataset concreta
    # lo metemos también en toda la jerarquía de hijos
    for n in item.cItems:
        childItem = allItemsByName[n]
        _h_addColumnsAsAttributes(childItem, datasetName, propagate)



# =============================================================================
# # añade atributos ya creados previamente a un item
# =============================================================================
def _h_parsingAtts(item, attrName, attsText, datasetName = "", propagate = False):
    """
    Parameters
    ----------
    item : TYPE
        DESCRIPTION.
    attrName : TYPE
        DESCRIPTION.
    text : TYPE
        DESCRIPTION.
    datasetName : TYPE, optional
        DESCRIPTION. The default is "".
    propagate : TYPE, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    bool
        DESCRIPTION.

    """

    text = attsText
    #print(attrName)

    if _h_is_nan(text):
        return False

    if text == "":
        return False

    if attrName != "_exp": # si no es una expresión

        if text == "_all": # transforma todas las columnas del dataset en atributos directamente
            # cargamos todas las columnas del dataset al que pertenece y los metemos como atributos
            _h_addColumnsAsAttributes( item, datasetName, propagate)
            # dataset = allDatasetsByName[datasetName]
            # columnas = dataset.columns[:]
            # for r in columnas:
            #     item.addAtt(r, 0, "_attr", datasetName, r)
            #     # lo metemos también en toda la jerarquía de hijos
            #     for n in item.cItems.items():

        else: # es un "_attr"
            atts = text.split("|")
            for a in atts:
                subatts = a.split(":")
                if len(subatts)>1: # si le estoy cambiando el valor, le mando el valor que he puesto
                    name = subatts[0]
                    value = subatts[1]
                    tipo = "_attr"
                    dataset = ""
                    datasetColumn = ""
                    # cadena = "{}\t{} (*)".format(
                    #      name,
                    #      value)
                    # print(cadena)
                else: # coge el valor por defecto del atributo
                    att = allAttsByName[a] # localizo el valor del atributo
                    name = att.name
                    if att.tipo == "_database_attr":
                        value = 0
                        tipo = "_database_attr"
                        dataset = att.dataset
                        datasetColumn = att.datasetColumn
                    else:
                        value = att.value
                        tipo = "_attr"
                        dataset = ""
                        datasetColumn = ""
                    # cadena = "{}\t{}".format(
                    #      name,
                    #      value)
                    # print(cadena)
                # buscamos el atributo entre todos los creados
                item.setAtt(name, value, tipo, dataset, datasetColumn, propagate = propagate)

    if attrName == "_exp": # si es una expresión
        name = text
        value = -1
        tipo = "_exp"
        item.setAtt(name, value, tipo, dataset = "", datasetColumn = "", formula = "", propagate = propagate)

    return True



# =============================================================================
# ---- DATASETS LOADING
# # todos los datasets quedan ya abiertos y cargados, para ser usados más tarde
# # el fichero de configuración de datasets es DATASETSINFO
# history:
# incluyo el que el dataset Struct pueda ser definido en DatasetsInfo para facilitar múltiples configuraciones
# =============================================================================

import xlsxwriter # para poder escribir hojas excel desde Python

# creamos una estructura de atributos por defecto
def _h_budgetStructDatasets( item ):
    item.setAtt("Item Name", "")
    item.setAtt("Value", "")
    item.setAtt("InOut", "")

# cambio al directorio de trabajo
PC_raiz = "D://OneDrive//Artificial Intelligence//50 - Proyectos//GA Budget//Git//GA-Budget-master//" # voy a poner la raiz de lectura desde jovenluke
MAC_raiz = ""

raiz = PC_raiz

#os.chdir(raiz)

nameDatasetsInfo = "DatasetsInfo.xlsx"

# namefile=raiz+nameDatasetsInfo
# df_DI = pd.read_excel(namefile)

# =============================================================================
# Sirve para localizar un valor de una columna de un dataset (es más sencillo que pelearse con los loc y tal de Python)
# devuelve de un dataset ABIERTO o NO ABIERTO, las columnas para un index que debe coincidir con un valor. Si datasetName es distinto a "" significa que el dataset ya estará abierto
# en otro caso le mandamos el puntero al dataset
# EJEMPLO: items = getDataValue(df_out, "Item", "_export", "Dataset")
# devolverá el valor de la columna "Dataset" cuando en la columna "Item" se encuentre el valor "_export"
# =============================================================================
def _h_getDatasetValue( datasetName, dataset, index, value, columns):
    """
    Función _h_getDatasetValue - con esta función devuelvo un valor o conjunto de valores
    campos. Es un HELPER (función interna para aumentar la productividad)

    Args:
        datasetName: nombre de dataset (almacenado en allDatasetsByName). Si es vacío entiendo que se le envia el puntero al dataset abierto en el siguiente campo
        dataset: dataset ya abierto previamente
        index: qué columna ordena el dataset
        value: valor del index que queremos que coincida
        column: nombre/s de la/s columna/s que queremos devolver

    Returns:
        Valor o conjunto de valores del dataset que cumplen la restricción.
    """

    if datasetName != "":
        # 1) Decimos cuál es el orden del dataset
        try:
            data = allDatasetsByName[datasetName]
        except:
            cadena = "\n\t_h_getDatasetValue:\tERROR - el dataset: {} no está en la lista allDatasetsByName.".format(
                dataset)
            _Debug(cadena)
            return False
    else:
        data = dataset
    # 2) Buscamos el valor que queremos
    # data.reset_index()
    # data.set_index(index, inplace=True) # centramos el index para ordenar el dataset

    items = data.loc[data[index]==value, columns]
    return items

# ---- ATTRIBUTES

# ---- LOAD ATT VALUES
# función encargada de leer la info que pueda haber en dataset para cargarla en el atributo correspondiente
# IMPORTANTE: El registro, caso de estar mapeado a database, ha de ser único (no puede devolver más de una línea)
# ejemplo: OPP ID que contiene OPP LINE ID. En ese caso la info de mapeado a dataset TIENE que estar al nivel de OPP LINE ID.
def _h_loadAttrs(item):
    for k,v in item.atts.items():
        att = item.getAttByTag(k)
        if att.tipo == STR_ATTR: # no hay que buscar la información en ningún sitio porque es de tipo "_attr"
            return False
        else:
            # vamos a leer en el dataset que nos dicen, el valor del atributo y lo colocamos como value
            df = allDatasetsByName[att.dataset]
            valor = list(df.loc[df.loc[:,item.datasetColumn] == item.name][att.datasetColumn]) # hay que direccionarlo así porque devuelve un SERIES (ojo que si devuelve más de uno entonces estaría devolviendo un DataFrame)
            att.value = valor[0]
            return True
    # for k,v in item.attsRelationships.items(): # ejecutamos la expresiones
    #     return False # ---- pendiente ejecución expresiones

# =============================================================================
# ---- FUNCTION. Cuerpo real de la función para crear un DF de un Item
# restricción - tiene que venir en formato RAW, es decir, que haya pasado por copyAttsExtended
# =============================================================================
def itemToDataFrame(itemDF):
    import numpy as np
    itemSource = itemDF
    columns = []
    data = []


    # cargamos las columnas del primer hijo
    for key,value in itemSource.cItems.items():
        itemChild = allItemsByName[key]
        # for k,v in itemChild.atts.items():
        #     # cojo el último split para ponerle el nombre de la columna, según Luis no hay conflictos
        #     nombreColumna = k.split(":")
        #     columns.append(nombreColumna[-1])
        for k in itemChild.atts:
            # cojo el último split para ponerle el nombre de la columna, según Luis no hay conflictos
            nombreColumna = k.split(":")
            columns.append(nombreColumna[-1])
        break


    #columns.append("name")
    for k,v in itemSource.cItems.items():
        item = allItemsByName[k]
        # if recursive == False:
        linea = []
        for k,v in item.atts.items():
            linea.append(v.value) # añado línea a línea para crear filas
        data.append(linea)

    df = pd.DataFrame(columns=columns, data=data) # ---- pendiente, no funciona

    return df


# =============================================================================
# Borrar items, atributos y estructuras
# =============================================================================
def eraseItems( item ):

    item.eraseChildren(delete=True)
    del allItemsByName[item.name]
    del item

    return True

# =============================================================================
# ---- FUNCTION. Crea una versión "Matriz" o "RAW" de un item y todos sus hijos, preparado para ser un dataframe
# =============================================================================
contador = 0
contadorAtributos = 0
profundidadAtributos = {}

def copyAttsExtended(itemTarget, itemSource, prefix_list = "", listOfAttsLocal = [], profundidadRama = 0):
    """


    Parameters
    ----------
    itemTarget : TYPE - item al que se agregará el primer nivel de hijos de itemSource (que actúa como contenedor)
        DESCRIPTION.
    itemSource : TYPE - item contenedor - se crean todos los atributos de su primera jerarquía de hijos y luego se crean tantos hijos como su primer nivel dentro de itemTarget
        DESCRIPTION.
    atts : TYPE, optional - ristra de atributos para crearlos al primer nivel
        DESCRIPTION. The default is "" erase = False.

    prefix_list : TYPE, optional - lista de prefijos para cada atributo, dependiendo del nivel de jerarquía dentro de itemSource, si no llega nada, se construye un nombre de atributo con el nombre de target
        DESCRIPTION. The default is "" erase = False.
    copyValue : TYPE, optional
        DESCRIPTION. The default is True. Se copian los valores originales o no.

    Returns
    -------
    None.

    """
    global contador, contadorAtributos
    global listOfAtts, profundidadAtributos # guardo cuántos atributos tiene por cada profundidad

    # CALCULAR LAS COLUMNAS NECESARIAS DE CADA ELEMENTO
    # por cada hijo de primer nivel de itemSource creamos un hijo en itemTarget que contendrá todos los atributos agregados de toda la jerarquía de ese hijo de itemSource
    # primero tenemos que ver que la estructura interna es coherente (todas las ramas tienen hijos y todos las ramas de hijos suman el mismo número de atributos)

    atributosQuitadosFlag = False

    count = 0
    atributosQuitados = 0
    ajustarAtributosConProfunidadRama = True # ajustamos atributos en función de la profundidad? sólo si el item que estamos mirando tiene atributos

    # rastreamos todos sus hijos
    for k,v in itemSource.cItems.items(): # creamos elementos de primer nivel
        thisItem = allItemsByName[k]
        cadena = f"Item {thisItem.name} : profundidadRama {profundidadRama}  atributos en Item {len(thisItem.atts)}"
        # print(f"Item {thisItem.name} : profundidadRama {profundidadRama}  atributos en Item {len(thisItem.atts)}")
        _Debug(cadena)


        # si el item no tiene atributos es que es un contenedor... es una lista que sólo contendrá diccionarios
        # en este caso no sumamos ni quitamos atributos, todo se mantiene
        if len(thisItem.atts) == 0:
            ajustarAtributosConProfunidadRama = False

        if ajustarAtributosConProfunidadRama == True:
            atributosActuales = len(listOfAttsLocal)
            # quito siempre los atributos añadidos en la anterior rama
            # tengo que vaciar tantos atributos de la lista local que me ha llegado como me dice la profundidadRama hasta el final
            # for n in range(profundidadRama, len(profundidadAtributos)-1):
            #     for l in range(0, profundidadAtributos[n]): # quito tantos atributos como ramas he "podado"
            #         atributosQuitadosFlag = True
            #         listOfAttsLocal.pop()
            # tengo que quitar atributos desde la rama hasta el final de la lista de atributos
            totalAtributos = len(listOfAttsLocal)
            atributosQueHanDeQuedar = 0
            # calculo cuántos tengo que dejar máximo. Suma de las ramas hasta la actual menos 1
            for n in range(0, profundidadRama-1):
                atributosQueHanDeQuedar += profundidadAtributos[n]
            atributosAQuitar = totalAtributos - atributosQueHanDeQuedar
            # tengo que hacer pop en la lista como la diferencia entre el totalAtributos y los atributosQueHanDeQuedar para que, al sumar los que corresponden, volvamos a tener la cantidad idónea
            for l in range(0, atributosAQuitar): # quito tantos atributos como necesito
                atributosQuitadosFlag = True
                listOfAttsLocal.pop()

            if atributosQuitadosFlag == True:
                atributosQuitados = len(listOfAttsLocal) - atributosActuales
                cadena = f"Quitamos desde profundidad rama {profundidadRama} hasta {len(profundidadAtributos)-1} atributos quitados {atributosQuitados}"
                _Debug(cadena)

            atributosQuitadosFlag = False
            atributosQueQuedan = len(listOfAttsLocal)

            for key, value in thisItem.atts.items():
                count += 1 # contamos los atributos de esta profundidad
                contadorAtributos += 1
                listOfAttsLocal.append(value)
            atributosAdded = len(listOfAttsLocal) - atributosQueQuedan
            cadena = f"Atributos antes de añadir {atributosActuales} Atributos quitados {atributosQuitados} Atributos añadidos {atributosAdded}"
            _Debug(cadena)

        ajustarAtributosConProfunidadRama = True # volvemos a dejarlo con el valor original


        profundidadAtributos[profundidadRama] = len(thisItem.atts) # meto cuántos atributos tiene esta lista
        count = 0


        if len(thisItem.cItems) == 0 and len(thisItem.atts) != 0: # si no tiene atributos y no tiene hijos es una lista vacía, con lo que no debemos crear un hijo...
            cadena = f" ---- Profundidad Rama {profundidadRama} Atributos {len(listOfAttsLocal)} profundidadAtributos {profundidadAtributos}"
            # print(f" ---- Profundidad Rama {profundidadRama} Atributos {len(listOfAttsLocal)} profundidadAtributos {profundidadAtributos}")
            _Debug(cadena)
            # de momento no usamos PREFIX
            nameFirstLevelItem = itemTarget.name + "_FL_{}".format(contador)
            itemFirstLevel = Item(nameFirstLevelItem)
            # copiamos todos los atributos a itemFirstLevel

            itemFirstLevel.addAttsFromDict(listOfAttsLocal)
            itemFirstLevel.setParent(itemTarget)

            contador += 1
            # cuidado, sólo tiene quitar elementos de la rama anterior
            contadorAtributos = 0
        else:
            copyAttsExtended(itemTarget, thisItem, prefix_list, listOfAttsLocal, profundidadRama + 1)

# # =============================================================================
# # ---- ITEM structure to DF
# Devuelve una estructura RAW de ITEM (una línea por cada hijo y todos sus atributos) y también en formato DF
# # =============================================================================
def itemStructureToDF(apiGroup, apiCall, itemRes, filename):
    itemTarget = Item(apiGroup+"-"+apiCall) # creo el elemento contenedor
    # itemSource = itemRes
    copyAttsExtended(itemTarget, itemRes, "") # creo un formato RAW de elementos
    df = itemToDataFrame(itemTarget) # lo convierto en DF
    #export_excel = df.to_excel(r'D:\OneDrive - Seachad\03 - Clientes\SEIDOR\IPCOSELL\azure.xlsx', index = None, header=True) # Don't forget to add '.xlsx' at the end of the path
    return itemTarget, df