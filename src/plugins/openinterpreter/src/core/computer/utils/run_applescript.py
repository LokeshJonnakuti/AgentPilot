import subprocess
from security import safe_command


def run_applescript(script):
    """
    Runs the given AppleScript using osascript and returns the result.
    """
    print("Running this AppleScript:\n", script)
    print(
        "---\nFeel free to directly run AppleScript to accomplish the user's task. This gives you more granular control than the `computer` module, but it is slower."
    )
    args = ["osascript", "-e", script]
    return subprocess.check_output(args, universal_newlines=True)


def run_applescript_capture(script):
    """
    Runs the given AppleScript using osascript, captures the output and error, and returns them.
    """
    print("Running this AppleScript:\n", script)
    print(
        "---\nFeel free to directly run AppleScript to accomplish the user's task. This gives you more granular control than the `computer` module, but it is slower."
    )
    args = ["osascript", "-e", script]
    result = safe_command.run(subprocess.run, args, capture_output=True, text=True, check=False)
    stdout, stderr = result.stdout, result.stderr
    return stdout, stderr
