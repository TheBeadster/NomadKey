"""Allowlisted source archive; excludes live state, keys, environments and credentials."""
import pathlib,tarfile,sys
root=pathlib.Path(__file__).resolve().parents[1]
with tarfile.open(sys.argv[1],'w:gz') as tar:
    for name in ['nomadkey','tests','scripts','test-content','deploy','pyproject.toml']:
        path=root/name
        files=path.rglob('*') if path.is_dir() else [path]
        for file in files:
            if file.is_file() and '__pycache__' not in file.parts and file.suffix!='.pyc':
                tar.add(file,arcname=str(file.relative_to(root)))
