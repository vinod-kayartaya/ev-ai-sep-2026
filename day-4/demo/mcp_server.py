from pathlib import Path

from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(
    "/Users/vinod/Documents/"
).resolve()

mcp = FastMCP("Local File Server")


# ---------------------------------------------------------
# Security helper
# ---------------------------------------------------------

def safe_path(relative_path: str) -> Path:

    path = (BASE_DIR / relative_path).resolve()

    try:
        path.relative_to(BASE_DIR)
    except ValueError:
        raise ValueError(
            "Access outside the allowed directory is not permitted"
        )

    return path


# ---------------------------------------------------------
# List files
# ---------------------------------------------------------

@mcp.tool()
def list_files(directory: str = ".") -> str:
    """List files and directories."""

    path = safe_path(directory)

    if not path.exists():
        return f"Directory does not exist: {directory}"

    if not path.is_dir():
        return f"Not a directory: {directory}"

    entries = []

    for item in sorted(path.iterdir()):

        if item.is_dir():
            entries.append(f"[DIR]  {item.name}")
        else:
            entries.append(f"[FILE] {item.name}")

    return "\n".join(entries) if entries else "Directory is empty."


# ---------------------------------------------------------
# Read file
# ---------------------------------------------------------

@mcp.tool()
def read_file(file_path: str) -> str:
    """Read a text file."""

    path = safe_path(file_path)

    if not path.exists():
        return f"File does not exist: {file_path}"

    if not path.is_file():
        return f"Not a file: {file_path}"

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "This file is not a UTF-8 text file."


# ---------------------------------------------------------
# Search files
# ---------------------------------------------------------

@mcp.tool()
def search_files(query: str, directory: str = ".") -> str:
    """Search for text inside files."""

    search_path = safe_path(directory)

    if not search_path.exists():
        return f"Directory does not exist: {directory}"

    results = []

    for file in search_path.rglob("*"):

        if not file.is_file():
            continue

        try:
            content = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        if query.lower() in content.lower():
            results.append(
                str(file.relative_to(BASE_DIR))
            )

    if not results:
        return f"No files found containing: {query}"

    return "\n".join(results)


# ---------------------------------------------------------
# Start MCP server
# ---------------------------------------------------------

if __name__ == "__main__":

    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8000

    mcp.run(transport="streamable-http")