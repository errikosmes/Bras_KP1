# Imports
import logging, sys, traceback
from niryo_one_tcp_client import *
from niryo_one_camera import *
import cv2 as cv
import numpy as np
from time import sleep
from API.croisement import *
from API.draw_rectangle import *
from API.workspace_referential import *
from API.workshop_processing import *
from PyQt5.QtCore import QMutex, QObject, QThread, pyqtSignal, QReadWriteLock
from PyQt5 import QtCore, QtGui, QtWidgets

sensibilite = 200
space_lines = 5
space_point = 5
execute = False
capture = False
client = None

lock = QReadWriteLock()
mlock = QMutex()

# Inits
# Set robot address
#robot_ip_address = None
robot_ip_address = "10.10.10.10"
# robot_ip_address = "169.254.200.200"

#init logging
logging.basicConfig(format="%(message)s", level=logging.INFO)

tool_used = RobotTool.GRIPPER_2

# Définition des Workspaces
wkshop = "Workshop_v2"
dwks = "default_workspace"  # Robot's placing Workspace Name

# POS observation workshop
observation_pose_wkshop = PoseObject(
    x=-0.00, y=-0.21, z=0.24,
    roll=1.47, pitch=1.46, yaw=-0.22,
)

# POS observation Packing AREA
observation_pose_dwks = PoseObject(
    x=0.2, y=0.0, z=0.34,
    roll=0, pitch=1.57, yaw=-0.2,
)

# Position de repos
sleep_joints = [-1.6, 0.152, -1.3, 0.1, 0.01, 0.04]


def main_thread(client):
    global sensibilite
    global space_lines
    global space_point
    global robot_ip_address

    def stream_init(client, observation_pose, workspace_ratio=1.0):

         # Getting calibration param
        _, mtx, dist = client.get_calibration_object()
        # Moving to observation pose
        client.move_pose(*observation_pose.to_list())
        sleep(1)
        while "workspace_not_found" :

            # Getting image
            status, img_compressed = client.get_img_compressed()
            if status is not True:
                print("[ERROR] error with Niryo One's service")
                break

            img_raw = uncompress_image(img_compressed) # Uncompressing image
            img_undistort = undistort_image(img_raw, mtx, dist) # Undistorting
            workspace_found, res_img_markers = debug_markers(img_undistort) # Trying to find markers

            # Trying to extract workspace if possible
            if workspace_found: img_workspace = extract_img_workspace(img_undistort, workspace_ratio=workspace_ratio)
            else: img_workspace = None

            # - Display
            # Concatenating raw image and undistorted image
            concat_ims = concat_imgs((img_raw, img_undistort))

            # Concatenating extracted workspace with markers annotation
            if img_workspace is not None: res_img_markers = concat_imgs((res_img_markers, resize_img(img_workspace, height=res_img_markers.shape[0])))

            # Showing images
            # show_img("Images raw & undistorted", concat_ims, wait_ms=0)

            return img_workspace, res_img_markers

    def select_and_pick(client,tab_pose) :
        global execute
        global capture

        while True:
            img_workspace, res_img_markers = stream_init(client, observation_pose_dwks)

            if img_workspace is not None:
                line_img = resize_img(img_workspace, height=res_img_markers.shape[0])

                break
            else:
                line_img=None


        POI = line_inter(line_img,400-sensibilite,space_lines/100,space_point) #Points Of Interest
 #Points Of Interest
        POISelected = []
        clickCoord = [0, 0]
        regionSize = 30

        show_img('Workspace', line_img, wait_ms=10)
        cv2.setMouseCallback('Workspace', selectRectCallback, param=[POI, POISelected, regionSize])
        imgCached = line_img.copy()

        lock.lockForRead()
        capt = capture
        not_quit_n_not_exec =  not(execute)
        lock.unlock()

        continue_capture = True

        while not_quit_n_not_exec:
            #texte
            bottomLeftCornerOfText = (10,30)
            if (len(tab_pose)>len(POISelected)) :
                cv2.putText(line_img,'Encore '+ str(len(tab_pose)-len(POISelected))+ ' a selectionner', bottomLeftCornerOfText, cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,255),2)
            elif (len(tab_pose)<len(POISelected)) :
                cv2.putText(line_img,str(len(POISelected)-len(tab_pose))+' points selectionne en trop !', bottomLeftCornerOfText, cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,255),2)
            else :
                cv2.putText(line_img,'ok', bottomLeftCornerOfText, cv2.FONT_HERSHEY_SIMPLEX, 1,(0,255,0),2)
            #fin texte

            # draw region of interest rectangles
            for point in POI:
                point=tuple(point)
                if point in POISelected: drawSelected(line_img, point, regionSize, POISelected.index(point))
                else: drawUnselected(line_img,point,regionSize)

            key = show_img('Workspace', line_img)
            line_img = imgCached.copy()

            if ((key in [27, ord('\n'), ord('\r'), ord("q")]) and (len(tab_pose) is len(POISelected))):  # Will break loop if the user press Escape or Q
                break
            lock.lockForRead()
            not_quit_n_not_exec =  not(execute)

            capt = capture
            lock.unlock()
            if capt :
                mlock.lock()
                capture = False
                mlock.unlock()
                continue_capture = True
                return continue_capture
            else:
                continue_capture = False

        # # PICK FROM POISelected
        pick_from_POIselected(POISelected,tab_pose)

        return continue_capture

    def pick_from_POIselected(POISelected, tab_pose):
        if len(POISelected) > len(tab_pose):
            print("[ERROR] Point de placement supérieur au nombre d'objet")

        else:
            cpt=0
            for point in POISelected:
                point=tuple(point)
                inter_1_x, inter_1_y= change_space(point[1],point[0],0.01,0) #revoir les offsets ?
                place_pose_object = PoseObject(x=inter_1_x, y=inter_1_y, z=0.135,roll=-2.70, pitch=1.57, yaw=-2.7)
                try:
                    if(tab_pose[cpt][0].z < 0.12):
                        #print(tab_pose[cpt][0])
                        print('[ERROR] ATTENTION z is to small!')
                        break
                    client.pick_from_pose(*tab_pose[cpt][0].to_list()) # pick from workshop
                except:
                    print(traceback.format_exc())
                    print('[ERROR] More objects selected than placement selected')
                    break
                client.place_from_pose(*place_pose_object.to_list())
                cpt+=1

    def find_target(niryo_one_client, image):
        '''renvoie False False si le bouton "Capture a été actionné'''
        global capture

        tab_pose_bc, bc = get_obj_pose(niryo_one_client, wkshop, image)

        POI = bc #Points Of Interest
        POISelected = []
        clickCoord = [0, 0]
        regionSize = 30

        show_img('Workspace 2', image, wait_ms=10)
        cv2.setMouseCallback('Workspace 2', selectRectCallback, param=[POI, POISelected, regionSize])
        imgCached = image.copy()

        while True:
            # draw region of interest rectangles
            for point in POI:
                point=tuple(point)
                if point in POISelected:
                    drawSelected(image, point, regionSize, POISelected.index(point))
                else:
                    drawUnselected(image,point,regionSize)

            key = show_img('Workspace 2', image)
            image = imgCached.copy()

            lock.lockForRead()
            capt = capture
            lock.unlock()

            if capt :
                mlock.lock()
                capture = False
                mlock.unlock()
                return False, False

            if key in [27, ord('\n'), ord('\r'), ord("q")]:  # Will break loop if the user press Escape or Q
                break

        tab_pose=[]
        for obj_selected in POISelected:
            if obj_selected in bc:
                tab_pose.append(tab_pose_bc[bc.index(obj_selected)][0])

        return tab_pose, len(POISelected)

    def workshop_stream(niryo_one_client):
        global capture
        #mise a zéro du bouton Capture :
        mlock.lock()
        capture = False
        mlock.unlock()

        while True:
            img_workspace, res_img_markers = stream_init(niryo_one_client, observation_pose_wkshop, 1.5)
            # On recherche les cibles à déplacer
            if img_workspace is not None:
                sleep(1)
                tab_pose, nb_obj_selected = find_target(niryo_one_client, resize_img(img_workspace, height=res_img_markers.shape[0]))
                if tab_pose == False and nb_obj_selected == False :
                    continue #reboucle car le bouton Capture a été actionné
                return tab_pose, nb_obj_selected

    def main_select_pick2(client):
        global capture
        nb_obj_select = -1
        lg_tab_pose=0
        while nb_obj_select != lg_tab_pose:

            tab_pose, nb_obj_select = workshop_stream(client)
            lg_tab_pose = len(tab_pose)



            #mise a zéro du bouton Capture :
            mlock.lock()
            capture = False
            mlock.unlock()
            continue_capture = True
            while continue_capture:
                continue_capture = select_and_pick(client,tab_pose)


            if nb_obj_select != lg_tab_pose:
                ans = input("Shop is not empty, do you want to pick other object ? (y/n)")
                if ans=='n':
                    break
            else:
                break

        cv.destroyAllWindows()
        client.move_joints(*sleep_joints)
        client.set_learning_mode(True)

    main_select_pick2(client)

class Ui_MainWindow(object):

    def setupUi(self, MainWindow):

        ###################### AJOUT ! ######################
        # garder les lignes suivantes lors de la réécriture de l'interface !
        app.aboutToQuit.connect(self.closeEvent) #connect le bouton X à "closeEvent"
        #####################################################

        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(421, 400)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.sensib_slider = QtWidgets.QSlider(self.centralwidget)
        self.sensib_slider.setGeometry(QtCore.QRect(20, 60, 361, 16))
        self.sensib_slider.setMaximum(400)
        self.sensib_slider.setProperty("value", sensibilite)
        self.sensib_slider.setOrientation(QtCore.Qt.Horizontal)
        self.sensib_slider.setObjectName("sensib_slider")
        self.lcd_sensib = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcd_sensib.setGeometry(QtCore.QRect(315, 30, 64, 23))
        self.lcd_sensib.setSmallDecimalPoint(False)
        self.lcd_sensib.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcd_sensib.setProperty("value", sensibilite)
        self.lcd_sensib.setObjectName("lcd_sensib")
        self.Capture = QtWidgets.QPushButton(self.centralwidget)
        self.Capture.setGeometry(QtCore.QRect(160, 210, 100, 35))
        self.Capture.setObjectName("Capture")
        self.label_sensib = QtWidgets.QLabel(self.centralwidget)
        #self.label_sensib.setGeometry(QtCore.QRect(70, 30, 71, 17))
        self.label_sensib.setGeometry(QtCore.QRect(20, 30, 71, 17))
        self.label_sensib.setObjectName("label_sensib")
        self.espace_lignes_slider = QtWidgets.QSlider(self.centralwidget)
        self.espace_lignes_slider.setGeometry(QtCore.QRect(20, 120, 361, 16))
        self.espace_lignes_slider.setMaximum(20)
        self.espace_lignes_slider.setProperty("value", space_lines)
        self.espace_lignes_slider.setOrientation(QtCore.Qt.Horizontal)
        self.espace_lignes_slider.setObjectName("espace_lignes_slider")
        self.lcd_espace_lignes = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcd_espace_lignes.setGeometry(QtCore.QRect(315, 90, 64, 23))
        self.lcd_espace_lignes.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcd_espace_lignes.setProperty("value", space_lines)
        self.lcd_espace_lignes.setObjectName("lcd_espace_lignes")
        self.label_espace_ligne = QtWidgets.QLabel(self.centralwidget)
        self.label_espace_ligne.setGeometry(QtCore.QRect(20, 90, 181, 20))
        self.label_espace_ligne.setObjectName("label_espace_ligne")
        self.espace_inter_slider = QtWidgets.QSlider(self.centralwidget)
        self.espace_inter_slider.setGeometry(QtCore.QRect(20, 180, 361, 16))
        self.espace_inter_slider.setMaximum(20)
        self.espace_inter_slider.setProperty("value", space_point)
        self.espace_inter_slider.setOrientation(QtCore.Qt.Horizontal)
        self.espace_inter_slider.setObjectName("espace_inter_slider")
        self.label_espace_inter = QtWidgets.QLabel(self.centralwidget)
        self.label_espace_inter.setGeometry(QtCore.QRect(20, 140, 331, 31))
        self.label_espace_inter.setObjectName("label_espace_inter")
        self.lcd_espace_inter = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcd_espace_inter.setGeometry(QtCore.QRect(315, 140, 64, 23))
        self.lcd_espace_inter.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcd_espace_inter.setProperty("value", space_point)
        self.lcd_espace_inter.setObjectName("lcd_espace_inter")
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(204, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(204, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(190, 190, 190))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(204, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)

        #IP part
        self.lineEdit_ip = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_ip.setGeometry(QtCore.QRect(150, 270, 161, 25))
        self.lineEdit_ip.setObjectName("lineEdit_ip")
        self.label_adresse_ip = QtWidgets.QLabel(self.centralwidget)
        self.label_adresse_ip.setGeometry(QtCore.QRect(50, 270, 121, 31))
        self.label_adresse_ip.setObjectName("label_adresse_ip")
        self.connect_button = QtWidgets.QPushButton(self.centralwidget)
        self.connect_button.setGeometry(QtCore.QRect(110, 320, 91, 41))
        self.connect_button.setObjectName("connect_button")

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 421, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.sensib_slider.sliderMoved['int'].connect(self.lcd_sensib.display)
        self.espace_lignes_slider.sliderMoved['int'].connect(self.lcd_espace_lignes.display)
        self.espace_inter_slider.sliderMoved['int'].connect(self.lcd_espace_inter.display)
         ###################### AJOUT ! #################
        # garder les lignes suivantes lors de la réécriture de l'interface !

        self.sensib_slider.sliderMoved['int'].connect(self.set_sensib)
        self.espace_lignes_slider.sliderMoved['int'].connect(self.set_space_lines)
        self.espace_inter_slider.sliderMoved['int'].connect(self.set_space_point)
        self.Capture.clicked.connect(self.set_capture)

        #ip part
        self.connect_button.clicked.connect(self.set_connection)

        #connection de signaux
        ###########################################"####"#

        QtCore.QMetaObject.connectSlotsByName(MainWindow)


    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.Capture.setText(_translate("MainWindow", "Capture"))
        self.label_sensib.setText(_translate("MainWindow", "Sensibilité"))
        self.label_espace_ligne.setText(_translate("MainWindow", "Espace entre deux lignes"))
        self.label_espace_inter.setText(_translate("MainWindow", "Espacement minimum entre deux intersections"))

        #IP part :
        self.lineEdit_ip.setText(_translate("MainWindow", robot_ip_address))
        self.label_adresse_ip.setText(_translate("MainWindow", "Adresse IP  : "))
        self.connect_button.setText(_translate("MainWindow", "Connect"))

    def closeEvent(self) :
        ''' call when the X button is clicked '''
        global client
        if (client == None) : # if the client is not define
            return
        else :
            client.move_joints(*sleep_joints)
            client.set_learning_mode(True)

    def set_sensib(self,entier) :
        global sensibilite
        lock.lockForWrite()
        sensibilite=entier
        lock.unlock()

    def set_space_lines(self,entier) :
        global space_lines
        lock.lockForWrite()
        space_lines=entier
        lock.unlock()

    def set_space_point(self,entier) :
        global space_point
        lock.lockForWrite()
        space_point=entier
        lock.unlock()

    def set_execute (self) :
        global execute
        lock.lockForWrite()
        execute=True
        lock.unlock()

    def set_capture (self) :
        global capture
        mlock.lock()
        capture=True
        mlock.unlock()

    def set_connection (self) :
        global robot_ip_address
        robot_ip_address = self.lineEdit_ip.text()
        print (robot_ip_address)
        self.creat_n_run_thread() #Élancement du thread

    def creat_n_run_thread(self) :
        self.thread = QThread()
        self.robot_opencv = robot_opencv()
        self.robot_opencv.moveToThread(self.thread)

        #connections
        self.thread.started.connect(self.robot_opencv.run)

        #start
        self.thread.start()


class robot_opencv(QObject):

    def run (self) :
        """ tache du robot et opencv """
        global client


        # Connect to robot
        client = NiryoOneClient()
        client.connect(robot_ip_address)
        # Calibrate robot if robot needs calibration
        client.calibrate(CalibrateMode.AUTO)
        client.change_tool(tool_used)
        #programme principal
        try :
            main_thread(client)

        except Exception as e:
            logging.info(traceback.format_exc())
            client.move_joints(*sleep_joints)
            client.set_learning_mode(True)
            logging.info("erreur")

        client.move_joints(*sleep_joints)
        client.set_learning_mode(True)
        # Releasing connection
        client.quit()
        client = None

if __name__ == '__main__' :
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
