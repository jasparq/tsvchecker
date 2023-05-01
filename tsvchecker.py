import sys, os
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton, QTextEdit, QPushButton, QVBoxLayout, QGridLayout, QLabel, QFileDialog, QProgressBar
from PyQt6.QtGui import QIcon

from pdfreader import SimplePDFViewer
import time
from datetime import datetime, timedelta
from collections import defaultdict

class DirSignal(QObject):
    pathChanged=pyqtSignal(str)

class processingThread(QThread):
    finished=pyqtSignal()
    progress=pyqtSignal(int)

    def run(self):
        pass
class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('TSV SCRIPTLORD')
        self.setWindowIcon(QIcon('qlogo.png'))

        self.setStyleSheet('''
            QWidget {
                background-color: #3E3E3E;
                color: #F0F0F0;
            }
            QPushButton {
                background-color: #555;
                color: #F0F0F0;
                border-style: outset;
                border-width: 2px;
                border-radius: 10px;
                border-color: #8B8B8B;
                font: bold 14px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #777;
            }
            QLabel {
                color: #F0F0F0;
            }
            QTextEdit {
                background-color: #1E1E1E;
                color: #F0F0F0;
            }
            QProgressBar {
                background-color: #555;
                color: #F0F0F0;
                border-style: outset;
                border-width: 2px;
                border-radius: 10px;
                border-color: #8B8B8B;
                font: bold 14px;
                padding: 6px;
                text-align: center;
            }
        ''')

        self.layout=QGridLayout()
        self.setLayout(self.layout)

        # Label and Button to open Select directory modal
        self.select_folder_label=QLabel("Select Folder:")
        self.layout.addWidget(self.select_folder_label,0,0)
        select_folder_button=QPushButton('Select Folder')
        select_folder_button.clicked.connect(self.getDir)
        self.layout.addWidget(select_folder_button)

        # signal catcher when getDir finishes
        self.dir_signal=DirSignal()
        self.dir_signal.pathChanged.connect(lambda:self.getMissedDates('F70'))

        # missed reading results box
        self.missed_dates_label=QLabel('Missed Readings:')
        self.layout.addWidget(self.missed_dates_label,2,0)
        self.missed_dates_text=QTextEdit()
        self.layout.addWidget(self.missed_dates_text,3,0)

        # excursion results box
        self.excursion_label=QLabel('Excursions: ')
        self.layout.addWidget(self.excursion_label,2,1)
        self.excursion_text=QTextEdit()
        self.layout.addWidget(self.excursion_text,3,1)
        # progress bar
        self.progress_bar=QProgressBar()
        self.layout.addWidget(self.progress_bar,4,0,1,2)

    def getMissedDates(self,type):
        format='.pdf'   #checks for only pdf files in the directory
        if self.folder_input is not None and self.folder_input!='' :
            file_count=len([f for f in os.listdir(self.folder_input) if f.endswith(format)])
            self.file_count=file_count 

            print('File Count '+str(file_count))

            # logic for progress bar
            self.progress_bar.setMaximum(file_count)
            self.progress_bar.setValue(0)

            count=0

            for filename in os.listdir(self.folder_input):
                print(filename)
                filepath=os.path.join(self.folder_input, filename)
                if os.path.isfile(filepath) and filename.endswith('.pdf') and 'Printing sensor readings' in filename:
                    with open(filepath, 'rb') as file:
                        # create a PDF viewer object
                        viewer = SimplePDFViewer(file)
                        datelist=[]
                        errordates=[]
                        templist=[]

                        tempdatedict={}
                        out_of_range_dict=defaultdict(list)
                        excursion_dict=defaultdict(list)

                        excursion=0
                        excursion_count=0

                        # loop through each page and extract the text
                        for canvas in viewer:
                            cyclecount=0                       
                            lines=canvas.strings[12:]

                            for line in lines:
                                data=line.strip()
                                print(data)

                                if ":" in data and ('Print' not in data) and 'Signature' not in data:
                                    datelist.append(datetime.strptime(data,'%m/%d/%Y %H:%M'))
                                if 'C' in data or '%' in data:
                                    templist.append(data)
                            tempdatedict=dict(zip(datelist,templist))   # this turns both lists into a dictionary with 1:1 key,value

                            for i in range(len(datelist)-1):
                                diff=datelist[i+1] - datelist[i]
                                if diff>timedelta(minutes=10):
                                    if datelist[i].strftime('%m/%d/%Y %H:%M') not in errordates:
                                        errordates.append(datelist[i].strftime('%m/%d/%Y %H:%M'))
                        print(tempdatedict)
                        for date in errordates:
                            self.missed_dates_text.append(filename+': '+date)

                        if 'F70' in filename:
                            type='F70'
                        elif 'F20' in filename:
                            type='F20'
                        elif 'RFG' in filename:
                            type='RFG'
                        elif 'LAB AMBNT' in filename:
                            type='LAB AMBNT'
                        elif 'SERVER RM' in filename:
                            type='SERVER RM'
                        elif 'ARCH TEMP' in filename:
                            type='ARCH TEMP'
                        elif 'ARCH Rh' in filename:
                            type='ARCH Rh'

                        match type:
                            case 'F70':
                                high=-60
                                low=-87
                            case 'F20':
                                high=-10
                                low:-30
                            case 'RFG':
                                high=8
                                low=2
                            case 'LAB AMBNT':
                                high=30
                                low=10
                            case 'SERVER RM':
                                high=30
                                low=15
                            case 'ARCH TEMP':
                                high=30
                                low=15
                            case 'ARCH Rh':
                                high=70
                                low=10                                
                                
                        for timepoint, temp in tempdatedict.items():
                            temp=float(str(temp).split(' ')[0])
                            if temp>high or temp<low:
                                if not excursion:
                                    excursion_count+=1
                                excursion=1
                                out_of_range_dict[str(excursion_count)].append({timepoint:temp})
                            else:
                                excursion=0
                            
                        
                        for key, reading in out_of_range_dict.items():
                            first_reading_time=list(reading[0].keys())[0]
                            last_reading_time=list(reading[-1].keys())[0]

                            if last_reading_time-first_reading_time>=timedelta(minutes=30):
                                excursion_dict[key]={first_reading_time.strftime('%m/%d/%Y %H:%M'):last_reading_time.strftime('%m/%d/%Y %H:%M')}

                        for key, reading in excursion_dict.items():
                            self.excursion_text.append(filename+': '+str(reading))

                count+=1
                self.progress_bar.setValue(count)
            print(self.file_count)

    def getDir(self):
        folder_input=QFileDialog.getExistingDirectory(
            parent=self,
            caption='Select Folder',
            directory=os.getcwd()
        )
        self.folder_input=folder_input
        print(folder_input)
        self.dir_signal.pathChanged.emit(folder_input)

    

#app=QApplication([])
app=QApplication(sys.argv)

window=MyApp()
window.show()

app.exec()


