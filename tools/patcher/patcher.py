import os
import subprocess
from langchain.tools import tool

@tool
def apply_patch(patch: str) -> str:
    """
    Apply a patch to edit files.
    
    Args:
        patch: Patch contents
        
    Returns:
        STDOUT/STDERR from applying patch
    """

    try:
        result = subprocess.run(
            ["apply_patch"],
            input=patch,
            capture_output=True,
            text=True,
        )

        stderr = result.stderr.strip()
        if stderr:
            return f"STDERR: {stderr}\nSTDOUT: {result.stdout.strip()}"
        return f"STDOUT: {result.stdout.strip()}"

    except Exception as e:
        return f"An error occurred while applying patch: {str(e)}"
