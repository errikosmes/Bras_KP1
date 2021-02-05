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


def line_inter(line_img):
                
    gray = cv.cvtColor(line_img,cv.COLOR_BGR2GRAY)
    edges = cv.Canny(gray,50,150,apertureSize = 3)
    lines = cv.HoughLines(edges,1,np.pi/180,200)
    if lines is None:
        return None
    lines_net = clean_line(line_img,lines)
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
    
    return inter


def dist_eucli(x0,y0,x1,y1):
    dx=x1-x0
    dy=y1-y0
    return(np.sqrt(dx**2+dy**2))
    
def clean_line(img, lines): 
    lines_cpy= np.copy(lines)

    for i in range ( len(lines) ):
        for j in range ( len(lines) ):
            if (i!=j) and (lines[i][0][0] / lines[j][0][0] <= 1.1) and  (lines[i][0][0] / lines[j][0][0] >= 0.9) : 
                if ( (lines_cpy[j][0][0]!= 0) and ( lines_cpy[i][0][0]!=0) ): 
                    lines_cpy[j][0][0]= 0

       
    lines_net=[i for i in lines_cpy if int(i[0][0]) != 0 and (int(i[0][0]) <=len(img[0])-5) ]
    return lines_net


def type_croisement(lines):
    first = lines[0][0][1]
    droites = []
    droites.append(first)
    for i in lines:
        if  not angle_dedans(i[0][1],droites):
            droites.append(i[0][1])
            #une erreur peut se glisser au dessus
    if len(droites) != 2:
        type_droite = 2
        print("Plus de deux types droites")

    
    else:
        if ( droites[0] % (np.pi/2) >= -0.1 ) and (droites[1] % (np.pi/2) >= -0.1) and ( droites[0] % (np.pi/2) <= 0.1 ) and (droites[1] % (np.pi/2) <= 0.1):
            type_droite = 0
            print('Droite horizontale et verticale')
            
        else:
            type_droite = 1
            print('Droite ni horizontale ni verticale')
    
    return(type_droite,droites)

# type_droite = 0 -> droite horizontale, verticale
# type_droite = 1 -> droite non horizontale, non verticale
# type_droite = 2 -> Plus de deux types de droite

def angle_dedans(angle,tab):
    for i in tab:
        if ( angle % np.pi <= (i % np.pi) + 0.1 ) and ( angle % np.pi >= (i % np.pi) - 0.1 ) :
            return True
        
    return False


def find_croisement(lines):
    horiz =[]
    vert = []
    inter=[]
    
    type_droite, droites = type_croisement(lines) 
    
# =============================================================================
#    Sépare en deu types de droite
# =============================================================================

    if type_droite != 2:
        for i in lines:
            if i[0][1] < droites[1] + 0.1 and i[0][1] > droites[1]-0.1:
                vert.append(i)
            elif i[0][1] < droites[0] + 0.1 and i[0][1]  > droites[0] - 0.1 :
                horiz.append(i)
            else:
                print("erreur inconnu")
                
            
# =============================================================================
#     Trouve les croisements 
# =============================================================================
            
            
    if type_droite==0 :       
        for i in range ( len(horiz)  ):
            x0i= np.cos(horiz[i][0][1]) * horiz[i][0][0] 
            y0i= np.sin(horiz[i][0][1]) * horiz[i][0][0]
            for j in range ( len(vert) ):
                y0j= np.sin(vert[j][0][1]) * vert[j][0][0]
                inter.append(( round(x0i), round(y0i+y0j) ))
    
    

    if type_droite == 1 : 
        for i in range ( len(vert)  ):
           x0i= np.cos(vert[i][0][1]) * vert[i][0][0] 
           y0i= np.sin(vert[i][0][1]) * vert[i][0][0]
           x1i = int(x0i - 100* np.sin(vert[i][0][1]) )
           y1i = int(y0i + 100* np.cos(vert[i][0][1]) )
           
           coef_dir_i = (y1i-y0i)/(x1i-x0i)
           ord_ori_i = y0i - coef_dir_i * x0i

               
           for j in range ( len(horiz) ):
               x0j= np.cos(horiz[j][0][1]) * horiz[j][0][0]
               y0j= np.sin(horiz[j][0][1]) * horiz[j][0][0]
               x1j = int(x0j + 100 * np.sin(horiz[j][0][1]) )
               y1j = int(y0j - 100 * np.cos(horiz[j][0][1]) )
               
               coef_dir_j = (y1j-y0j)/(x1j-x0j)
               ord_ori_j = y0j - coef_dir_j * x0j
               
               inter_x = (ord_ori_j - ord_ori_i ) /  ( coef_dir_i - coef_dir_j)
               inter_y = coef_dir_i * inter_x + ord_ori_i
               

               inter.append(   (round(inter_x), round(inter_y))   )
               # inter.append(   (round(x1j), round(y1j))   )
               
    print('\ninter',inter)
    print('droites',droites)
    print('\nLEN x',len(horiz))
    print('LEN y',len(vert))
    return(inter)
