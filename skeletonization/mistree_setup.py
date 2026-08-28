import os

MISTREE_LIBS = os.path.join(
    os.environ["VIRTUAL_ENV"],
    "Lib",
    "site-packages",
    "mistree",
    ".libs"
)

if os.path.isdir(MISTREE_LIBS):
    os.add_dll_directory(MISTREE_LIBS)