import sys, os
if sys.executable.endswith('pythonw.exe'):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.path.join(os.getenv('TEMP'), 'stderr-{}'.format(os.path.basename(sys.argv[0]))), "w")
    
# python -m venv gui
# linux: source gui/bin/activate
# windows: gui\Scripts\activate
# windows: set FLASK_APP=app.py
# pyinstaller --onefile --windowed app.py
# export FLASK_APP=app.py
# pyvan app.py --no-console
# pip install sample-sheet

import re, json, collections
from sample_sheet2 import SampleSheet

from flask import Flask, render_template, request, redirect, url_for, flash
from flaskwebgui import FlaskUI   # get the FlaskUI class

#setup flask app
#-----------------------------------------------------------
app = Flask(__name__, template_folder='templates')
ui = FlaskUI(app, width=1200, height=800)
app.secret_key = 'samplesheetsarecool'
app.config['UPLOAD_PATH'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_PATH']):
    os.makedirs(app.config['UPLOAD_PATH'])


#setup functions
#-----------------------------------------------------------
def merge_dicts(*dicts):
    d = {}
    for dict in dicts:
        for key in dict:
            try:
                d[key].append(dict[key])
            except KeyError:
                d[key] = [dict[key]]
    return d


def checkIndexes(samplesheet):
    barcodes = {}
    badBarcodes = {}
    badSamples = []

    #iterate samples in samplesheet and collect barcode pairs as tuple
    for sample in samplesheet.samples:
        barcode = (sample.index, sample.index2)
        barcodes[sample.Sample_ID] = barcode
    
    #calculate barcode pair frequency and add to barBarcodes if used
    #more than once
    for key, value in barcodes.items(): 
        badBarcodes.setdefault(value, set()).add(key)
    badBarcodes = merge_dicts(badBarcodes)
    badBarcodes = { k: v for k, v in badBarcodes.items() if len(v[0]) > 1 }

    if len(badBarcodes):
        print("Barcode conflicts dectected in sample sheet:")

        for key in badBarcodes:
            badSamples = badBarcodes[key][0]
            print(f"{key} detected in: {', '.join(badBarcodes[key][0])}")
            flash(f"BARCODE CONFLICT: {key} detected in samples: {', '.join(badBarcodes[key][0])}", 'error')

    else:
        print("No barcode conflicts dectected in sample sheet")
        flash("No barcode conflicts dectected in sample sheet", 'success')
    return badSamples


def checkChars(samplesheet):
    """ Use regex to find illegal characters in key columns of all samples """
    badCharacters = re.compile(r"[?!()<>/{}[\]~`+=\\;:\"\',*^|&.]");
    checklist     = ["Sample_ID", "Sample_Name", "Sample_Plate", "I7_Index_ID", "I5_Index_ID"]
    charSamples   = {}
    
    for sample in samplesheet.samples:
        for column in checklist: 
            if badCharacters.search(sample[column]):
                print(f"Invalid char detected in column {column} in sample {sample.Sample_ID}")
                flash(f"Invalid character in column {column} in sample {sample.Sample_ID}", "error")
                charSamples[sample.Sample_ID] = column
    return charSamples

def checkNames(samplesheet):
    sampleNames    = []
    duplicateNames = []
    emptyNames     = [] 
    i = 0
    for sample in samplesheet.samples:
        sampleNames.append(sample["Sample_Name"])
        if sample["Sample_Name"] == "":
            print(samplesheet.samples[i])
            flash(f"Warning: missing Sample_Name in row {i+1}", "error")
        i=+1

    duplicateNames = [sample for sample, count in collections.Counter(sampleNames).items() if count > 1]
    for sampleName in duplicateNames:
        flash(f"Duplicate Sample_Name for samples: {sampleName}", "error")

    print(emptyNames)
    return duplicateNames

def checkExperimentName(samplesheet):
    exName = False
    if samplesheet.Header['Experiment Name']:
        exName = True
    if not exName:
        flash(f"Experiment Name is missing from sample sheet", "error")
    return exName

#setup routes
#-----------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    sample_sheet   = None
    exName         = False
    bad_samples    = []
    bad_characters = {}
    sampleList     = []
    duplicateNames = []

    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            #save the sample sheet file in uploads
            uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], uploaded_file.filename))
            # read the sample sheet file
            sample_sheet   = SampleSheet(os.path.join(app.config['UPLOAD_PATH'], uploaded_file.filename))
            bad_samples    = checkIndexes(sample_sheet)
            bad_characters = checkChars(sample_sheet)
            sampleHeader   = ['Sample_ID', 'Sample_Name', 'Sample_Plate', 'Sample_Well', 'Index_Plate_Well', 'I7_Index_ID', 'index', 'I5_Index_ID', 'index2', 'GenomeFolder', 'Sample_Project', 'Description']
            sampleList     = [list(dict(sample).values()) for sample in sample_sheet]
            sampleList     = [sampleHeader] + sampleList
            duplicateNames = checkNames(sample_sheet)
            exName         = checkExperimentName(sample_sheet)

        return render_template('index.html', sampleSheet=sample_sheet, badSamples=bad_samples, badChars=bad_characters, sampleList=sampleList, duplicateNames=duplicateNames, exName=exName)
    return render_template('index.html', sampleSheet=sample_sheet, badSamples=bad_samples, badChars=bad_characters, sampleList=sampleList, duplicateNames=duplicateNames, exName=exName)


#-----------------------------------------------------------
if __name__ == "__main__":
    ui.run() # call the 'run' method 
