from pathlib import Path
import sys
import os

app_name = 'snap-generator'
company_name = "Alf Mikael Constantinou"

lib_dir = 'lib'
app_path = Path(__file__).parent
lib_path = app_path / lib_dir


# # Make the contents of lib_path accessible by 'import'
# if str(lib_path) not in sys.path:
#     sys.path.append(str(lib_path))

# # Make the contents of app_path also accessible by import
# if str(app_path) not in sys.path:
#     sys.path.append(str(app_path))

# import adsk.core
# app = adsk.core.Application.cast(adsk.core.Application.get())
# ui = app.userInterface
# ui.messageBox(f"Added to  path: \n{lib_path}\n{app_path}")



