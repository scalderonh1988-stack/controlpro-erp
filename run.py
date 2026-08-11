import sys
import os
from streamlit.web import cli as stcli

if __name__ == "__main__":
    try:
        # Obtiene la ruta donde está corriendo realmente el ejecutable
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        app_path = os.path.join(application_path, "app.py")

        sys.argv = [
            "streamlit",
            "run",
            app_path,
            "--global.developmentMode=false",
        ]
        sys.exit(stcli.main())
    except Exception as e:
        import traceback
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)
        raise