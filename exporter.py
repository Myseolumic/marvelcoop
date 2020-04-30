from zipfile import ZipFile
from datetime import date
import io
from PIL import Image, ImageTk


def import_file(filename):
    d = {}
    with ZipFile(filename, 'r') as zip:
        floor_plan_name = ""
        with io.TextIOWrapper(zip.open("meta.txt"), encoding="utf-8") as f:
            d["date"] = f.readline()
            floor_plan_name = f.readline()

        d["img"] = io.BytesIO(zip.read(floor_plan_name))

        with io.TextIOWrapper(zip.open("positions.txt"), encoding="utf-8") as f:
            beacons = {}
            prev_parts = None
            for line in f.readlines():
                parts = line.strip().replace(' ', '')[1:-1].split(',')

                for i in range(len(parts[1:-1])):
                    parts[i + 1] = float(parts[i + 1])
                parts[-1] = int(parts[-1])
                if parts == prev_parts:
                    continue

                if parts[0] not in beacons.keys():
                    beacons[parts[0]] = []

                beacons[parts[0]].append(parts[1:])
                prev_parts = parts[:]

            d["beacons"] = beacons

    return d


def export_file():
    with ZipFile('exported_'+str(date.today())+'.zip', 'w') as zip:
        zip.write(file)