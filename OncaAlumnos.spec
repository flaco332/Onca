# Only reviewed resources are bundled. No directory-wide data/asset inclusion.
from pathlib import Path
import runpy
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
root = Path(SPECPATH)
version_module = runpy.run_path(str(root / 'app/version.py'))
version = version_module['__version__']
numbers = version_module['windows_version'](version)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, mask=0x3f, flags=0x2 if '-rc' in version else 0,
                     OS=0x40004, fileType=0x1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('FileDescription', 'ONCA Alumnos'),
        StringStruct('FileVersion', version),
        StringStruct('ProductName', 'ONCA Alumnos'),
        StringStruct('ProductVersion', version),
        StringStruct('OriginalFilename', 'OncaAlumnos.exe'),
    ])]), VarFileInfo([VarStruct('Translation', [0x0409, 1200])])])
a = Analysis([str(root / 'run.py')], pathex=[str(root)], binaries=[],
             datas=[(str(root / 'app/schema.sql'), 'app'),
                    (str(root / 'app/migrations/002_integrity_and_indexes.sql'), 'app/migrations'),
                    (str(root / 'app/migrations/003_medical_verification.sql'), 'app/migrations'),
                    (str(root / 'app/migrations/004_student_names.sql'), 'app/migrations')], hiddenimports=[],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
             noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='OncaAlumnos',
          debug=False, strip=False, upx=False, console=False, icon='NONE', version=version_info)
