#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 29 09:57:22 2021

@author: kat
"""

import cv2 as cv
import numpy as np

# =============================================================================
# FONCTION
# =============================================================================

def circle_inter(line_img,inter):
    cpt=0
    if inter is None:
        return
    for i in inter:
        line_img = cv.circle(line_img, i , radius=15, color=(0, 255, 255), thickness=2)
        line_img = cv.putText(line_img, str(cpt) , i, cv.FONT_HERSHEY_SIMPLEX , 2, color=(0,0,0), thickness=3)
        cpt+=1


def line_inter(line_img,sensibilite=200,space_lines=0.1,space_point=5):

    gray = cv.cvtColor(line_img,cv.COLOR_BGR2GRAY)
    edges = cv.Canny(gray,50,150,apertureSize = 3)
    lines = cv.HoughLines(edges,1,np.pi/180,sensibilite)
    if lines is None:
        return []
    lines_net = clean_line(line_img,lines,space_lines)
    inter = find_croisement(lines_net)
    for i in range ( len(lines_net) ):
        for rho,theta in lines_net[i]:
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a*rho
            y0 = b*rho
            x1 = int(x0 + 1000*(-b))
            y1 = int(y0 + 1000*(a))
            x2 = int(x0 - 1000*(-b))
            y2 = int(y0 - 1000*(a))
                # and (y0 <= 10):
            cv.line(line_img,(x1,y1),(x2,y2),(0,0,255),1)
    inter_net = clean_points(inter,space_point)
    return inter_net

def dist_eucli(x0,y0,x1,y1):
    """
    Calcul la distance euclidiènne entre deux points repérés avec des coordonnées cartésiennes

    Paramètres
    ----------
    x0 : float
        La coordonnée du premier point selon x
    y0 : float
        La coordonnée du premier point selon y
    x1 : float
        La coordonnée du second point selon x
    y1 : float
        La coordonnée du second point selon y

    Retour
    ------
    dist : float
        la distance euclidiènne entre les deux points
    """
    dx=x1-x0
    dy=y1-y0
    return(np.sqrt(dx**2+dy**2))

def clean_line(img, lines, th_btw_2_lines=0.1):
    """
    Supprime les lignes redondantes ou trop proche l'une de l'autre  en fonction d'un seuil
     ainsi que les lignes que l'on detecte au bord de l'image

    Paramètres
    ----------
    img : Matrix of int  n x m
        n lignes, m colonnes
        L'image dans laquelle on souhaite supprimer les ligne trouver ( necessaire pour enlever les lignes sur les bords )
    lines : Matrix of float n x 1 x 2
        n lignes,h
        Le tableau de ligne à nettoyer
    th_btw_2_lines : float
        Le seuil en pourcentage pour savoir si deux lignes peuvent être considéré comme appartenant au même objet

    Retour
    ------
    lines_net : Matrix of float n x 1 x 2
        Tableau de dimension inférieur ou égale à lines contenant uniquement les lignes "importantes"

    """
    lines_cpy= np.copy(lines)

    for i in range ( len(lines) ):

        for j in range ( len(lines) ):
            if (lines [j][0][0] == 0) :
                lines [j][0][0] == -1
            if (i!=j) and (lines[i][0][0] / lines[j][0][0] <= 1 + th_btw_2_lines ) and  (lines[i][0][0] / lines[j][0][0] >= 1 - th_btw_2_lines) :
                if ( (lines_cpy[j][0][0]!= -1) and (lines_cpy[i][0][0]!=-1) ):
                    lines_cpy[j][0][0]= -1


    lines_net=[i for i in lines_cpy if int(i[0][0]) != -1 and (int(i[0][0]) <=len(img[0])-5) ]
    return lines_net

def angle_dedans(angle, tab_angle, th_same_angle = 0.075):
    """
    Permet de savoir si un angle ( modulo pi ) se trouve dans un tableau d'angle

    Paramètres
    ----------
    angle : float
        L'angle dont l'on souhaite determiner la position
    tab_angle : list of float
        Le tableau contenant plusieurs angles
    th_same_angle : float
        Un seuil ( en radian ) pour definir si deux angles sont à peu près égaux

    Retour
    ------
    ret : bool
        True si l'élément est présent dans le tableau, False sinon


    """
    ret = False
    for i in tab_angle:
        if ( i % np.pi - (angle % np.pi) <= th_same_angle ) and ( i % np.pi - (angle% np.pi) >=  - th_same_angle) :
            ret = True
            return ret
        if ( i % np.pi - (angle % -np.pi) <= th_same_angle ) and ( i % np.pi - (angle % -np.pi) >=  - th_same_angle) :
            ret = True
            return ret
    return ret


def arg_angle(angle, tab_angle, th_same_angle=0.075):
    """
    Permet de retrouver la première postion d'un angle dans un tableau d'angle

    Paramètres
    ----------
    angle : float
        L'angle dont l'on souhaite determiner la position
    tab_angle : list of float
        Le tableau contenant plusieurs angles
    th_same_angle : float
        La valeur en radian pour déterminer si deux angles sont semblables

    Retour
    ------
    pos : int
        La position de l'élément trouvé, retourne -1 si il est absent du tableau

    """

    pos = -1

    for i in range (len(tab_angle)) :

        if (angle <= 0 + th_same_angle and angle >= 0 - th_same_angle and tab_angle[i] <= 0 + th_same_angle and tab_angle[i] >= 0 - th_same_angle ) :
            pos=i
            break
        elif ( tab_angle[i] % np.pi - (angle % np.pi) <= th_same_angle ) and ( tab_angle[i] % np.pi - (angle% np.pi) >=  - th_same_angle) :
            pos=i
            break
        elif ( tab_angle[i] % np.pi - (angle % -np.pi) <= th_same_angle ) and ( tab_angle[i] % np.pi - (angle% -np.pi) >=  - th_same_angle) :
            pos=i
            break
        else:
            # print( "probleme :", tab_angle[i], angle )
            a=1
        #     # print(pos)
    return(pos)


def pt_semblable(pt1,pt2,th_xy_pt=5):
    """
    Permet de determiner si deux points peuvent être considérer comme identique

    Paramètres
    ----------

    pt1 : tuple of float
        Les coordonnées cartésiennes du premier point sous forme d'un tuple ( dans un repère cartesien )
    pt2 : tuple of float
        Les coordonnées cartésiennes du second point également sous la forme d'un tuple ( dans un repère cartesien )
    th_xy_pt : float
        Un seuil sur x et y permettant de juger de la proximité entre les deux points

    Retour
    ------
    ret : Bool
        True si les points sont semblable, False sinon

    """
    ret = False
    if (pt1[0] >= pt2[0] - th_xy_pt and pt1[0] <= pt2[0] + th_xy_pt) and ( pt1[1] >= pt2[1] - th_xy_pt and pt1[1] <= pt2[1] + th_xy_pt) :
        ret = True
        return ret
    return ret

def clean_points(tab_pts, th_xy_pt=5):
    """
    Supprime les points trop proches entre eux en fonction d'un seuil

    Paramètres
    ----------
    tab_pts :  Matrix of int n x 2 ( codé sur 64 bits )
        n lignes,
        Le tableau de point à nettoyer
    th_xy_pt : float
        Un seuil sur x et y permettant de juger de la proximité entre les deux points

    Retour
    ------
    pts_net : Matrix of int n x 2 ( codé sur 64 bits )
        Tableau de dimension inférieur ou égale à tab_pts contenant uniquement les points non redondant

    """
    pt_cpy= np.copy(tab_pts)
    pts_net = []
    for i in range ( len(tab_pts) ):
        for j in range ( i+1, len(tab_pts) ) :

            if pt_semblable(tab_pts[i],tab_pts[j],th_xy_pt) or tab_pts[j][0] < 0 or tab_pts[j][1] < 0:
                pt_cpy[j][0] = -1
                pt_cpy[j][1] = -1

    pts_net=[i for i in pt_cpy if i[0] != -1 and i[1] != -1 and i[0] != np.nan and i[1] != np.nan ]
    return(pts_net)


def type_croisement(lines):
    """
    Permet de determiner le nombre de type de droites, c'est à dire le nombre de droites avec des coefficients directeur différents. Des droites
    appartenant au même type sont toutes parralèlle entre elles.
    Permet aussi de trier les droites dans une liste selon leurs coefficients directeurs

    Paramètres
    ----------
    lines :  Matrix n x 1 x 2
        n lignes,
        Le tableau de ligne dont on souhaite determine le type et que l'on souhaite trier

    Retour
    ------
    type_droite : Int
        Sa valeur est determiné en fonction du type de droite ( expliqué précédement ) présent dans lines\n
        type_droite = -1 --> Un ou aucun type de droites \n
        type_droite = 0 --> 2 types de droites horizontales et verticales\n
        type_droite = 1 --> 2 types de droites non horizontales et non verticales\n
        type_droite = 2 --> Plus de deux types de droites
    droites : List n x m
        n types de droites différentes
        m est le nombre de droites d'un certain type de droite
        droites est donc un tableau de droites trier en fonction de la pente des droites

    """

    first = lines[0][0][1]

    droites = []
    droites.append(first)
    for i in lines:
        if  not angle_dedans(i[0][1],droites, 0.1):
            droites.append(i[0][1])
            #une erreur peut se glisser au dessus
    if len(droites) != 2:
        type_droite = 2
        #print("Plus de deux types droites")

    elif len(droites) == 0 or len(droites) == 1 :
        type_droite = -1
        #print('Une ou aucune droite')

    else:
        if ( droites[0] % (np.pi/2) >= - 0.1 ) and (droites[1] % (np.pi/2) >= - 0.1) and ( droites[0] % (np.pi/2) <= 0.1 ) and (droites[1] % (np.pi/2) <=  0.1):
            type_droite = 0
            #print('Droite horizontale et verticale')

        else:
            type_droite = 1
            #print('Droite ni horizontale ni verticale')

    return(type_droite,droites)

def find_croisement(lines):
    """
    Trouve tout les croisements dans un ensemble de droite,

    Paramètres
    ----------
    lines :  Matrix of floats n x 1 x 2 ( codé sur 64 bits )
        n lignes,
        Le tableau de ligne dont on souhaite trouver les intersections.

    Retour
    ------
    inter : list of int tuples
        Tableau des points d'intersection des droites contenu dans lines
    """


    inter=[]

    type_droite, droites = type_croisement(lines)


# =============================================================================
#    Sépare en deux types de droite
# =============================================================================

    tab_of_types = [[] for i in range (len( droites ))]

    for i in range ( len(lines) ):
        pos = arg_angle(lines[i][0][1], droites, 0.1)
        tab_of_types[pos].append(lines[i][0])


# =============================================================================
#     Trouve les croisements
# =============================================================================

    if type_droite==0 :
        for i in range ( len(tab_of_types[1])  ):
            x0i= np.cos(tab_of_types[1][i][1]) * tab_of_types[1][i][0]
            y0i= np.sin(tab_of_types[1][i][1]) * tab_of_types[1][i][0]
            for j in range ( len(tab_of_types[0]) ):
                y0j= np.sin(tab_of_types[0][j][1]) * tab_of_types[0][j][0]
                inter.append(( round(x0i), round(y0i+y0j) ))


    elif (type_droite > 0)  :
        for i in range ( len(tab_of_types)  ):
            for j in range ( len(tab_of_types[i]) ):

               x0i= np.cos(tab_of_types[i][j][1]) * tab_of_types[i][j][0]
               y0i= np.sin(tab_of_types[i][j][1]) * tab_of_types[i][j][0]
               x1i = int(x0i - 100* np.sin(tab_of_types[i][j][1]) )
               y1i = int(y0i + 100* np.cos(tab_of_types[i][j][1]) )

               coef_dir_i = (y1i-y0i)/(x1i-x0i)
               ord_ori_i = y0i - coef_dir_i * x0i

               for k in range (i+1, len(tab_of_types) ):
                   for l in range ( len(tab_of_types[k]) ):
                        x0j= np.cos(tab_of_types[k][l][1]) * tab_of_types[k][l][0]
                        y0j= np.sin(tab_of_types[k][l][1]) * tab_of_types[k][l][0]

                        x1j = int(x0j + 100 * np.sin(tab_of_types[k][l][1]) )
                        y1j = int(y0j - 100 * np.cos(tab_of_types[k][l][1]) )

                        coef_dir_j = (y1j-y0j)/(x1j-x0j)
                        ord_ori_j = y0j - coef_dir_j * x0j

                        inter_x = (ord_ori_j - ord_ori_i ) /  ( coef_dir_i - coef_dir_j)
                        inter_y = coef_dir_i * inter_x + ord_ori_i

                        #on ne prends pas les points qui sont trop loins (intersection == nan)
                        if (not np.isnan(inter_x)) and (not np.isnan(inter_y)):
                            inter.append(   (round(inter_x), round(inter_y))   )
    else:
        print('erreur')

    return(inter)
        #
