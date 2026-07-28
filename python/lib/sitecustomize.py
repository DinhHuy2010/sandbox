if __name__ != "__main__":
    import sys
    import audit
    print("This is sitecustomize.py")
    print("SITE LOADED FROM:", __file__, flush=True)
    print("EXECUTABLE:", sys.executable, flush=True)
    sys.addaudithook(audit.audithook)
    del audit
else:
    import os, sys
    print("This is sitecustomize.py")
    print("linking to site-packages...")
    to = f"{sys.prefix}/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/sitecustomize.py"
    if not os.path.exists(to):
        os.symlink(__file__, to)