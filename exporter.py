from zipfile import ZipFile
from datetime import date


def import_file(filename):
    with ZipFile(filename, 'r') as zip:
        metadata = zip.read("meta.txt")
        positions = zip.read("positions.txt")
        image = zip.read("floorplan.png") # handle different formats maybe?


def export_file():
    with ZipFile('exported_'+str(date.today())+'.zip', 'w') as zip:
        zip.write(file)