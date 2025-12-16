import sys
import time

def trace_calls(frame, event, arg):
    if event != 'call':
        return
    co = frame.f_code
    func_name = co.co_name
    if func_name == 'write':
        return
    line_no = frame.f_lineno
    filename = co.co_filename
    if 'backend' in filename:
        print(f"Call to {func_name} on line {line_no} of {filename}")
    return

sys.settrace(trace_calls)

print("Starting import of backend.app.main...")
start_time = time.time()

try:
    import backend.app.main
    print(f"Import successful in {time.time() - start_time:.2f} seconds")
except Exception as e:
    print(f"Import failed: {e}")
except KeyboardInterrupt:
    print("\nInterrupted during import")

print("Done.")
