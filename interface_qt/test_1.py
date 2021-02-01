import sys
from PyQt5.QtWidgets import QApplication, QWidget, QCheckBox

class Fenetre(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.setWindowTitle("Ma fenetre")

        # activation du suivi du mouvement de la souris
        self.setMouseTracking(True)

    def mouseMoveEvent(self,event):
        print("position = " + str(event.x()) + " " + str(event.y()))

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

case = QCheckBox("case 1 ")
case = QCheckBox("case 2")

case.showMaximized()
case.show()



app.exec_()
