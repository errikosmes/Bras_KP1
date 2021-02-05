# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 11:21:01 2021

@author: borde
"""

def change_space(px_x,px_y,offset_x=0,offset_y=0):
    lg_x = 0.178
    lg_y = 0.188
    size_img = 480
    
    xi = px_x*(lg_x/size_img)
    yi = px_y*(lg_y/size_img)
    
    x0 = 0.163
    y0=-0.093
        
    x=xi+x0+offset_x
    y=yi+y0+offset_x
    
    return x,y