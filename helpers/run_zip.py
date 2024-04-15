import argparse
import datetime
import os
import re
import sys
import zipfile

parser = argparse.ArgumentParser("Construct zip archive")
parser.add_argument("target", action="store")
parser.add_argument("-x", "--exclude", action="append")
parser.add_argument("-m", "--merge-from", action="append", default=[])
parser.add_argument("files", nargs="+")
args = parser.parse_args(sys.argv[1:])

# raise Exception(args, sys.argv)

exclusions = [re.compile(regexp) for regexp in args.exclude]

print(datetime.datetime.now())
print(f"File {args.target}", "already exists" if os.path.exists(args.target) else "does not exist")
z = zipfile.ZipFile(args.target, "w")

for archive in args.merge_from:
    z2 = zipfile.ZipFile(archive, "r")
    for t in ((n, z2.open(n)) for n in z2.namelist()):
        z.writestr(t[0], t[1].read())


for idx in range(0, len(args.files), 2):
    file, target = args.files[idx : idx + 2]
    print(f"Checking {file}")
    if os.path.isfile(file):
        print(f"Adding {file} as {target}")
        z.write(file, target)
        continue
    for root, dirs, files in os.walk(file):
        print(f"{file} is a directory")
        for sub_file in files:
            arcpath = os.path.join(root.replace(file, target, 1), sub_file)
            print(f"Adding {sub_file} as {arcpath}")
            if any([regexp.match(arcpath) is not None for regexp in exclusions]):
                print(f"Skipping {os.path.join(root, sub_file)}")
                continue
            z.write(os.path.join(root, sub_file), arcpath)
z.close()
