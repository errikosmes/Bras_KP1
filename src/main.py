# Imports
import logging, sys, traceback
from niryo_one_tcp_client import *
from niryo_one_camera import *
import cv2 as cv
import numpy as np
from time import sleep
from API.cross_finder import *
from API.draw_rectangle import *
from API.workspace_referential import *
from API.workshop_processing import *
from PyQt5.QtCore import QMutex, QObject, QThread, pyqtSignal, QReadWriteLock
from PyQt5 import QtCore, QtGui, QtWidgets

sensibilite = 200
space_lines = 5
space_point = 5
capture = False
client = None

lock = QReadWriteLock()
mlock = QMutex()

# Inits
# Set robot address
robot_ip_address = "10.10.10.10" #adresse ip "d'origine"
# robot_ip_address = "169.254.200.200"

#init logging
logging.basicConfig(format="%(message)s", level=logging.INFO)

#griiper used on the arm
tool_used = RobotTool.GRIPPER_2

# Workspaces' definition (set with niryonestudio)
wkshop = "Workshop_v2"
dwks = "default_workspace"  # Robot's placing Workspace Name

# POS observation workshop (Obs workshop v5)
observation_pose_wkshop = PoseObject(
    x=-0.0002, y=-0.199, z=0.262,
    roll=-0.504, pitch=1.553, yaw=-2.078,
)

# POS observation Packing AREA
observation_pose_dwks = PoseObject(
    x=0.143, y=-0.004, z=0.287,
    roll=-0.086, pitch=1.395, yaw=-0.275,
)

# Position de repos
sleep_joints = [-1.6, 0.152, -1.3, 0.1, 0.01, 0.04]


def main_thread(client):
    """
    fonction executed by the thread to control the arm, do the vision analyse,
    and open the 2 opencv windows
    """

    # global variable to catch the value of sliders of GUI and robot ip adress
    global sensibilite
    global space_lines
    global space_point
    global robot_ip_address

    def stream_init(client, observation_pose, workspace_ratio=1.0):
        """
        put the arm on the position observation_pose, and try to extract a workspace
        with the camera. If no workspace foud, try continuously, if a workspace is found,
        return the image of the workspace  :  img_workspace, and the image with the detection
        of markers : res_img_markers
        """

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

            # Concatenating extracted workspace with markers annotation
            if img_workspace is not None: res_img_markers = concat_imgs((res_img_markers, resize_img(img_workspace, height=res_img_markers.shape[0])))

            return img_workspace, res_img_markers

    def select_and_pick(client,tab_pose) :
        """ fonction used by the thread to show the image of the workspace default_workspace,
        and propose to the user the intersections whee the objects could be placed
        If the user clicled on "enter" or "q", the arm execute the movements
        If the button capture was clicked, the function return True, and no movements was executed
        """

        # global variable link to the button capture on the GUI
        global capture

        while True:
            img_workspace, res_img_markers = stream_init(client, observation_pose_dwks) # catch the workspace

            if img_workspace is not None: # check if the workspace is find
                line_img = resize_img(img_workspace, height=res_img_markers.shape[0])
                break # exit the while loop
            else:
                line_img=None

        # catch the values of sliders :
        lock.lockForRead()
        sensibilite_lock=sensibilite
        space_lines_lock=space_lines
        space_point_lock=space_point
        lock.unlock()

        # POI : Point of interest :
        # catch the intersections find on the image with the parameters puted
        # on the sliders
        POI = line_inter(line_img,350-sensibilite_lock,space_lines_lock/100,space_point_lock)
        #Points Of Interest
        POISelected = []
        clickCoord = [0, 0]
        regionSize = 30

        show_img('Workspace', line_img, wait_ms=10)
        cv2.setMouseCallback('Workspace', selectRectCallback, param=[POI, POISelected, regionSize])
        imgCached = line_img.copy() # imgcached = image without rectangle or texte


        while True :
            # put text to say to the user if The number of points selected is too
            #  high , too low, or ok
            bottomLeftCornerOfText = (10,30)
            if (len(tab_pose)>len(POISelected)) :
                cv2.putText(line_img,str(len(tab_pose)-len(POISelected))+ ' left to pick', bottomLeftCornerOfText, cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,255),2)
            elif (len(tab_pose)<len(POISelected)) :
                cv2.putText(line_img,str(len(POISelected)-len(tab_pose))+' excess points picked!', bottomLeftCornerOfText, cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,255),2)
            else :
                cv2.putText(line_img,'ok - Press Enter', bottomLeftCornerOfText, cv2.FONT_HERSHEY_SIMPLEX, 1,(0,255,0),2)


            # draw region of interest rectangles
            for point in POI:
                point=tuple(point)
                if point in POISelected: drawSelected(line_img, point, regionSize, POISelected.index(point))
                else: drawUnselected(line_img,point,regionSize)

            key = show_img('Workspace', line_img)
            line_img = imgCached.copy() # reload image cached in line_img (without rectangle and text)

            # if enter is pressed and the godd number  of POI is selected : break the loop
            if ((key in [27, ord('\n'), ord('\r'), ord("q")]) and (len(tab_pose) is len(POISelected))):  # Will break loop if the user press Escape or Q
                break

            # catch the value of global variable capture
            lock.lockForRead()
            capt = capture
            lock.unlock()

            # check if the button was clicked
            if capt :  # if capture was clicked
                mlock.lock()
                capture = False
                mlock.unlock()
                return True # return True (a new capture must be take)

        # # PICK FROM POISelected
        pick_from_POIselected(POISelected,tab_pose) # execution of the movements by the arm

        return False # no needs of a new capture, the movemnts were executed

    def pick_from_POIselected(POISelected, tab_pose):
        """
        Pick and place the selected objects
        """
        if len(POISelected) > len(tab_pose):
            print("[ERROR] Placement point greater than number of object")

        else:
            cpt=0
            for point in POISelected:
                point=tuple(point)
                inter_1_x, inter_1_y= change_space(point[1],point[0],0.01,0) #revoir les offsets ?
                place_pose_object = PoseObject(x=inter_1_x, y=inter_1_y, z=0.135,roll=-2.70, pitch=1.57, yaw=-2.7)
                try:
                    if(tab_pose[cpt][0].z < 0.12):
                        #print(tab_pose[cpt][0])
                        print('[ERROR] z is to small!')
                        break
                    client.pick_from_pose(*tab_pose[cpt][0].to_list()) # pick from workshop
                except:
                    print(traceback.format_exc())
                    print('[ERROR] More objects selected than placement selected')
                    break
                client.place_from_pose(*place_pose_object.to_list())
                cpt+=1

    def find_target(niryo_one_client, image):
        '''Return False if  "Capture clicked'''
        global capture

        tab_pose_bc, bc, preds = get_obj_pose(niryo_one_client, wkshop, image)
        np_preds = [item for sublist in preds for item in sublist]

        POI = bc #Points Of Interest
        POISelected = []
        clickCoord = [0, 0]
        regionSize = 30

        bottomLeftCornerOfText = (60,30)
        if len(bc) == 0:
            cv2.putText(image,'Shop is empty ! Add objects and click CAPTURE or press ENTER to quit', bottomLeftCornerOfText, cv2.FONT_HERSHEY_SIMPLEX, 0.5,(0,0,255),2)
        else:
            writeNames(image, preds, regionSize)

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
            try:
                if obj_selected in np_preds:
                    name_obj_selected = np_preds[np_preds.index(obj_selected)-1]

            except:
                print('Object not recognized !')
                continue

        return tab_pose, len(POISelected)

    def workshop_stream(niryo_one_client):
        """
        Initiate the video stream, find the objects to pick and place and let the user choose which ones to take
        """
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
                if tab_pose == False and nb_obj_selected == False:
                    continue #reboucle car le bouton Capture a été actionné
                return tab_pose, nb_obj_selected

    def main_select_pick2(client):
        """
        A wrapper for select and pick
        """
        global capture
        nb_obj_select = -1
        lg_tab_pose = 0
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
        self.sensib_slider.setEnabled(False)
        self.sensib_slider.setGeometry(QtCore.QRect(20, 60, 361, 16))
        self.sensib_slider.setMaximum(350)
        self.sensib_slider.setProperty("value", sensibilite)
        self.sensib_slider.setOrientation(QtCore.Qt.Horizontal)
        self.sensib_slider.setObjectName("sensib_slider")

        self.lcd_sensib = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcd_sensib.setEnabled(False)
        self.lcd_sensib.setGeometry(QtCore.QRect(315, 30, 64, 23))
        self.lcd_sensib.setSmallDecimalPoint(False)
        self.lcd_sensib.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcd_sensib.setProperty("value", sensibilite)
        self.lcd_sensib.setObjectName("lcd_sensib")

        self.Capture = QtWidgets.QPushButton(self.centralwidget)
        self.Capture.setEnabled(False)
        self.Capture.setGeometry(QtCore.QRect(160, 210, 100, 35))
        self.Capture.setObjectName("Capture")

        self.label_sensib = QtWidgets.QLabel(self.centralwidget)
        self.label_sensib.setEnabled(False)
        #self.label_sensib.setGeometry(QtCore.QRect(70, 30, 71, 17))
        self.label_sensib.setGeometry(QtCore.QRect(20, 30, 71, 17))
        self.label_sensib.setObjectName("label_sensib")

        self.espace_lignes_slider = QtWidgets.QSlider(self.centralwidget)
        self.espace_lignes_slider.setEnabled(False)
        self.espace_lignes_slider.setGeometry(QtCore.QRect(20, 120, 361, 16))
        self.espace_lignes_slider.setMaximum(20)
        self.espace_lignes_slider.setProperty("value", space_lines)
        self.espace_lignes_slider.setOrientation(QtCore.Qt.Horizontal)
        self.espace_lignes_slider.setObjectName("espace_lignes_slider")

        self.lcd_espace_lignes = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcd_espace_lignes.setEnabled(False)
        self.lcd_espace_lignes.setGeometry(QtCore.QRect(315, 90, 64, 23))
        self.lcd_espace_lignes.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcd_espace_lignes.setProperty("value", space_lines)
        self.lcd_espace_lignes.setObjectName("lcd_espace_lignes")

        self.label_espace_ligne = QtWidgets.QLabel(self.centralwidget)
        self.label_espace_ligne.setEnabled(False)
        self.label_espace_ligne.setGeometry(QtCore.QRect(20, 90, 181, 20))
        self.label_espace_ligne.setObjectName("label_espace_ligne")

        self.espace_inter_slider = QtWidgets.QSlider(self.centralwidget)
        self.espace_inter_slider.setEnabled(False)
        self.espace_inter_slider.setGeometry(QtCore.QRect(20, 180, 361, 16))
        self.espace_inter_slider.setMaximum(20)
        self.espace_inter_slider.setProperty("value", space_point)
        self.espace_inter_slider.setOrientation(QtCore.Qt.Horizontal)
        self.espace_inter_slider.setObjectName("espace_inter_slider")

        self.label_espace_inter = QtWidgets.QLabel(self.centralwidget)
        self.label_espace_inter.setEnabled(False)
        self.label_espace_inter.setGeometry(QtCore.QRect(20, 140, 331, 31))
        self.label_espace_inter.setObjectName("label_espace_inter")

        self.lcd_espace_inter = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcd_espace_inter.setEnabled(False)
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
        self.connect_button.setGeometry(QtCore.QRect(160, 320, 91, 41))
        self.connect_button.setObjectName("connect_button")

        self.enable_disable(False) #disable slider part and enable Ip part

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
        """
        Set GUI text
        """
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.Capture.setText(_translate("MainWindow", "Capture"))
        self.label_sensib.setText(_translate("MainWindow", "Sensibility"))
        self.label_espace_ligne.setText(_translate("MainWindow", "Space between two lines"))
        self.label_espace_inter.setText(_translate("MainWindow", "Minimum space between two points"))

        #IP part :
        self.lineEdit_ip.setText(_translate("MainWindow", robot_ip_address))
        self.label_adresse_ip.setText(_translate("MainWindow", "IP adress : "))
        self.connect_button.setText(_translate("MainWindow", "Connect"))

    def closeEvent(self):
        """
        Handler called when the X button is clicked
        """
        global client
        if (client == None) : # if the client is not define
            return
        else :
            client.move_joints(*sleep_joints)
            client.set_learning_mode(True)

    def set_sensib(self,entier):
        """
        Sensibility slider handler
        """
        global sensibilite
        lock.lockForWrite()
        sensibilite=entier
        lock.unlock()

    def set_space_lines(self,entier):
        """
        Space between two lines slider handler
        """
        global space_lines
        lock.lockForWrite()
        space_lines=entier
        lock.unlock()

    def set_space_point(self,entier):
        """
        Space between two points slider handler
        """
        global space_point
        lock.lockForWrite()
        space_point=entier
        lock.unlock()

    def set_capture (self):
        """
        Capture button handler
        """
        global capture
        mlock.lock()
        capture=True
        mlock.unlock()

    def set_connection (self):
        """
        Connection button handler
        """
        global robot_ip_address
        robot_ip_address = self.lineEdit_ip.text()
        print (robot_ip_address)
        self.creat_n_run_thread() #lancement du thread
        self.enable_disable(True)

    def enable_disable(self,var=False) :
        ''' enable slider part and disable ip part when var == True
            disable slider part and enable ip part when var == False
        '''
        self.lineEdit_ip.setEnabled(not(var))
        self.label_adresse_ip.setEnabled(not(var))
        self.connect_button.setEnabled(not(var))

        self.sensib_slider.setEnabled(var)
        self.Capture.setEnabled(var)
        self.lcd_sensib.setEnabled(var)
        self.espace_lignes_slider.setEnabled(var)
        self.label_sensib.setEnabled(var)
        self.lcd_espace_inter.setEnabled(var)
        self.label_espace_inter.setEnabled(var)
        self.espace_inter_slider.setEnabled(var)
        self.label_espace_ligne.setEnabled(var)
        self.lcd_espace_lignes.setEnabled(var)
        self.espace_lignes_slider.setEnabled(var)



    def creat_n_run_thread(self) :
        self.thread = QThread()
        self.robot_opencv = robot_opencv()
        self.robot_opencv.moveToThread(self.thread)

        #connections
        self.thread.started.connect(self.robot_opencv.run)

        #start
        self.thread.start()


class robot_opencv(QObject):
    """
    Class that starts the main thread and sets the robot in learning mode in case of a problem
    """

    def run (self) :
        global client
        # Connect to the robot
        client = NiryoOneClient()
        client.connect(robot_ip_address)
        # Calibrate the robot if needed
        client.calibrate(CalibrateMode.AUTO)
        client.change_tool(tool_used)
        #main program
        try :
            main_thread(client)

        except Exception as e:
            logging.info(traceback.format_exc())
            client.move_joints(*sleep_joints)
            client.set_learning_mode(True)
            logging.info("erreur")

        client.set_learning_mode(True)
        # Releasing connection
        client.quit()
        client = None

if __name__ == '__main__' :
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('icon.png'))
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
