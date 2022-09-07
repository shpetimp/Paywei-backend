import traceback

def safe_script(func):
    def script():
        try:
            func()
        except Exception as e:
            traceback.print_exc()
    return script
